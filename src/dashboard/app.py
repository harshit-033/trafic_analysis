# dashboard/app.py
import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh

BACKEND = "http://127.0.0.1:8000"
JUNCTION = "J1"

st.set_page_config(page_title="AutoRoute Dashboard", layout="wide")
st.title("🚦 SmartFlow — Smart Traffic Dashboard")

# --- Auto-refresh every 5 seconds ---
st_autorefresh(interval=5000, key="refresh")

# --- Helper functions ---
def get_latest_counts():
    try:
        return requests.get(f"{BACKEND}/latest/{JUNCTION}", timeout=1).json()
    except Exception as e:
        return {"error": str(e)}

def get_status():
    try:
        return requests.get(f"{BACKEND}/status/{JUNCTION}", timeout=1).json()
    except Exception as e:
        return {"error": str(e)}

def get_alerts():
    try:
        return requests.get(f"{BACKEND}/alerts/{JUNCTION}", timeout=1).json()
    except Exception as e:
        return {"error": str(e)}

def get_processes():
    try:
        return requests.get(f"{BACKEND}/process_status/{JUNCTION}", timeout=1).json()
    except Exception as e:
        return {"error": str(e)}

def compute_timing(counts):
    try:
        req = {"junction_id": JUNCTION,
               "approaches": {"N": counts or {}, "S": counts or {}, "E": counts or {}, "W": counts or {}}}
        return requests.post(f"{BACKEND}/compute_timing", json=req, timeout=2).json()
    except Exception as e:
        return {"error": str(e)}

# --- Layout ---
col1, col2, col3 = st.columns([2, 1, 2])

# --- Live Detection Counts ---
with col1:
    st.subheader("📊 Live Detection Counts")
    latest = get_latest_counts()
    counts = latest.get("counts", {}) if isinstance(latest, dict) else {}
    if counts:
        df = pd.DataFrame(list(counts.items()), columns=["Class", "Count"])
        st.table(df)

        st.subheader("🚘 Traffic Composition")
        fig, ax = plt.subplots()
        ax.pie(df["Count"].values, labels=df["Class"].values,
               autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
        st.pyplot(fig)
    else:
        st.info("No detection data yet")

# --- Signal Health ---
with col2:
    st.subheader("🩺 Signal Health")
    status = get_status()
    if isinstance(status, dict) and "status" in status:
        s = status["status"]
        if s == "OK":
            st.success("✅ Signal Online & Stable")
        elif s == "DEGRADED":
            st.warning("⚠️ Signal Degraded")
        else:
            st.error("❌ Signal Offline")

        metrics = status.get("metrics", {})
        if metrics:
            st.write("**Last Heartbeat Metrics**")
            st.metric("CPU (%)", metrics.get("cpu", "—"))
            st.metric("Memory (%)", metrics.get("mem", "—"))
            st.metric("FPS", metrics.get("fps", "—"))
            st.metric("Avg Confidence", metrics.get("avg_conf", "—"))
            st.caption(f"Last seen: {status.get('last_seen')}")
    else:
        st.error("Status not available")

    st.markdown("---")
    st.subheader("⏱️ Signal Timings (computed)")
    timing = compute_timing(counts)
    if isinstance(timing, dict) and "phases" in timing:
        st.write(f"Cycle Length: {timing.get('cycle_length', '?')}s")
        for lane, phase in timing["phases"].items():
            st.write(f"**{lane}** → 🟢 {phase['green']}s | 🟡 {phase['yellow']}s | 🔴 {phase['all_red']}s")
    else:
        st.info("No timing data available")

# --- Process Status + Alerts ---
with col3:
    st.subheader("🔧 Process Status (Edge)")
    procs = get_processes()
    if isinstance(procs, dict) and "processes" in procs:
        for p in procs["processes"]:
            status_icon = "🟢 Running" if p.get("status") == "running" else "🔴 Stopped"
            st.write(f"- **{p.get('process')}** : {status_icon} (last: {p.get('ts')})")
    else:
        st.info("No process status available")

    st.markdown("---")
    st.subheader("🚨 Recent Alerts")
    alerts = get_alerts()
    if isinstance(alerts, dict) and "alerts" in alerts and alerts["alerts"]:
        for a in alerts["alerts"]:
            st.write(f"**{a.get('ts')}** — {a.get('issue')}")
    else:
        st.info("No alerts yet")

st.caption("Auto-refresh every 5 seconds")
