import os
import time
import asyncio
import threading
import json
from typing import Optional, List
from google.cloud import aiplatform
from dotenv import load_dotenv

load_dotenv()

# Heavy ML imports are moved inside the LocalModelManager to allow 
# the API to run in a lightweight CPU-only container for Vertex mode.

# Configuration from environment
INFERENCE_MODE = os.getenv("INFERENCE_MODE", "local").lower() # 'local' or 'vertex'

# Local Config
DEFAULT_MODEL_ID = os.getenv("MODEL_ID", "google/gemma-7b-it")
DEFAULT_ADAPTER_PATH = os.getenv("ADAPTER_PATH")
ADAPTER_BASE_DIR = os.getenv("ADAPTER_BASE_DIR", "../../out/step2/")
MAX_GPU_MEMORY = os.getenv("MAX_GPU_MEMORY", "7.5GiB")
OFFLOAD_TIMEOUT = int(os.getenv("OFFLOAD_TIMEOUT_MINUTES", "10")) * 60

# Vertex Config
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GCP_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-east4")
VERTEX_ENDPOINT_ID = os.getenv("VERTEX_ENDPOINT_ID")

class BaseManager:
    def __init__(self):
        self.is_loading = False
        self.mode = INFERENCE_MODE

    async def stream_generate(self, prompt: str):
        raise NotImplementedError()

    async def update_config(self, **kwargs):
        pass

    def get_config(self):
        return {"mode": self.mode}

class LocalModelManager(BaseManager):
    def __init__(self):
        super().__init__()
        # Import heavy libraries only when this manager is initialized
        global torch, AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TextIteratorStreamer, PeftModel
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TextIteratorStreamer
        from peft import PeftModel
        
        self.model = None
        self.tokenizer = None
        self.model_id = DEFAULT_MODEL_ID
        self.adapter_path = DEFAULT_ADAPTER_PATH
        self.adapter_base_dir = ADAPTER_BASE_DIR
        self.last_active = 0
        self._lock = asyncio.Lock()
        self._offload_task = None

    async def update_config(self, model_id: Optional[str] = None, adapter_path: Optional[str] = None, adapter_base_dir: Optional[str] = None):
        async with self._lock:
            changed = False
            if model_id is not None and model_id != self.model_id:
                self.model_id = model_id
                changed = True
            if adapter_base_dir is not None and adapter_base_dir != self.adapter_base_dir:
                self.adapter_base_dir = adapter_base_dir
                changed = True
            if adapter_path is not None and adapter_path != self.adapter_path:
                self.adapter_path = adapter_path
                changed = True
            
            if changed and self.model is not None:
                print("Configuration changed. Offloading current model for reload...")
                await self._offload()

    async def _offload(self):
        if self.model:
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None
            torch.cuda.empty_cache()
            print("Model offloaded from VRAM.")

    async def load_model(self):
        async with self._lock:
            if self.model is not None:
                self.last_active = time.time()
                return

            if self.is_loading:
                while self.is_loading:
                    await asyncio.sleep(0.5)
                return

            print(f"Loading local model {self.model_id}...")
            self.is_loading = True
            try:
                compute_dtype = torch.bfloat16
                from transformers import BitsAndBytesConfig
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=compute_dtype,
                    bnb_4bit_use_double_quant=True,
                    llm_int8_enable_fp32_cpu_offload=True
                )

                self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
                self.tokenizer.pad_token = self.tokenizer.eos_token

                base_model = AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    quantization_config=bnb_config,
                    device_map="auto",
                    max_memory={0: MAX_GPU_MEMORY, "cpu": "32GiB"},
                    torch_dtype=compute_dtype,
                    low_cpu_mem_usage=True,
                    attn_implementation="sdpa"
                )

                if self.adapter_path and os.path.exists(self.adapter_path):
                    print(f"Applying adapters from {self.adapter_path}...")
                    self.model = PeftModel.from_pretrained(base_model, self.adapter_path)
                else:
                    self.model = base_model

                self.model.eval()
                self.last_active = time.time()
                print("Model loaded successfully.")
                
                if self._offload_task is None:
                    self._offload_task = asyncio.create_task(self._watchdog())
            finally:
                self.is_loading = False

    async def _watchdog(self):
        while True:
            await asyncio.sleep(60)
            if self.model and (time.time() - self.last_active > OFFLOAD_TIMEOUT):
                async with self._lock:
                    print("Inactivity timeout reached. Offloading model...")
                    await self._offload()

    async def stream_generate(self, prompt: str):
        if self.model is None:
            await self.load_model()

        self.last_active = time.time()
        inputs = self.tokenizer(prompt, return_tensors="pt").to(0)
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)

        generation_kwargs = dict(
            inputs,
            streamer=streamer,
            max_new_tokens=1024,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
        )

        # Start generation in a background thread
        thread = threading.Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()

        # Safely iterate the synchronous streamer without blocking the event loop
        iterator = iter(streamer)
        def get_next_token():
            try:
                return next(iterator)
            except StopIteration:
                return None

        while True:
            # Yield control back to the event loop while waiting for the next token
            new_text = await asyncio.to_thread(get_next_token)
            if new_text is None:
                break
                
            yield new_text
            self.last_active = time.time()

    def get_config(self):
        return {
            "mode": "local",
            "model_id": self.model_id,
            "adapter_path": self.adapter_path,
            "adapter_base_dir": self.adapter_base_dir
        }

