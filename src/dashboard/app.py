# dashboard/app.py
from __future__ import annotations

import base64
from io import BytesIO
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

AUTO_REFRESH_ENABLED = st_autorefresh is not None

BACKEND = "http://127.0.0.1:8000"
JUNCTION = "J1"
ROOT = Path(__file__).resolve().parents[2]
REFERENCE_IMAGE = ROOT / "reference image.png"
TRAFFIC_IMAGE = ROOT / "models" / "runs" / "detect" / "predict" / "test.jpg"

ACCENT_GREEN = "#62ee86"
ACCENT_LIME = "#dfff45"
PANEL = "rgba(24, 30, 38, 0.82)"
BORDER = "rgba(181, 255, 150, 0.25)"

DEMO_COUNTS = {"car": 14, "bike": 5, "bus": 2, "truck": 3, "pedestrian": 1}
HISTORY = [28, 48, 68, 75, 58, 62, 118, 104, 96, 112, 126, 168, 154, 116, 104, 128, 84]
PEDESTRIANS = [8, 10, 14, 20, 13, 16, 26, 21, 24, 22, 25, 36, 31, 22, 24, 29, 12]
EFFICIENCY = [68, 88, 69, 55, 86, 76, 86]

st.set_page_config(page_title="SmartFlow", page_icon="S", layout="wide")
if AUTO_REFRESH_ENABLED:
    st_autorefresh(interval=5000, key="smartflow_refresh")


def image_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def get_json(path: str, timeout: float = 1.2) -> dict[str, Any]:
    try:
        response = requests.get(f"{BACKEND}{path}", timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"error": str(exc)}


def post_json(path: str, payload: dict[str, Any], timeout: float = 2.0) -> dict[str, Any]:
    try:
        response = requests.post(f"{BACKEND}{path}", json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"error": str(exc)}


def get_latest_counts() -> dict[str, Any]:
    return get_json(f"/latest/{JUNCTION}")


def get_status() -> dict[str, Any]:
    return get_json(f"/status/{JUNCTION}")


def get_alerts() -> dict[str, Any]:
    return get_json(f"/alerts/{JUNCTION}")


def get_processes() -> dict[str, Any]:
    return get_json(f"/process_status/{JUNCTION}")


def compute_timing(counts: dict[str, int]) -> dict[str, Any]:
    payload = {
        "junction_id": JUNCTION,
        "approaches": {"N": counts, "S": counts, "E": counts, "W": counts},
    }
    return post_json("/compute_timing", payload)


def compact_time(value: Any) -> str:
    if not value:
        return "No signal"
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%H:%M:%S")
    except ValueError:
        return str(value)


def safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def health_value(metric: Any, invert: bool = True) -> int:
    value = safe_int(metric, 0)
    return max(0, min(100, 100 - value if invert else value))


