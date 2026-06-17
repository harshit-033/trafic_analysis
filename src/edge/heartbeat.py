# edge/heartbeat.py
import time, requests, psutil
JUNCTION = "J1"
BACKEND = "http://127.0.0.1:8000/heartbeat"   # adjust if backend host differs

def send_heartbeat(fps=0.0, avg_conf=0.0, camera_ok=True):
    payload = {
        "junction_id": JUNCTION,
        "ts": time.time(),
        "cpu": psutil.cpu_percent(interval=0.5),
        "mem": psutil.virtual_memory().percent,
        "fps": fps,
        "avg_conf": avg_conf,
        "camera_ok": camera_ok
    }
    try:
        requests.post(BACKEND, json=payload, timeout=2.0)
    except Exception as e:
        print("hb send failed", e)

if __name__ == "__main__":
    while True:
        send_heartbeat()
        time.sleep(10)
