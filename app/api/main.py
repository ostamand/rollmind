import os
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware

# ... (rest of the imports)
from model import manager
import asyncio

app = FastAPI(title="RollMind API")

# Security configuration
CONFIG_SECRET_KEY = os.getenv("CONFIG_SECRET_KEY")

def verify_config_access(x_config_secret: Optional[str] = Header(None)):
    if CONFIG_SECRET_KEY and x_config_secret != CONFIG_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Config-Secret header")

# Enable CORS for Next.js
# ... (rest of middleware)
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
    endpoint_id: Optional[str] = None

@app.get("/health")
async def health():
    # Base health info
    resp = {
        "status": "online",
        "mode": manager.mode,
        "is_loading": manager.is_loading,
    }
    # Add mode-specific health
    if manager.mode == "local":
        resp["model_loaded"] = manager.model is not None
    
    return resp

@app.get("/config")
async def get_config(_: None = Depends(verify_config_access)):
    return manager.get_config()

@app.post("/config")
async def update_config(config: ConfigUpdate, _: None = Depends(verify_config_access)):
    await manager.update_config(
        model_id=config.model_id, 
        adapter_path=config.adapter_path,
        adapter_base_dir=config.adapter_base_dir,
        endpoint_id=config.endpoint_id
    )
    return {"message": "Configuration updated", "config": manager.get_config()}

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
