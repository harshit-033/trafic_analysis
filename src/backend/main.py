# backend/main.py
import asyncio
import base64
import threading
import tempfile
import shutil
from pathlib import Path
from collections import Counter
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
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

try:
    import cv2
    CV2_OK = True
except ImportError:
    CV2_OK = False
    print('[WARN] cv2 not installed')

try:
    from ultralytics import YOLO as _YOLO
    YOLO_OK = True
except ImportError:
    YOLO_OK = False
    print('[WARN] ultralytics not installed')

# ---------------------------------------------------------------------------
# MongoDB setup
# ---------------------------------------------------------------------------
try:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=500, connectTimeoutMS=500)
    db = client["autoroute"]
    detections_col = db["detections"]
    timings_col = db["timings"]
    heartbeats_col = db["heartbeats"]
    alerts_col = db["alerts"]
    processes_col = db["processes"]       # collection to track processes
    client.server_info()
    print("[DB] Connected to MongoDB")
except errors.ServerSelectionTimeoutError as e:
    print("[DB ERROR] Could not connect", e)
    detections_col = timings_col = heartbeats_col = alerts_col = processes_col = None

# ---------------------------------------------------------------------------
# FastAPI app + CORS
# ---------------------------------------------------------------------------
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SmartFlow Backend", version="1.7")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Global direction state + YOLO loader
# ---------------------------------------------------------------------------
DIRECTIONS = ['N', 'S', 'E', 'W']
direction_states = {d: {
    'running': False,
    'counts': {},
    'fps': 0.0,
    'latest_frame': None,
    'source_type': None,
    'source_path': None,
    'lock': threading.Lock()
} for d in DIRECTIONS}

_yolo_model = None
_yolo_lock = threading.Lock()

def _get_yolo():
    global _yolo_model
    if _yolo_model is not None:
        return _yolo_model
    if not YOLO_OK:
        return None
    try:
        with _yolo_lock:
            if _yolo_model is None:
                _yolo_model = _YOLO('models/best.pt')
                print('[YOLO] Model loaded')
    except Exception as e:
        print(f'[YOLO ERROR] {e}')
    return _yolo_model

# ---------------------------------------------------------------------------
# Inference thread
# ---------------------------------------------------------------------------
def _run_inference(direction: str, source: str):
    import time
    state = direction_states[direction]
    state['running'] = True
    if not CV2_OK:
        state['running'] = False
        return
    cap = cv2.VideoCapture(source if not source.isdigit() else int(source))
    if not cap.isOpened():
        print(f'[{direction}] Cannot open source: {source}')
        state['running'] = False
        return
    frame_skip = 2
    frame_id = 0
    model = _get_yolo()
    print(f'[{direction}] Inference started')
    try:
        while state['running']:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                if not ret:
                    break
            frame_id += 1
            if frame_id % frame_skip != 0:
                continue
            t0 = time.time()
            if model is not None:
                with _yolo_lock:
                    results = model.predict(frame, imgsz=480, conf=0.25, verbose=False)
                labels = []
                for r in results:
                    for box in r.boxes:
                        labels.append(model.names[int(box.cls)])
                counts = dict(Counter(labels))
                annotated = results[0].plot()
            else:
                annotated = frame.copy()
                counts = {}
            fps_val = 1.0 / max(time.time() - t0, 0.001)
            annotated = cv2.resize(annotated, (640, 360))
            with state['lock']:
                state['counts'] = counts
                state['fps'] = round(fps_val, 1)
                state['latest_frame'] = annotated.copy()
            # Also post to detections collection in DB
            if detections_col is not None:
                try:
                    total = sum(counts.values())
                    if total > 0:
                        detections_col.insert_one({
                            'junction_id': f'J1-{direction}',
                            'direction': direction,
                            'ts': datetime.utcnow(),
                            'counts': counts
                        })
                except Exception:
                    pass
            time.sleep(0.04)  # ~25fps max
    finally:
        cap.release()
        state['running'] = False
        print(f'[{direction}] Inference stopped')