class VertexModelManager(BaseManager):
    def __init__(self):
        super().__init__()
        self.project = GCP_PROJECT
        self.location = GCP_LOCATION
        self.endpoint_id = VERTEX_ENDPOINT_ID
        aiplatform.init(project=self.project, location=self.location)

    async def update_config(self, endpoint_id: Optional[str] = None, **kwargs):
        if endpoint_id:
            self.endpoint_id = endpoint_id

    async def stream_generate(self, prompt: str):
        if not self.endpoint_id:
            yield "\n[RollMind API is online, but no Vertex AI Endpoint ID has been configured yet. Please update the configuration or set the VERTEX_ENDPOINT_ID environment variable.]"
            return

        endpoint = aiplatform.Endpoint(
            endpoint_name=f"projects/{self.project}/locations/{self.location}/endpoints/{self.endpoint_id}"
        )
        
        # Format payload as standard OpenAI chat completions for vLLM
        openai_payload = {
            "model": "gemma",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 400,
            "temperature": 0.7,
            "top_p": 0.9,
        }
        
        try:
            # vLLM on Vertex often requires raw_predict to bypass standard Vertex formatting
            response = await asyncio.to_thread(
                endpoint.raw_predict,
                body=json.dumps(openai_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            
            # Parse OpenAI-compatible response
            response_data = json.loads(response.text)
            
            if "choices" in response_data and len(response_data["choices"]) > 0:
                content = response_data["choices"][0]["message"]["content"]
                yield content.strip()
            elif "error" in response_data:
                yield f"\n[API Error: {response_data['error']}]"
            else:
                yield "\n[Unrecognized response format from Vertex AI.]"
                    
        except Exception as e:
            # Log the full error for the administrator
            print(f"❌ Vertex AI Connection Error: {e}")
            
            # Yield a user-friendly message in the stream
            yield "\n[The RollMind engine is currently offline. Please contact the administrator.]"

    def get_config(self):
        return {
            "mode": "vertex",
            "endpoint_id": self.endpoint_id or "MISSING",
            "status": "ready" if self.endpoint_id else "awaiting_config",
            "project": self.project,
            "location": self.location
        }
    
# Singleton instance based on mode
if INFERENCE_MODE == "vertex":
    print("RollMind running in VERTEX mode.")
    manager = VertexModelManager()
else:
    print("RollMind running in LOCAL mode.")
    manager = LocalModelManager()
