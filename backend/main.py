import asyncio
import os
import json
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.simulation.world_simulator import WorldSimulator

app = FastAPI(
    title="Autonomous Kill-Web: Automated Preemptive Suppression Architecture",
    description="MCA Minor Project Software Simulation and Network Architecture Prototype",
    version="1.0.0"
)

# Global simulation instance
simulator = WorldSimulator()

class ScenarioRequest(BaseModel):
    scenario: str

class ModeRequest(BaseModel):
    autonomous: bool

class SpeedRequest(BaseModel):
    speed: float

class ManualSuppressRequest(BaseModel):
    track_id: str
    asset_id: str

@app.get("/api/status")
async def get_status():
    return simulator.get_world_snapshot()

@app.get("/api/model_info")
async def get_model_info():
    if simulator.ml_brain.model_data:
        return {
            "roc_auc": simulator.ml_brain.model_data.get("roc_auc", 0.98),
            "feature_importances": simulator.ml_brain.model_data.get("feature_importances", {}),
            "feature_columns": simulator.ml_brain.model_data.get("feature_columns", [])
        }
    return {"status": "Model not loaded"}

@app.post("/api/scenario")
async def set_scenario(req: ScenarioRequest):
    simulator.load_scenario(req.scenario)
    return {"status": "ok", "current_scenario": req.scenario}

@app.post("/api/mode")
async def set_mode(req: ModeRequest):
    simulator.autonomous_mode = req.autonomous
    return {"status": "ok", "autonomous_mode": simulator.autonomous_mode}

@app.post("/api/speed")
async def set_speed(req: SpeedRequest):
    simulator.sim_speed = max(0.2, min(5.0, req.speed))
    return {"status": "ok", "sim_speed": simulator.sim_speed}

@app.post("/api/manual_suppress")
async def manual_suppress(req: ManualSuppressRequest):
    simulator.manual_authorize(req.track_id, req.asset_id)
    return {"status": "ok", "action": f"Authorized asset {req.asset_id} against {req.track_id}"}

@app.websocket("/ws/stream")
async def websocket_telemetry_stream(websocket: WebSocket):
    await websocket.accept()
    print("[WebSocket] Client connected to tactical C2 telemetry stream.")
    try:
        while True:
            # Advance simulation step by 0.15s
            simulator.step(dt=0.15)
            snapshot = simulator.get_world_snapshot()
            await websocket.send_text(json.dumps(snapshot))
            await asyncio.sleep(0.12)
    except WebSocketDisconnect:
        print("[WebSocket] Client disconnected.")
    except Exception as e:
        print(f"[WebSocket] Exception: {e}")

# Mount static frontend files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
async def serve_index():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"status": "Frontend building..."})
