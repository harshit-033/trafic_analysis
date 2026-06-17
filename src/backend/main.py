# backend/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
from pymongo import MongoClient, errors
from src.backend.sms_utils import send_alert_sms
import psutil
import os

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

load_dotenv()
# Mongo
try:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=500, connectTimeoutMS=500)
    db = client["autoroute"]
    detections_col = db["detections"]
    timings_col = db["timings"]
    heartbeats_col = db["heartbeats"]
    alerts_col = db["alerts"]
    processes_col = db["processes"]       # new collection to track processes
    client.server_info()
    print("[DB] Connected to MongoDB")
except errors.ServerSelectionTimeoutError as e:
    print("[DB ERROR] Could not connect", e)
    detections_col = timings_col = heartbeats_col = alerts_col = processes_col = None

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SmartFlow Backend", version="1.6")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schemas
class Detection(BaseModel):
    cls: int
    conf: float
    xyxy: List[float]

class DetectionPayload(BaseModel):
    junction_id: str
    ts: float
    detections: List[Detection]
    counts: Dict[str, int]

class HeartbeatPayload(BaseModel):
    junction_id: str
    ts: float
    cpu: float
    mem: float
    fps: float = 0.0
    avg_conf: float = 0.0
    camera_ok: bool = True

class ComputeTimingRequest(BaseModel):
    junction_id: str
    approaches: Dict[str, Dict[str, int]]

# timing helpers (kept simple)
WEIGHTS = {"bike": 0.5, "car": 1.0, "bus": 2.5, "truck": 3.0, "pedestrian": 1.0}
MIN_GREEN, MAX_GREEN, BASE_CYCLE, K = 5.0, 60.0, 30.0, 30.0
MAX_CAPACITY_PER_APPROACH, YELLOW_TIME, ALL_RED = 30.0, 3.0, 1.0

def compute_timings_from_counts(approaches: Dict[str, Dict[str, int]]):
    weighted = {}
    for ap, counts in approaches.items():
        w = 0.0
        for cls, cnt in counts.items():
            try:
                w += float(cnt) * float(WEIGHTS.get(cls, 1.0))
            except:
                pass
        weighted[ap] = w
    total = sum(weighted.values())
    phases = {}
    if total <= 0:
        equal = round(BASE_CYCLE / max(1, len(weighted)), 2)
        for ap in weighted:
            phases[ap] = {"green": equal, "yellow": YELLOW_TIME, "all_red": ALL_RED}
        return BASE_CYCLE, phases
    cycle = round(BASE_CYCLE + K * (total / (len(weighted) * MAX_CAPACITY_PER_APPROACH)), 2)
    effective_green = max(0.0, cycle - len(weighted) * (YELLOW_TIME + ALL_RED))
    for ap, w in weighted.items():
        share = (w / total) * effective_green if total > 0 else effective_green / len(weighted)
        g = max(MIN_GREEN, min(MAX_GREEN, round(share, 2)))
        phases[ap] = {"green": g, "yellow": YELLOW_TIME, "all_red": ALL_RED}
    return cycle, phases

# Routes
@app.post("/detections")
def receive_detections(payload: DetectionPayload):
    if detections_col is None:
        raise HTTPException(status_code=500, detail="DB not available")
    doc = {
        "junction_id": payload.junction_id,
        "ts": datetime.utcfromtimestamp(payload.ts),
        "detections": [d.dict() for d in payload.detections],
        "counts": payload.counts
    }
    detections_col.insert_one(doc)
    return {"status": "ok", "counts": payload.counts}

@app.get("/latest/{junction_id}")
def get_latest_counts(junction_id: str):
    if detections_col is None:
        return {"junction_id": junction_id, "counts": {}, "msg": "DB not available"}
    doc = detections_col.find_one({"junction_id": junction_id}, sort=[("_id", -1)])
    if not doc:
        return {"junction_id": junction_id, "counts": {}, "msg": "No data"}
    # make ts ISO string for frontend clarity
    ts = doc.get("ts")
    ts_iso = ts.isoformat() if isinstance(ts, datetime) else str(ts)
    return {"junction_id": junction_id, "counts": doc.get("counts", {}), "ts": ts_iso}

@app.post("/heartbeat")
def receive_heartbeat(payload: HeartbeatPayload):
    if heartbeats_col is None:
        raise HTTPException(status_code=500, detail="DB not available")
    # convert float ts -> datetime
    try:
        ts_dt = datetime.utcfromtimestamp(payload.ts)
    except:
        ts_dt = datetime.utcnow()
    doc = {
        "junction_id": payload.junction_id,
        "ts": ts_dt,
        "cpu": payload.cpu,
        "mem": payload.mem,
        "fps": payload.fps,
        "avg_conf": payload.avg_conf,
        "camera_ok": payload.camera_ok
    }
    heartbeats_col.insert_one(doc)
    return {"status": "ok"}