# ---------------------------------------------------------------------------
# WebSocket stream endpoint
# ---------------------------------------------------------------------------
@app.websocket('/stream/{direction}')
async def ws_stream(websocket: WebSocket, direction: str):
    if direction not in direction_states:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    state = direction_states[direction]
    try:
        while True:
            with state['lock']:
                frame = state.get('latest_frame')
                counts = dict(state.get('counts', {}))
                fps = state.get('fps', 0.0)
                running = state.get('running', False)
            if frame is not None and CV2_OK:
                _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
                b64 = base64.b64encode(buf.tobytes()).decode('utf-8')
            else:
                b64 = None
            try:
                await websocket.send_json({
                    'frame': b64,
                    'counts': counts,
                    'fps': fps,
                    'direction': direction,
                    'active': running
                })
            except Exception:
                break
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass

# ---------------------------------------------------------------------------
# Upload video endpoint
# ---------------------------------------------------------------------------
@app.post('/upload_video/{direction}')
async def upload_video(direction: str, file: UploadFile = File(...)):
    if direction not in direction_states:
        raise HTTPException(400, 'Invalid direction. Use N/S/E/W')
    direction_states[direction]['running'] = False
    await asyncio.sleep(0.3)
    suffix = Path(file.filename).suffix if file.filename else '.mp4'
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    content = await file.read()
    tmp.write(content)
    tmp.close()
    direction_states[direction].update({
        'source_type': 'video',
        'source_path': tmp.name,
        'latest_frame': None,
        'counts': {}
    })
    threading.Thread(target=_run_inference, args=(direction, tmp.name), daemon=True).start()
    return {'status': 'ok', 'direction': direction, 'source': 'video', 'filename': file.filename}

# ---------------------------------------------------------------------------
# Set CCTV source endpoint
# ---------------------------------------------------------------------------
@app.post('/set_cctv/{direction}')
async def set_cctv(direction: str, payload: Dict[str, Any]):
    if direction not in direction_states:
        raise HTTPException(400, 'Invalid direction. Use N/S/E/W')
    url = payload.get('url', '')
    if not url:
        raise HTTPException(400, 'url is required')
    direction_states[direction]['running'] = False
    await asyncio.sleep(0.3)
    direction_states[direction].update({
        'source_type': 'cctv',
        'source_path': url,
        'latest_frame': None,
        'counts': {}
    })
    threading.Thread(target=_run_inference, args=(direction, url), daemon=True).start()
    return {'status': 'ok', 'direction': direction, 'source': 'cctv', 'url': url}

# ---------------------------------------------------------------------------
# Stop stream endpoint
# ---------------------------------------------------------------------------
@app.post('/stop_stream/{direction}')
async def stop_stream(direction: str):
    if direction not in direction_states:
        raise HTTPException(400, 'Invalid direction')
    direction_states[direction]['running'] = False
    direction_states[direction].update({
        'source_type': None,
        'source_path': None,
        'latest_frame': None,
        'counts': {}
    })
    return {'status': 'stopped', 'direction': direction}

# ---------------------------------------------------------------------------
# Direction counts endpoint
# ---------------------------------------------------------------------------
@app.get('/direction_counts/{junction_id}')
def get_direction_counts(junction_id: str):
    result = {}
    for d in DIRECTIONS:
        s = direction_states[d]
        result[d] = {
            'counts': dict(s['counts']),
            'fps': s['fps'],
            'active': s['running'],
            'source_type': s['source_type']
        }
    return {'junction_id': junction_id, 'directions': result}