def css() -> None:
    bg = image_data_uri(TRAFFIC_IMAGE if TRAFFIC_IMAGE.exists() else REFERENCE_IMAGE)
    background = (
        f"linear-gradient(rgba(11, 15, 20, .76), rgba(11, 15, 20, .82)), url('{bg}')"
        if bg
        else "linear-gradient(135deg, #101820, #1b242b)"
    )
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        :root {{
            --green: {ACCENT_GREEN};
            --lime: {ACCENT_LIME};
            --panel: {PANEL};
            --border: {BORDER};
            --text: #f4f7f5;
            --muted: #a9b6b2;
        }}
        html, body, [class*="css"] {{
            font-family: Inter, system-ui, -apple-system, Segoe UI, sans-serif;
        }}
        .stApp {{
            background: {background};
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: var(--text);
        }}
        .stApp::before {{
            content: "";
            position: fixed;
            inset: 0;
            backdrop-filter: blur(7px);
            pointer-events: none;
        }}
        [data-testid="stSidebar"] {{
            background: rgba(244, 248, 246, 0.95);
            border-right: 1px solid rgba(12, 17, 23, 0.1);
        }}
        [data-testid="stSidebar"] * {{
            color: #111820;
        }}
        [data-testid="stSidebar"] [role="radiogroup"] label {{
            border-radius: 8px;
            padding: 9px 10px;
            margin: 5px 0;
        }}
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
            background: #182029;
            box-shadow: 0 12px 24px rgba(11, 16, 22, 0.18);
        }}
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) * {{
            color: white;
        }}
        .main .block-container {{
            padding: 1.35rem 1.7rem 2.4rem;
            max-width: 1480px;
        }}
        header, footer, #MainMenu {{ visibility: hidden; }}
        h1, h2, h3, p {{ margin: 0; }}
        .topbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-height: 58px;
            margin: -1.35rem -1.7rem 1.2rem;
            padding: 0 1.7rem;
            background: rgba(24, 29, 36, 0.94);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .topbar h1 {{
            font-size: clamp(1.25rem, 2vw, 1.55rem);
            font-weight: 800;
            letter-spacing: 0;
        }}
        .top-actions {{
            display: flex;
            align-items: center;
            gap: 14px;
            color: #eaf0ee;
            font-size: 0.9rem;
        }}
        .avatar {{
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: grid;
            place-items: center;
            background: linear-gradient(145deg, #39424b, #161d24);
            border: 1px solid rgba(255,255,255,.18);
            font-weight: 800;
        }}
        .page-title {{
            margin: 1.2rem 0 1.1rem;
            font-size: clamp(1.3rem, 2.3vw, 1.8rem);
            font-weight: 800;
            color: #f8fbfa;
        }}
        .glass {{
            min-height: 100%;
            padding: 18px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--panel);
            box-shadow: 0 18px 45px rgba(0, 0, 0, 0.27), inset 0 1px 0 rgba(255,255,255,.05);
        }}
        .glass.glow {{
            border-color: rgba(223, 255, 69, 0.78);
            box-shadow: 0 0 0 1px rgba(223,255,69,.22), 0 0 42px rgba(98,238,134,.23);
            background: radial-gradient(circle at 50% 12%, rgba(223,255,69,.22), transparent 52%), var(--panel);
        }}
        .card-title {{
            color: white;
            font-weight: 700;
            font-size: 0.98rem;
            margin-bottom: 16px;
            text-transform: uppercase;
        }}
        .big-number {{
            font-size: clamp(2.4rem, 6vw, 4.2rem);
            line-height: 1;
            font-weight: 800;
            color: white;
            text-align: center;
        }}
        .metric-label {{
            color: #dbe6de;
            text-align: center;
            font-weight: 700;
            margin-top: 8px;
            line-height: 1.08;
        }}
        .muted {{
            color: var(--muted);
            font-size: .86rem;
        }}
        .health-row {{
            display: grid;
            grid-template-columns: minmax(90px, 1fr) 3fr 48px;
            gap: 10px;
            align-items: center;
            margin: 13px 0;
            font-size: .9rem;
        }}
        .bar {{
            height: 10px;
            border-radius: 99px;
            background: rgba(255,255,255,.12);
            overflow: hidden;
        }}
        .fill {{
            height: 100%;
            border-radius: inherit;
            background: linear-gradient(90deg, var(--green), var(--lime));
        }}
        .signal-grid {{
            display: grid;
            grid-template-columns: 42px 1fr 56px 42px;
            gap: 8px;
            align-items: center;
            text-align: center;
        }}
        .direction {{
            padding: 12px 0;
            border-radius: 6px;
            background: rgba(255,255,255,.12);
            color: #aeb8b5;
        }}
        .phase {{
            padding: 10px 8px;
            border-radius: 6px;
            border: 1px solid rgba(98,238,134,.72);
            background: rgba(98,238,134,.18);
            color: white;
        }}
        .phase.alt {{
            border-color: rgba(223,255,69,.7);
            background: rgba(223,255,69,.18);
        }}
        .cycle {{
            margin-top: 14px;
            display: flex;
            gap: 10px;
            align-items: end;
            justify-content: center;
        }}
        .cycle strong {{
            font-size: clamp(2.6rem, 6vw, 4rem);
            line-height: .85;
            color: white;
        }}
        .alert-row, .report-row {{
            padding: 11px 0;
            border-bottom: 1px solid rgba(255,255,255,.11);
            color: #e8eeee;
            font-size: .9rem;
        }}
        .pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 9px;
            border-radius: 999px;
            background: rgba(98,238,134,.12);
            border: 1px solid rgba(98,238,134,.28);
            color: #d9ffe0;
            font-size: .78rem;
            font-weight: 700;
        }}
        .map {{
            min-height: 360px;
            position: relative;
            overflow: hidden;
            background:
                linear-gradient(90deg, transparent 46%, rgba(255,255,255,.13) 46% 54%, transparent 54%),
                linear-gradient(0deg, transparent 46%, rgba(255,255,255,.13) 46% 54%, transparent 54%),
                rgba(19, 25, 33, .82);
        }}
        .map-node {{
            position: absolute;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: var(--green);
            box-shadow: 0 0 22px var(--green);
        }}
        .node-n {{ top: 18%; left: 49%; }}
        .node-s {{ bottom: 18%; left: 49%; }}
        .node-e {{ right: 18%; top: 49%; }}
        .node-w {{ left: 18%; top: 49%; }}
        .stDataFrame, [data-testid="stTable"] {{
            background: rgba(20, 25, 32, .82);
            border-radius: 8px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar() -> str:
    st.sidebar.markdown(
        """
        <div style="display:flex;align-items:center;gap:10px;margin:18px 0 28px;">
            <div style="width:34px;height:34px;border-radius:50%;border:2px solid #74df6e;display:grid;place-items:center;color:#58c95e;font-weight:900;">S</div>
            <div style="font-size:1.28rem;font-weight:800;">SmartFlow</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return st.sidebar.radio(
        "Navigation",
        [
            "Overview",
            "Traffic Analytics",
            "System Status",
            "Alerts",
            "Junction Map",
            "Reports",
        ],
        label_visibility="collapsed",
    )


def topbar() -> None:
    now = datetime.now().strftime("%I:%M %p, %d %b %Y")
    refresh_label = "Live refresh 5s" if AUTO_REFRESH_ENABLED else "Manual refresh"
    st.markdown(
        f"""
        <div class="topbar">
            <h1>OVERVIEW</h1>
            <div class="top-actions">
                <span>{now}</span>
                <span class="pill">{refresh_label}</span>
                <span class="avatar">AR</span>
                <strong>A.R.</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card(title: str, body: str, glow: bool = False) -> None:
    cls = "glass glow" if glow else "glass"
    st.markdown(f'<div class="{cls}"><div class="card-title">{title}</div>{body}</div>', unsafe_allow_html=True)


def fig_data_uri(fig: plt.Figure) -> str:
    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", transparent=True, dpi=160)
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def chart_card(title: str, fig: plt.Figure) -> None:
    body = f'<img src="{fig_data_uri(fig)}" style="width:100%;display:block;" alt="{title}">'
    card(title, body)


def donut(counts: dict[str, int]) -> plt.Figure:
    labels = list(counts.keys())
    values = [max(0, int(v)) for v in counts.values()]
    if not any(values):
        labels, values = list(DEMO_COUNTS.keys()), list(DEMO_COUNTS.values())
    fig, ax = plt.subplots(figsize=(3.7, 3), facecolor="none")
    ax.set_facecolor("none")
    colors = [ACCENT_GREEN, "#8ff266", ACCENT_LIME, "#f2ff7a", "#4ccf7b"]
    ax.pie(
        values,
        labels=None,
        autopct=lambda pct: f"{pct:.0f}%" if pct >= 4 else "",
        startangle=90,
        counterclock=False,
        colors=colors[: len(values)],
        wedgeprops={"width": 0.42, "edgecolor": "#1b222b", "linewidth": 1},
        textprops={"color": "#111820", "fontsize": 9, "fontweight": "bold"},
    )
    ax.legend(
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.1),
        ncol=2,
        frameon=False,
        fontsize=7,
        labelcolor="#eef5f0",
    )
    return fig


def line_chart() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8.4, 3.6), facecolor="none")
    ax.set_facecolor("none")
    x = list(range(len(HISTORY)))
    ax.plot(x, HISTORY, color=ACCENT_GREEN, linewidth=2.6)
    ax.fill_between(x, HISTORY, color=ACCENT_GREEN, alpha=0.22)
    ax.plot(x, PEDESTRIANS, color=ACCENT_LIME, linewidth=2)
    ax.grid(True, axis="y", color="white", alpha=0.16)
    ax.tick_params(colors="#edf4f0", labelsize=8)
    ax.set_ylim(0, max(HISTORY) + 28)
    ticks = x[::2]
    labels = [f"{min(i * 3, 23):02d}h" for i in range(len(ticks))]
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.legend(["Vehicles", "Pedestrians"], loc="upper right", frameon=False, labelcolor="#edf4f0", fontsize=8)
    return fig


