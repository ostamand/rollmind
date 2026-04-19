import os
import logging
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from endpoint.toggle_endpoint import toggle_endpoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RollMind Endpoint Manager")

@app.get("/toggle")
async def toggle(
    background_tasks: BackgroundTasks,
    action: str = Query(..., regex="^(on|off)$"),
    name: str = Query("rollmind-gemma3-12b"),
    model_name: str = Query("rollmind-gemma3-12b"),
    project: str = Query(os.getenv("GOOGLE_CLOUD_PROJECT")),
    location: str = Query(os.getenv("GOOGLE_CLOUD_LOCATION", "us-east4"))
):
    if not project:
        raise HTTPException(status_code=400, detail="Project ID missing")
    
    logger.info(f"Received toggle request: action={action}, name={name}, project={project}")
    
    # Since deployment takes 15+ minutes, we run it in background
    # Note: toggle_endpoint uses print statements which will go to Cloud Run logs
    background_tasks.add_task(toggle_endpoint, project, location, name, action, model_name)
    
    return {"status": "accepted", "message": f"Toggle {action} initiated for {name} in {project}"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