@app.get("/status/{junction_id}")
def status(junction_id: str):
    """Return small health summary and last heartbeat metrics (ISO timestamp)."""
    if heartbeats_col is None:
        return {"junction_id": junction_id, "status": "OFFLINE", "last_seen": None, "metrics": {}}
    hb = heartbeats_col.find_one({"junction_id": junction_id}, sort=[("ts", -1)])
    now = datetime.utcnow()
    if not hb:
        return {"junction_id": junction_id, "status": "OFFLINE", "last_seen": None, "metrics": {}}
    last = hb.get("ts")
    if not isinstance(last, datetime):
        return {"junction_id": junction_id, "status": "OFFLINE", "last_seen": None, "metrics": {}}
    delta = (now - last).total_seconds()
    if delta <= 15:
        status_str = "OK"
    elif delta <= 45:
        status_str = "DEGRADED"
    else:
        status_str = "OFFLINE"
        # send SMS once (could be spammy if called often - acceptable for prototype)
        send_alert_sms(f"🚨 Junction {junction_id} OFFLINE (no heartbeat >45s)")
    metrics = {
        "cpu": hb.get("cpu"),
        "mem": hb.get("mem"),
        "fps": hb.get("fps"),
        "avg_conf": hb.get("avg_conf"),
        "camera_ok": hb.get("camera_ok")
    }
    return {"junction_id": junction_id,
            "status": status_str,
            "last_seen": last.isoformat(),
            "metrics": metrics}

@app.post("/compute_timing")
def compute_timing(req: ComputeTimingRequest):
    if not req.approaches:
        raise HTTPException(status_code=400, detail="approaches missing")

    # If all counts are empty → return equal split timing
    if all(sum(v.values()) == 0 for v in req.approaches.values()):
        equal = round(BASE_CYCLE / len(req.approaches), 2)
        phases = {ap: {"green": equal, "yellow": YELLOW_TIME, "all_red": ALL_RED}
                  for ap in req.approaches}
        return {"junction_id": req.junction_id, "cycle_length": BASE_CYCLE, "phases": phases}

    cycle, phases = compute_timings_from_counts(req.approaches)


    if timings_col is not None:
        timings_col.insert_one({
            "junction_id": req.junction_id,
            "ts": datetime.utcnow(),
            "cycle_length": cycle,
            "phases": phases
        })

    return {"junction_id": req.junction_id, "cycle_length": cycle, "phases": phases}



@app.post("/process_status")
def update_process_status(payload: Dict[str, Any]):
    """Watchdog posts current process status (running/failed)"""
    if processes_col is None:
        raise HTTPException(status_code=500, detail="DB not available")
    junction = payload.get("junction_id", payload.get("junction", "J1"))
    proc = payload.get("process", payload.get("process_name", "unknown"))
    status = payload.get("status", "unknown")
    ts = datetime.utcfromtimestamp(payload.get("ts")) if payload.get("ts") else datetime.utcnow()
    processes_col.update_one({"junction_id": junction, "process": proc},
                             {"$set": {"status": status, "ts": ts}}, upsert=True)
    return {"status": "ok", "junction_id": junction, "process": proc, "state": status}

@app.get("/process_status/{junction_id}")
def process_status(junction_id: str):
    """Check if inference and heartbeat processes are really running"""
    procs = []
    targets = ["inference3.py", "heartbeat.py"]

    for target in targets:
        running = False
        for p in psutil.process_iter(['cmdline']):
            try:
                cmd = p.info.get("cmdline") or []
                if any(target in str(x) for x in cmd):
                    running = True
                    break
            except Exception:
                continue

        procs.append({
            "process": target,
            "status": "running" if running else "stopped",
            "ts": datetime.utcnow()
        })

    return {"junction_id": junction_id, "processes": procs}

@app.post("/alert")
def receive_alert(payload: Dict[str, Any]):
    if alerts_col is None:
        raise HTTPException(status_code=500, detail="DB not available")
    p = payload.copy()
    p["ts"] = datetime.utcnow()
    junction_id = p.get("junction_id", p.get("junction", "Unknown"))
    p["junction_id"] = junction_id
    alerts_col.insert_one(p)
    issue = p.get("issue", "Unknown")
    send_alert_sms(f"🚨 ALERT from {junction_id}: {issue}")
    return {"status": "recorded"}

@app.get("/alerts/{junction_id}")
def get_alerts(junction_id: str):
    if alerts_col is None:
        return {"junction_id": junction_id, "alerts": []}
    alerts = list(alerts_col.find({"junction_id": junction_id}).sort("ts", -1).limit(20))
    out = []
    for a in alerts:
        out.append({"ts": a.get("ts").isoformat() if isinstance(a.get("ts"), datetime) else str(a.get("ts")), "issue": a.get("issue"), "junction": a.get("junction")})
    return {"junction_id": junction_id, "alerts": out}

@app.get("/")
def root():
    return {"msg": "SmartFlow Backend Running"}