def bar_chart() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8.4, 3.6), facecolor="none")
    ax.set_facecolor("none")
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    bars = ax.bar(days, EFFICIENCY, color=ACCENT_GREEN, edgecolor=ACCENT_LIME, linewidth=1)
    for idx, patch in enumerate(bars):
        shade = 0.65 + idx * 0.04
        patch.set_facecolor((0.35, min(1, shade), 0.42, 1))
    ax.grid(True, axis="y", color="white", alpha=0.16)
    ax.tick_params(colors="#edf4f0", labelsize=8)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Wait time reduced (%)", color="#edf4f0", fontsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    return fig


def current_state() -> tuple[dict[str, int], dict[str, Any], dict[str, Any], dict[str, Any], bool]:
    latest = get_latest_counts()
    counts = latest.get("counts", {}) if isinstance(latest, dict) else {}
    live_counts = bool(counts)
    if not counts:
        counts = DEMO_COUNTS
    status = get_status()
    alerts = get_alerts()
    procs = get_processes()
    return counts, status, alerts, procs, live_counts


def vehicle_card(counts: dict[str, int], live_counts: bool) -> None:
    total = sum(safe_int(v) for v in counts.values())
    body = f"""
        <div style="display:grid;place-items:center;gap:8px;">
            <div style="font-size:4.2rem;color:{ACCENT_GREEN};line-height:1;">car</div>
            <div class="big-number">{total}</div>
            <div class="metric-label">VEHICLES<br>DETECTED</div>
            <div class="muted">{"Live" if live_counts else "Demo preview"}</div>
        </div>
    """
    card("", body, glow=True)