# ---------------------------------------------------------------------------
# History endpoint
# ---------------------------------------------------------------------------
@app.get('/history/{junction_id}')
def get_history(junction_id: str, interval: str = '5s', limit: int = 20):
    import random
    interval_map = {'5s': 5, '1m': 60, '1h': 3600, '1d': 86400}
    interval_sec = interval_map.get(interval, 5)
    if detections_col is None:
        # Return simulated data
        data = []
        base = 40
        for i in range(limit):
            v = max(0, base + random.randint(-15, 25))
            data.append({
                'time': f'T-{(limit - i) * interval_sec}s',
                'total': v,
                'car': int(v * 0.55),
                'bus': int(v * 0.1),
                'truck': int(v * 0.08),
                'bike': int(v * 0.27),
                'N': random.randint(3, 25),
                'S': random.randint(3, 25),
                'E': random.randint(3, 25),
                'W': random.randint(3, 25),
            })
            base = max(5, base + random.randint(-5, 5))
        return {'junction_id': junction_id, 'interval': interval, 'data': data}
    from datetime import timedelta
    now = datetime.utcnow()
    start_time = now - timedelta(seconds=interval_sec * limit)
    docs = list(detections_col.find(
        {'ts': {'$gte': start_time}},
        sort=[('ts', 1)]
    ).limit(limit * 20))
    data = []
    for i in range(limit):
        bs = start_time + timedelta(seconds=i * interval_sec)
        be = bs + timedelta(seconds=interval_sec)
        bucket = [d for d in docs if bs <= d.get('ts', now) < be]
        counts = Counter()
        dir_totals = {dir_: 0 for dir_ in DIRECTIONS}
        for d in bucket:
            for cls, cnt in (d.get('counts') or {}).items():
                counts[cls] += cnt
            dir_ = d.get('direction')
            if dir_ in DIRECTIONS:
                dir_totals[dir_] += sum((d.get('counts') or {}).values())
        fmt = '%H:%M' if interval_sec < 3600 else '%d/%m'
        data.append({
            'time': bs.strftime(fmt),
            'total': sum(counts.values()),
            'car': counts.get('car', 0),
            'bus': counts.get('bus', 0),
            'truck': counts.get('truck', 0),
            'bike': counts.get('bike', 0),
            **dir_totals
        })
    return {'junction_id': junction_id, 'interval': interval, 'data': data}

# ---------------------------------------------------------------------------
# Original existing endpoints
# ---------------------------------------------------------------------------
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
    ts = doc.get("ts")
    ts_iso = ts.isoformat() if isinstance(ts, datetime) else str(ts)
    return {"junction_id": junction_id, "counts": doc.get("counts", {}), "ts": ts_iso}

@app.post("/heartbeat")
def receive_heartbeat(payload: HeartbeatPayload):
    if heartbeats_col is None:
        raise HTTPException(status_code=500, detail="DB not available")
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
        send_alert_sms(f"Junction {junction_id} OFFLINE (no heartbeat >45s)")
    metrics = {
        "cpu": hb.get("cpu"),
        "mem": hb.get("mem"),
        "fps": hb.get("fps"),
        "avg_conf": hb.get("avg_conf"),
        "camera_ok": hb.get("camera_ok")
    }
    return {
        "junction_id": junction_id,
        "status": status_str,
        "last_seen": last.isoformat(),
        "metrics": metrics
    }

@app.post("/compute_timing")
def compute_timing(req: ComputeTimingRequest):
    if not req.approaches:
        raise HTTPException(status_code=400, detail="approaches missing")

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
    status_val = payload.get("status", "unknown")
    ts = datetime.utcfromtimestamp(payload.get("ts")) if payload.get("ts") else datetime.utcnow()
    processes_col.update_one(
        {"junction_id": junction, "process": proc},
        {"$set": {"status": status_val, "ts": ts}},
        upsert=True
    )
    return {"status": "ok", "junction_id": junction, "process": proc, "state": status_val}

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
    send_alert_sms(f"ALERT from {junction_id}: {issue}")
    return {"status": "recorded"}

@app.get("/alerts/{junction_id}")
def get_alerts(junction_id: str):
    if alerts_col is None:
        return {"junction_id": junction_id, "alerts": []}
    alerts = list(alerts_col.find({"junction_id": junction_id}).sort("ts", -1).limit(20))
    out = []
    for a in alerts:
        out.append({
            "ts": a.get("ts").isoformat() if isinstance(a.get("ts"), datetime) else str(a.get("ts")),
            "issue": a.get("issue"),
            "junction": a.get("junction")
        })
    return {"junction_id": junction_id, "alerts": out}

# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"msg": "SmartFlow Backend Running"}
