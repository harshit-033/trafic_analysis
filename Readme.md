# SmartFlow — Intelligent Traffic Monitoring System 🚦

<p align="center">
  <img src="reference image.png" alt="SmartFlow Dashboard" width="800"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Prototype%20Complete-brightgreen?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/React-Vite-61DAFB?style=for-the-badge&logo=react&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/YOLO-Object%20Detection-EF233C?style=for-the-badge" />
  <img src="https://img.shields.io/badge/MongoDB-Database-47A248?style=for-the-badge&logo=mongodb&logoColor=white" />
</p>

---

**SmartFlow** is a real-time, computer-vision-powered smart traffic signal system. It uses YOLO object detection on live video feeds to count and classify vehicles, dynamically computes adaptive green-light timings based on actual traffic load, and presents everything through a professional glassmorphic dashboard. The system is fully self-healing — edge scripts monitor themselves, restart on failure, and send SMS alerts if a camera or node goes offline.

---

## 🌟 Current Status

> **Prototype — Feature Complete**

| Component | Status |
|---|---|
| YOLO Inference Engine | ✅ Working |
| FastAPI Backend + MongoDB | ✅ Working |
| Adaptive Signal Timing Algorithm | ✅ Working |
| React / Vite Dashboard | ✅ Working |
| Heartbeat + Watchdog Edge Services | ✅ Working |
| SMS Alerts via Twilio | ✅ Working |
| Per-Lane ROI Detection | 🔜 Planned |
| Multi-Junction Coordination | 🔜 Planned |

---

## ✨ Key Features

- **🤖 Real-Time Edge AI** — YOLOv8/YOLO11 detects and classifies vehicles (car, bus, truck, bike, pedestrian) from video or RTSP camera feeds every frame.
- **🚦 Adaptive Signal Timing** — An algorithm weighs vehicle types by size/impact and calculates optimal green-phase durations per approach, replacing fixed-interval timers.
- **📊 Live Dashboard** — A dark-themed, glassmorphic React web app with animated donut charts, area graphs, and bar charts — all polling live backend data every 5 seconds.
- **💓 Edge Health Monitoring** — A heartbeat script reports CPU, memory, FPS, and camera status to the backend every 10 seconds.
- **🐕 Watchdog Recovery** — Automatically detects crashed inference or heartbeat processes and restarts them (up to 5 attempts before raising an alert).
- **📲 SMS Alerts** — Twilio integration sends an SMS instantly if a junction goes offline or a critical failure is detected.

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Edge Device (Camera)                   │
│   ┌────────────────┐   ┌────────────┐   ┌─────────────┐ │
│   │ inference3.py  │   │heartbeat.py│   │ watchdog.py │ │
│   │ (YOLO + OpenCV)│   │(Health HB) │   │(Auto-Restart│ │
│   └───────┬────────┘   └─────┬──────┘   └─────┬───────┘ │
└───────────┼──────────────────┼────────────────┼─────────┘
            │ POST /detections  │ POST /heartbeat │ POST /alert
            ▼                  ▼                 ▼
┌──────────────────────────────────────────────────────────┐
│             FastAPI Backend (src/backend/main.py)         │
│   • Stores detections, heartbeats, alerts in MongoDB      │
│   • Runs adaptive signal timing algorithm                 │
│   • Serves REST API on http://localhost:8001              │
└──────────────────────────────┬───────────────────────────┘
                               │ Polls every 5s
                               ▼
┌──────────────────────────────────────────────────────────┐
│        React/Vite Dashboard (frontend/)                   │
│   • http://localhost:5173                                 │
│   • Shows live counts, timing, health, alerts, charts     │
└──────────────────────────────────────────────────────────┘
```

---

## 🚀 Getting Started

### Prerequisites

Make sure the following are installed on your machine:

| Tool | Version | Purpose |
|---|---|---|
| Git | any | Clone the repository |
| Python | 3.10+ | Backend & edge scripts |
| Node.js + npm | 18+ | Frontend dashboard |
| Docker + Docker Compose | any | Run MongoDB |

### Step 1 — Clone the Repository

```bash
git clone https://github.com/your-username/SmartFlow.git
cd SmartFlow
```

### Step 2 — Configure Environment Variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
MONGO_URI=mongodb://admin:admin123@localhost:27017/
TWILIO_SID=your_twilio_sid
TWILIO_AUTH=your_twilio_auth_token
TWILIO_FROM=+1xxxxxxxxxx
TWILIO_TO=+91xxxxxxxxxx
```

> ⚠️ If you don't have Twilio credentials, the system still works fully — SMS alerts will just be silently skipped.

### Step 3 — Install Python Dependencies

```bash
# Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

### Step 4 — Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

## 🖥️ Running the Project

Start each component in its own terminal. Always activate the virtual environment (`venv\Scripts\activate`) before running Python scripts.

### Terminal 1 — Database
```bash
docker compose -f infra/docker-compose.yml up -d
```

### Terminal 2 — Backend API
```bash
python -m uvicorn src.backend.main:app --port 8001 --reload
```
API docs are available at [http://localhost:8001/docs](http://localhost:8001/docs)

### Terminal 3 — Frontend Dashboard
```bash
cd frontend
npm run dev
```
👉 Open [http://localhost:5173](http://localhost:5173) in your browser.

### Terminal 4 — AI Inference
```bash
python src/edge/inference3.py
```

### Terminal 5 — Heartbeat Monitor
```bash
python src/edge/heartbeat.py
```

### Terminal 6 — Watchdog
```bash
python src/edge/watchdog.py
```

---

## 📂 Project Structure

```
SmartFlow/
├── src/
│   ├── backend/           # FastAPI server, API routes, timing algorithm
│   │   ├── main.py        # Main application entry point
│   │   └── sms_utils.py   # Twilio SMS integration
│   ├── edge/              # Hardware-side runtime scripts
│   │   ├── inference3.py  # YOLO inference + frame processing
│   │   ├── heartbeat.py   # System health reporter
│   │   └── watchdog.py    # Process monitor + auto-restart
│   └── dashboard/         # (Legacy) Original Streamlit dashboard
├── frontend/              # React + Vite dashboard (NEW)
│   └── src/
│       ├── App.jsx        # Main app with routing & live data polling
│       ├── api.js         # Backend API client (fetch wrappers)
│       └── index.css      # Glassmorphic dark theme styles
├── infra/
│   └── docker-compose.yml # MongoDB container setup
├── models/                # Place your trained .pt model weights here
├── data/                  # Sample video files for the inference engine
├── ai/                    # Training experiments and datasets
├── .env.example           # Environment variable template
├── requirements.txt       # Python dependencies
└── Readme.md
```

---

## 🔑 Core Files Needed to Run (Pre-Trained Model)

If the model is already trained, you **only need these** to run the full system:

```
✅ src/backend/
✅ src/edge/
✅ frontend/
✅ infra/docker-compose.yml
✅ models/best.pt           ← your trained YOLO model weights
✅ data/sample2.mp4         ← camera feed video
✅ .env
✅ requirements.txt
```

The `ai/` and `experiments/` directories are only needed for research, re-training, or extending the model.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Object Detection | YOLO11 / YOLOv8 (Ultralytics) |
| Video Processing | OpenCV |
| Backend | FastAPI + Uvicorn |
| Database | MongoDB 6 (via Docker) |
| Dashboard | React 18 + Vite |
| Charts | Recharts |
| Icons | Lucide React |
| Alerting | Twilio SMS |
| Monitoring | psutil |

---
