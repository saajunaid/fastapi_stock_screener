from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import json

from your_logic.api_manager import AlpacaManager
from screener_engine import run_screener_instance

# --- Global State & Configuration ---
screener_results = []
scan_status = {
    "last_scan": "Never", "next_scan": "Not Scheduled",
    "auto_run": "Off", "status_message": "Idle", "progress": 0
}
SYMBOL_CONFIG = {
    'AAPL': 'low_vol_profile', 'MSFT': 'low_vol_profile', 'GOOGL': 'low_vol_profile',
    'NVDA': 'mid_vol_profile', 'AMD': 'mid_vol_profile', 'TSLA': 'high_vol_profile',
    'MSTR': 'high_vol_profile', 'RIOT': 'high_vol_profile', 'MARA': 'high_vol_profile',
    'SOFI': 'micro_cap_profile', 'PLTR': 'micro_cap_profile', 'RIVN': 'micro_cap_profile'
}

app = FastAPI()
scheduler = AsyncIOScheduler()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

api_manager = AlpacaManager()
api_manager.initialize()
api = api_manager.get_api()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

async def update_progress_and_broadcast(progress: float, message: str):
    scan_status['progress'] = progress
    scan_status['status_message'] = message
    await manager.broadcast(json.dumps({"type": "progress", "data": scan_status}))

async def scheduled_scan_job():
    global screener_results, scan_status
    if not api:
        scan_status['status_message'] = "Error: API not initialized"
        await manager.broadcast(json.dumps({"type": "status", "data": scan_status}))
        return

    await update_progress_and_broadcast(0, "Initializing scan...")
    try:
        results = await run_screener_instance(api, SYMBOL_CONFIG, update_progress_and_broadcast)
        screener_results = results
        scan_status['last_scan'] = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        job = scheduler.get_job('scan-job')
        scan_status['next_scan'] = job.next_run_time.strftime('%d-%m-%Y %H:%M:%S') if job else 'N/A'
        scan_status['status_message'] = f"Scan Completed at {scan_status['last_scan']}"
        scan_status['progress'] = 100
        await manager.broadcast(json.dumps({"type": "full_update", "data": {"results": screener_results, "status": scan_status}}))
    except Exception as e:
        logging.error(f"Error during scan: {e}", exc_info=True)
        scan_status['status_message'] = f"Error: {e}"
        await manager.broadcast(json.dumps({"type": "status", "data": scan_status}))

@app.on_event("startup")
async def startup_event():
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()

class ScheduleRequest(BaseModel):
    frequency: int

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/get_initial_data")
async def get_initial_data():
    return {"results": screener_results, "status": scan_status}

@app.post("/update_schedule")
async def update_schedule(schedule_request: ScheduleRequest):
    frequency = schedule_request.frequency
    if scheduler.get_job('scan-job'):
        scheduler.remove_job('scan-job')
    if frequency > 0:
        scheduler.add_job(scheduled_scan_job, 'interval', minutes=frequency, id='scan-job', next_run_time=datetime.now() + timedelta(seconds=5))
        scan_status['auto_run'] = f"Every {frequency} min"
        await asyncio.sleep(0.1)
        job = scheduler.get_job('scan-job')
        scan_status['next_scan'] = job.next_run_time.strftime('%d-%m-%Y %H:%M:%S') if job else "N/A"
    else:
        scan_status['auto_run'] = "Off"
        scan_status['next_scan'] = "Not Scheduled"
    await manager.broadcast(json.dumps({"type": "status", "data": scan_status}))
    return {"message": "Schedule updated."}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