def timing_card(timing: dict[str, Any]) -> None:
    phases = timing.get("phases", {}) if isinstance(timing, dict) else {}
    north = safe_int(phases.get("N", {}).get("green"), 28)
    east = safe_int(phases.get("E", {}).get("green"), 12)
    cycle = safe_int(timing.get("cycle_length"), 30) if isinstance(timing, dict) else 30
    body = f"""
        <div class="muted" style="display:flex;justify-content:space-between;margin-bottom:10px;">
            <span>N/S Green: <b style="color:{ACCENT_GREEN};">{north}s</b></span>
            <span>E/W Green: <b style="color:{ACCENT_LIME};">{east}s</b></span>
        </div>
        <div class="signal-grid">
            <div class="direction">N</div>
            <div class="phase">{north}s</div>
            <div class="phase alt">{east}s</div>
            <div class="direction">E</div>
            <div class="direction">S</div>
            <div></div>
            <div></div>
            <div class="direction">W</div>
        </div>
        <div class="cycle">
            <strong>{cycle}s</strong>
            <div>
                <div style="font-size:1.3rem;font-weight:800;color:white;">CYCLE</div>
                <div class="muted">AutoRoute active</div>
            </div>
        </div>
    """
    card("Adaptive Signal Timing (J1)", body)


def health_card(status: dict[str, Any], procs: dict[str, Any]) -> None:
    metrics = status.get("metrics", {}) if isinstance(status, dict) else {}
    state = status.get("status", "OFFLINE") if isinstance(status, dict) else "OFFLINE"
    camera_ok = metrics.get("camera_ok", state == "OK")
    process_list = procs.get("processes", []) if isinstance(procs, dict) else []
    running = sum(1 for p in process_list if p.get("status") == "running")
    process_score = round((running / max(1, len(process_list))) * 100)
    rows = [
        ("Edge AI", process_score, f"{process_score}%"),
        ("Backend API", 0 if "error" in status else 100, "OK" if "error" not in status else "DOWN"),
        ("CPU headroom", health_value(metrics.get("cpu")), f"{health_value(metrics.get('cpu'))}%"),
        ("Camera Feed", 100 if camera_ok else 0, "OK" if camera_ok else "LOST"),
    ]
    rendered = "".join(
        f"""
        <div class="health-row">
            <span>{name}</span>
            <div class="bar"><div class="fill" style="width:{value}%;"></div></div>
            <span style="text-align:right;">{label}</span>
        </div>
        """
        for name, value, label in rows
    )
    card("System Health", rendered)


def alerts_card(alerts: dict[str, Any]) -> None:
    items = alerts.get("alerts", []) if isinstance(alerts, dict) else []
    if not items:
        items = [
            {"ts": "09:44:12", "issue": "J1 S: High congestion detected"},
            {"ts": "09:41:05", "issue": "Edge AI: Reconnected"},
        ]
    body = "".join(
        f'<div class="alert-row"><span class="muted">{compact_time(a.get("ts"))}</span> - {a.get("issue", "Alert")}</div>'
        for a in items[:5]
    )
    card("Recent Alerts", body)


