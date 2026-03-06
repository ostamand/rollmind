import os
import time
import asyncio
import threading
import json
from typing import Optional, List
from google.cloud import aiplatform
import google.auth
import google.auth.transport.requests
import requests
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
                # Resolve local path if it exists
                model_path = self.model_id
                local_files_only = False
                if os.path.exists(model_path):
                    model_path = os.path.abspath(model_path)
                    local_files_only = True
                    print(f"Using local model path: {model_path}")

                compute_dtype = torch.bfloat16
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=compute_dtype,
                    bnb_4bit_use_double_quant=True,
                    llm_int8_enable_fp32_cpu_offload=True
                )

                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_path, 
                    local_files_only=local_files_only
                )
                self.tokenizer.pad_token = self.tokenizer.eos_token

                base_model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    quantization_config=bnb_config,
                    device_map="auto",
                    max_memory={0: MAX_GPU_MEMORY, "cpu": "32GiB"},
                    torch_dtype=compute_dtype,
                    low_cpu_mem_usage=True,
                    attn_implementation="sdpa",
                    local_files_only=local_files_only
                )

                if self.adapter_path:
                    # Try direct path first, then relative to base dir
                    actual_adapter_path = self.adapter_path
                    if not os.path.exists(actual_adapter_path) and self.adapter_base_dir:
                        potential_path = os.path.join(self.adapter_base_dir, self.adapter_path)
                        if os.path.exists(potential_path):
                            actual_adapter_path = potential_path

                    if os.path.exists(actual_adapter_path):
                        actual_adapter_path = os.path.abspath(actual_adapter_path)
                        print(f"Applying adapters from {actual_adapter_path}...")
                        self.model = PeftModel.from_pretrained(
                            base_model, 
                            actual_adapter_path,
                            local_files_only=True
                        )
                    else:
                        print(f"Warning: Adapter path {self.adapter_path} not found. Using base model.")
                        self.model = base_model
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

    def _get_auth_token(self):
        creds, project = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        return creds.token

    async def stream_generate(self, prompt: str):
        if not self.endpoint_id:
            yield "\n[[SYSTEM_MESSAGE: RollMind API is online, but no Vertex AI Endpoint ID has been configured yet.]]"
            return

        # 1. Get Token
        try:
            token = await asyncio.to_thread(self._get_auth_token)
        except Exception as e:
            yield f"\n[[SYSTEM_MESSAGE: Authentication Error: {e}]]"
            return

        # Use :rawPredict (POST) with stream=True. 
        # vLLM will stream if headers and payload are correct.
        url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project}/locations/{self.location}/endpoints/{self.endpoint_id}:rawPredict"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        # OpenAI payload format
        openai_payload = {
            "model": "gemma",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 400,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": True 
        }
        
        try:
            # 2. Open HTTP stream with manual chunk handling
            def make_request():
                # Use a small timeout for the connection, but none for the stream itself
                return requests.post(url, headers=headers, json=openai_payload, stream=True, timeout=(5, 60))

            response = await asyncio.to_thread(make_request)
            
            if response.status_code != 200:
                error_detail = response.text
                print(f"❌ Vertex API Error ({response.status_code}): {error_detail}")
                if response.status_code == 400:
                    yield "\n[[SYSTEM_MESSAGE: The RollMind engine is currently offline or unavailable. Please try again in a few minutes.]]"
                else:
                    yield f"\n[[SYSTEM_MESSAGE: The RollMind engine encountered an issue (Error {response.status_code}).]]"
                return

            # 3. Process the stream chunk by chunk
            def iterate_tokens(resp):
                # We iterate over chunks rather than lines to bypass buffering
                for chunk in resp.iter_content(chunk_size=None):
                    if not chunk:
                        continue
                    
                    decoded = chunk.decode("utf-8")
                    # SSE data can be multiple events in one chunk
                    for line in decoded.split("\n"):
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                return
                            try:
                                data = json.loads(data_str)
                                if "choices" in data and data["choices"]:
                                    content = data["choices"][0].get("delta", {}).get("content", "")
                                    if content:
                                        yield content
                            except:
                                continue

            # 4. Stream tokens to client with artificial delay to force UI rendering
            # Network latency sometimes bundles tokens together; this ensures a smooth "typing" feel.
            gen = iterate_tokens(response)
            while True:
                token = await asyncio.to_thread(next, gen, None)
                if token is None:
                    break
                yield token
                # Small sleep to ensure React has time to render the frame before the next batch
                await asyncio.sleep(0.01)
                    
        except Exception as e:
            print(f"❌ Vertex Stream Error: {e}")
            yield "\n[[SYSTEM_MESSAGE: The connection to the RollMind engine was interrupted. Please check your network or try again.]]"

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
