import os
import torch
import time
import asyncio
import threading
from typing import Optional
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    BitsAndBytesConfig,
    TextIteratorStreamer
)
from peft import PeftModel
from dotenv import load_dotenv

load_dotenv()

# Initial configuration from environment
DEFAULT_MODEL_ID = os.getenv("MODEL_ID", "google/gemma-7b-it")
DEFAULT_ADAPTER_PATH = os.getenv("ADAPTER_PATH")
ADAPTER_BASE_DIR = os.getenv("ADAPTER_BASE_DIR", "../../out/step2/")
MAX_GPU_MEMORY = os.getenv("MAX_GPU_MEMORY", "7.5GiB")
OFFLOAD_TIMEOUT = int(os.getenv("OFFLOAD_TIMEOUT_MINUTES", "10")) * 60

class ModelManager:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_id = DEFAULT_MODEL_ID
        self.adapter_path = DEFAULT_ADAPTER_PATH
        self.adapter_base_dir = ADAPTER_BASE_DIR
        self.last_active = 0
        self.is_loading = False
        self._lock = asyncio.Lock()
        self._offload_task = None

    async def update_config(self, model_id: Optional[str] = None, adapter_path: Optional[str] = None, adapter_base_dir: Optional[str] = None):
        """Updates the configuration and triggers a reload if necessary."""
        async with self._lock:
            changed = False
            if model_id is not None and model_id != self.model_id:
                self.model_id = model_id
                changed = True
            if adapter_base_dir is not None and adapter_base_dir != self.adapter_base_dir:
                self.adapter_base_dir = adapter_base_dir
                # If base dir changes, we should re-evaluate the adapter path if it was relative
                # but for now we'll just mark as changed to be safe.
                changed = True
            if adapter_path is not None and adapter_path != self.adapter_path:
                self.adapter_path = adapter_path
                changed = True
            
            if changed and self.model is not None:
                print("Configuration changed. Offloading current model for reload...")
                await self._offload()

    async def _offload(self):
        """Internal helper to clear model from VRAM."""
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

            print(f"Loading model {self.model_id}...")
            if self.adapter_path:
                print(f"Using adapter: {self.adapter_path}")
                
            self.is_loading = True
            try:
                compute_dtype = torch.bfloat16
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=compute_dtype,
                    bnb_4bit_use_double_quant=True,
                    llm_int8_enable_fp32_cpu_offload=True
                )

                self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
                self.tokenizer.pad_token = self.tokenizer.eos_token

                # Use the same VRAM-saving map strategy as training
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
                
                # Start offload watchdog
                if self._offload_task is None:
                    self._offload_task = asyncio.create_task(self._watchdog())

            finally:
                self.is_loading = False

    async def _watchdog(self):
        """Automatically offloads model if inactive."""
        while True:
            await asyncio.sleep(60) # Check every minute
            if self.model and (time.time() - self.last_active > OFFLOAD_TIMEOUT):
                async with self._lock:
                    print("Inactivity timeout reached. Offloading model...")
                    await self._offload()

    async def stream_generate(self, prompt: str):
        if self.model is None:
            await self.load_model()

        self.last_active = time.time()
        
        # Prepare input
        inputs = self.tokenizer(prompt, return_tensors="pt").to(0)
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)

        # Generation kwargs
        generation_kwargs = dict(
            inputs,
            streamer=streamer,
            max_new_tokens=1024,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
        )

        # Run generation in a separate thread to not block the event loop
        thread = threading.Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()

        for new_text in streamer:
            yield new_text
            self.last_active = time.time()

# Singleton instance
manager = ModelManager()