def overview() -> None:
    counts, status, alerts, procs, live_counts = current_state()
    timing = compute_timing(counts)
    st.markdown('<div class="page-title">Dashboard Overview - Junction J1 (Live Data)</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns([1.55, 1, 1.55, 1.5, 1.55], gap="medium")
    with c1:
        chart_card("Current Traffic Flow (J1)", donut(counts))
    with c2:
        vehicle_card(counts, live_counts)
    with c3:
        timing_card(timing)
    with c4:
        health_card(status, procs)
    with c5:
        alerts_card(alerts)

    c6, c7 = st.columns(2, gap="medium")
    with c6:
        chart_card("Historical Traffic Volume (24h)", line_chart())
    with c7:
        chart_card("Signal Efficiency Trend (7 days)", bar_chart())


def traffic_analytics() -> None:
    counts, _, _, _, live_counts = current_state()
    st.markdown('<div class="page-title">Traffic Analytics</div>', unsafe_allow_html=True)
    df = pd.DataFrame({"Class": counts.keys(), "Count": counts.values()}).sort_values("Count", ascending=False)
    total = df["Count"].sum()
    c1, c2 = st.columns([1.2, 1], gap="medium")
    with c1:
        chart_card("Vehicle Mix", donut(counts))
    with c2:
        rows = "".join(
            f'<div class="report-row"><b>{row.Class.title()}</b><span style="float:right;">{row.Count} ({(row.Count / max(1, total) * 100):.1f}%)</span></div>'
            for row in df.itertuples()
        )
        card("Detected Classes", rows + f'<div class="muted" style="margin-top:12px;">{"Live backend data" if live_counts else "Preview data until detections arrive"}</div>')
    chart_card("24h Flow Pattern", line_chart())


def system_status() -> None:
    _, status, _, procs, _ = current_state()
    metrics = status.get("metrics", {}) if isinstance(status, dict) else {}
    st.markdown('<div class="page-title">System Status</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4, gap="medium")
    values = [
        ("Signal State", status.get("status", "OFFLINE")),
        ("CPU", f"{metrics.get('cpu', '0')}%"),
        ("Memory", f"{metrics.get('mem', '0')}%"),
        ("FPS", metrics.get("fps", "0")),
    ]
    for col, (title, value) in zip([c1, c2, c3, c4], values):
        with col:
            card(title, f'<div class="big-number" style="font-size:2.6rem;">{value}</div>')
    health_card(status, procs)
    process_list = procs.get("processes", []) if isinstance(procs, dict) else []
    rows = "".join(
        f'<div class="report-row"><b>{p.get("process")}</b><span style="float:right;">{p.get("status", "unknown").title()}</span></div>'
        for p in process_list
    )
    card("Edge Processes", rows or '<div class="muted">No process data available.</div>')


def alerts_view() -> None:
    _, _, alerts, _, _ = current_state()
    st.markdown('<div class="page-title">Alerts</div>', unsafe_allow_html=True)
    alerts_card(alerts)
    card(
        "Response Guide",
        """
        <div class="report-row"><b>High congestion</b><span style="float:right;">Review adaptive timing and lane queue.</span></div>
        <div class="report-row"><b>Offline heartbeat</b><span style="float:right;">Start heartbeat.py or watchdog.py.</span></div>
        <div class="report-row"><b>Camera lost</b><span style="float:right;">Check edge camera feed and process status.</span></div>
        """,
    )


def junction_map() -> None:
    st.markdown('<div class="page-title">Junction Map</div>', unsafe_allow_html=True)
    card(
        "J1 Live Intersection",
        """
        <div class="map">
            <div class="map-node node-n"></div>
            <div class="map-node node-s"></div>
            <div class="map-node node-e"></div>
            <div class="map-node node-w"></div>
            <div style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font-size:2rem;font-weight:900;color:white;">J1</div>
        </div>
        """,
    )


def reports() -> None:
    counts, status, alerts, _, live_counts = current_state()
    st.markdown('<div class="page-title">Reports</div>', unsafe_allow_html=True)
    total = sum(safe_int(v) for v in counts.values())
    highest = max(counts, key=counts.get) if counts else "none"
    rows = [
        ("Total detections", total),
        ("Dominant class", highest.title()),
        ("Signal state", status.get("status", "OFFLINE") if isinstance(status, dict) else "OFFLINE"),
        ("Alert count", len(alerts.get("alerts", [])) if isinstance(alerts, dict) else 0),
        ("Data source", "Live" if live_counts else "Preview"),
    ]
    body = "".join(f'<div class="report-row"><b>{name}</b><span style="float:right;">{value}</span></div>' for name, value in rows)
    card("Operational Summary", body)
    chart_card("Efficiency Trend", bar_chart())


css()
page = sidebar()
topbar()

if page == "Overview":
    overview()
elif page == "Traffic Analytics":
    traffic_analytics()
elif page == "System Status":
    system_status()
elif page == "Alerts":
    alerts_view()
elif page == "Junction Map":
    junction_map()
else:
    reports()
