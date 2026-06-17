# edge/watchdog.py
import time, subprocess, requests, psutil
import sys, os

# Ensure project root is available to avoid ModuleNotFoundErrors
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.backend.sms_utils import send_alert_sms   # ✅ SMS fallback

JUNCTION_ID = "J1"
BACKEND_ALERT = "http://127.0.0.1:8000/alert"
BACKEND_HEALTH = "http://127.0.0.1:8000/"

# Processes to monitor
PROCS = {
    "inference3.py": "python src/edge/inference3.py",
    "heartbeat.py": "python src/edge/heartbeat.py",
    "backend": None  # backend is checked via HTTP, not psutil
}

MAX_RESTARTS = 5
restart_counts = {name: 0 for name in PROCS}
critical_flags = {name: False for name in PROCS}  # stop retrying after 5 fails


def is_running(name: str) -> bool:
    """Check if a process with 'name' in its cmdline is running"""
    if name == "backend":
        try:
            r = requests.get(BACKEND_HEALTH, timeout=2)
            return r.status_code == 200
        except:
            return False

    for p in psutil.process_iter(['cmdline']):
        try:
            cmd = p.info.get('cmdline') or []
            if any(name in str(x) for x in cmd):
                return True
        except Exception:
            continue
    return False


def send_backend_alert(issue: str):
    """Send alert to backend, fallback to SMS"""
    try:
        requests.post(BACKEND_ALERT,
                      json={"junction_id": JUNCTION_ID, "issue": issue},
                      timeout=2)
    except:
        send_alert_sms(f"🚨 {issue} (backend unreachable)")


while True:
    for name, cmd in PROCS.items():
        running = is_running(name)

        if not running and not critical_flags[name]:
            print(f"[Watchdog] {name} is not running")

            if restart_counts[name] < MAX_RESTARTS:
                if cmd:  # only restart if it's a local process
                    print(f"[Watchdog] Restarting {name} (attempt {restart_counts[name]+1})...")
                    subprocess.Popen(cmd, shell=True)
                restart_counts[name] += 1
                send_backend_alert(f"{name} restarted at Junction {JUNCTION_ID}")
            else:
                msg = f"{name} in CRITICAL condition at Junction {JUNCTION_ID}"
                print(f"[Watchdog] {msg}")
                send_backend_alert(msg)
                critical_flags[name] = True  # stop retrying further

        elif running:
            # Reset restart count if stable
            if restart_counts[name] > 0:
                print(f"[Watchdog] {name} is now stable ✅")
            restart_counts[name] = 0

    time.sleep(10)
