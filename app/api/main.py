import os
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from model import manager
import asyncio

app = FastAPI(title="RollMind API")

# Enable CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConsultationRequest(BaseModel):
    prompt: str

class ConfigUpdate(BaseModel):
    model_id: Optional[str] = None
    adapter_path: Optional[str] = None
    adapter_base_dir: Optional[str] = None

@app.get("/health")
async def health():
    return {
        "status": "online",
        "model_loaded": manager.model is not None,
        "is_loading": manager.is_loading,
        "model_id": manager.model_id,
        "adapter_path": manager.adapter_path,
        "adapter_base_dir": manager.adapter_base_dir
    }

@app.get("/config")
async def get_config():
    return {
        "model_id": manager.model_id,
        "adapter_path": manager.adapter_path,
        "adapter_base_dir": manager.adapter_base_dir
    }

@app.post("/config")
async def update_config(config: ConfigUpdate):
    await manager.update_config(model_id=config.model_id, adapter_path=config.adapter_path)
    return {"message": "Configuration updated", "config": {
        "model_id": manager.model_id,
        "adapter_path": manager.adapter_path,
        "adapter_base_dir": manager.adapter_base_dir
    }}

@app.post("/consult")
async def consult(request: ConsultationRequest):
    # Prepare the Gemma-specific instruction prompt
    full_prompt = f"<start_of_turn>user\n{request.prompt}<end_of_turn>\n<start_of_turn>model\n"
    
    async def event_generator():
        try:
            async for token in manager.stream_generate(full_prompt):
                # If client disconnects, the loop will raise an exception or stop
                yield {"data": token}
        except asyncio.CancelledError:
            print("Client disconnected from stream.")
        except Exception as e:
            yield {"data": f"Error: {str(e)}"}

    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
