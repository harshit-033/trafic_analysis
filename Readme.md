# 🚦 SmartFlow (AutoRoute)

**SmartFlow** is an intelligent, computer-vision-based traffic monitoring and dynamic signal-timing prototype. 

Using state-of-the-art YOLO object detection running on edge devices, SmartFlow watches live traffic camera feeds, counts varying vehicle types (cars, buses, trucks, bikes), and sends real-time data to a central FastAPI backend. The backend dynamically calculates optimal green-light times based on the weighted volume of traffic at each intersection approach, ensuring that busier roads get more time to flow. 

## ✨ Key Advantages & Features

* **Dynamic Adaptive Timing:** Escapes the inefficiency of static timers by granting green-light time proportionally to the actual live vehicle load. Heavy vehicles like buses/trucks are weighted higher.
* **Edge-to-Cloud Architecture:** Heavy video processing happens on the edge (the camera node). Only lightweight JSON telemetry is sent over the network to the database, saving massive amounts of bandwidth.
* **Resilient & Self-Healing:** Built-in Heartbeat and Watchdog scripts continuously monitor the edge node. If a camera disconnects or the AI process crashes, the watchdog automatically restarts it.
* **Live Analytics Dashboard:** A Streamlit-powered dashboard gives city planners and operators a real-time view into junction health, traffic composition pie charts, automated timings, and system alerts.
* **Instant SMS Alerts:** If a junction goes offline or enters a critical state, the system utilizes Twilio to instantly SMS the system administrator.

## 🏙️ Real-World Use Cases

1. **Smart City Intersections:** Reduce daily commuter congestion, lowering idle-engine carbon emissions and improving average travel speeds.
2. **Emergency Vehicle Corridors:** By tracking approaching traffic volumes, future modules can force green waves for ambulances and fire trucks.
3. **Traffic Auditing:** Automatically log daily vehicle counts to MongoDB, replacing the need for expensive manual traffic studies and road tubes.
4. **Temporary Construction Zones:** Deploy a portable camera and edge device to a construction site to dynamically manage alternating one-way traffic without a human flagger.

---

## 🏗️ Project Architecture

* **AI Edge Node (`src/edge`):** Runs YOLO object detection (`inference3.py`), a health monitoring script (`heartbeat.py`), and a self-recovery manager (`watchdog.py`). 
* **Backend Core (`src/backend`):** A FastAPI application that receives telemetry, interfaces with MongoDB for persistence, computes the signal timings, and dispatches Twilio SMS alerts.
* **Live Dashboard (`src/dashboard`):** A Streamlit application that polls the backend to visualize current system status.
* **Infrastructure (`infra/`):** Docker Compose configuration to instantly spin up the MongoDB instance.

---

## 🚀 Local Setup Guide

Follow these steps to run the complete SmartFlow system on your local machine.

### Prerequisites
* **Python 3.10+** (Tested on Python 3.13)
* **Docker Desktop** (For running the local MongoDB database)
* **NVIDIA GPU** (Optional but highly recommended for fast YOLO inference. Install CUDA 12.4 enabled PyTorch if you have an RTX card).

### 1. Clone & Configure
```bash
git clone https://github.com/yourusername/SmartFlow.git
cd SmartFlow

# Create a virtual environment
python -m venv venv

# Activate venv (Windows)
.\venv\Scripts\activate
# Activate venv (Mac/Linux)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables
Copy the provided example environment file and fill in your details:
```bash
cp .env.example .env
```
Inside `.env`, you can add your **Twilio** credentials if you want SMS alerts. The MongoDB credentials are set up for local Docker use by default.

### 3. Start the Database
Spin up the MongoDB container using Docker Compose:
```bash
docker compose -f infra/docker-compose.yml up -d
```

### 4. Run the Services
You need to run these components simultaneously. Open separate terminal windows, ensure your `venv` is activated in each, and run:

**Terminal A (Backend API):**
```bash
uvicorn src.backend.main:app --reload
```

**Terminal B (Live Dashboard):**
```bash
streamlit run src/dashboard/app.py
```

**Terminal C (Edge Inference):**
*Note: Make sure you have a test video placed at `data/sample2.mp4`.*
```bash
python src/edge/inference3.py
```

**Terminal D (Edge Heartbeat):**
```bash
python src/edge/heartbeat.py
```

> Instead of running the inference and heartbeat manually, you can test the self-healing system by just running `python src/edge/watchdog.py`. The watchdog will automatically spawn the AI and Heartbeat for you!

---

> You can replace sample2.mp4 with your own test video but keep your video in the same directory as sample2 and rename your video as sample2.mp4.


