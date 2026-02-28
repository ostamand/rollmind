import os
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from google.cloud import firestore

from model import manager

app = FastAPI(title="RollMind API")

# Initialize Firestore
db = None
try:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if project_id:
        db = firestore.Client(project=project_id)
        print(f"Firestore initialized for project: {project_id}")
    else:
        print("GOOGLE_CLOUD_PROJECT not set, Firestore disabled.")
except Exception as e:
    print(f"Failed to initialize Firestore: {e}")

# Security configuration
CONFIG_SECRET_KEY = os.getenv("CONFIG_SECRET_KEY")

def verify_config_access(x_config_secret: Optional[str] = Header(None)):
    if CONFIG_SECRET_KEY and x_config_secret != CONFIG_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Config-Secret header")

# Enable CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Stats(BaseModel):
    STR: int
    DEX: int
    CON: int
    INT: int
    WIS: int
    CHA: int

class Spellcasting(BaseModel):
    ability: str
    dc: int
    attackBonus: int

class CharacterProfile(BaseModel):
    charClass: str
    level: int
    stats: Stats
    spellcasting: Spellcasting

class ConsultationRequest(BaseModel):
    prompt: str
    profile: Optional[CharacterProfile] = None

class FeedbackRequest(BaseModel):
    inquiry: str
    answer: str
    is_positive: bool
    adapter_path: Optional[str] = None

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
        "firestore": db is not None
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
    # Build character profile string if provided, matching training data format
    profile_prefix = ""
    if request.profile:
        p = request.profile
        s = p.stats
        sc = p.spellcasting
        
        # Helper to format mods
        def mod(val):
            m = (val - 10) // 2
            return f"{m:+}"

        stats_str = f"STR {s.STR} ({mod(s.STR)}), DEX {s.DEX} ({mod(s.DEX)}), CON {s.CON} ({mod(s.CON)}), INT {s.INT} ({mod(s.INT)}), WIS {s.WIS} ({mod(s.WIS)}), CHA {s.CHA} ({mod(s.CHA)})"
        
        profile_prefix = f"Character Profile: {p.charClass} Level {p.level}. Stats: {stats_str}.\n"
        profile_prefix += f"Spellcasting: Ability {sc.ability}, DC {sc.dc}, Attack Bonus {sc.attackBonus:+}.\n\n"

    # Prepare the Gemma-specific instruction prompt
    full_prompt = f"<start_of_turn>user\n{profile_prefix}{request.prompt}<end_of_turn>\n<start_of_turn>model\n"
    
    # Print prompt for debugging when in local mode
    if manager.mode == "local":
        print("\n--- [LOCAL INFERENCE PROMPT] ---")
        print(repr(full_prompt))
        print("--- [END PROMPT] ---\n")

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

@app.post("/feedback")
async def save_feedback(feedback: FeedbackRequest):
    if not db:
        raise HTTPException(status_code=503, detail="Firestore is not available")
    
    try:
        current_config = manager.get_config()
        
        # Determine adapter path if not provided (fallback to current loaded one)
        adapter_path = feedback.adapter_path or current_config.get("adapter_path")
        if not adapter_path and current_config.get("mode") == "vertex":
            adapter_path = f"vertex_endpoint:{current_config.get('endpoint_id')}"

        doc_data = {
            "inquiry": feedback.inquiry,
            "answer": feedback.answer,
            "is_positive": feedback.is_positive,
            "adapter_path": adapter_path,
            "mode": current_config.get("mode"),
            "model_id": current_config.get("model_id"),
            "timestamp": firestore.SERVER_TIMESTAMP,
            "date_str": datetime.now().isoformat()
        }
        
        # Use a subagent or direct firestore call to add document
        db.collection("rollmind_feedbacks").add(doc_data)
        
        return {"message": "Feedback saved successfully"}
    except Exception as e:
        print(f"Error saving feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
