# SmartFlow - Intelligent Traffic Monitoring System

SmartFlow is a computer vision-based smart traffic signal prototype. It uses YOLO object detection to identify and count vehicles from traffic camera footage, sends live detection results to a FastAPI backend, stores events in MongoDB, computes adaptive green-light timings using weighted vehicle counts, and visualizes real-time traffic, system health, alerts, and signal timings through a React/Vite dashboard. Edge scripts provide heartbeat monitoring and watchdog-based recovery.

## Project Structure (Runtime Essentials)

If the model is already trained, you only need the following core components to run the system:

- **`src/backend/`**: FastAPI server, timing logic, and MongoDB integration.
- **`src/edge/`**: Runtime scripts for the physical intersection (`inference3.py`, `heartbeat.py`, `watchdog.py`).
- **`frontend/`**: The React/Vite dashboard UI.
- **`infra/`**: Docker Compose file for launching MongoDB.
- **`models/best.pt`**: Your trained YOLO model weights.
- **`data/sample2.mp4`**: Sample video file acting as the camera feed.
- **`.env`**: Environment variables (Twilio credentials, Mongo URI).
- **`requirements.txt`**: Python dependencies.

*(Other folders like `ai/`, `experiments/`, and `docs/` are useful for research and model training but are not required to run the live dashboard and inference system).*

## How to Run the Project

### 1. Start the Database (MongoDB)
Start the MongoDB container from the project root:
```bash
docker compose -f infra/docker-compose.yml up -d
```

### 2. Start the FastAPI Backend
Activate your virtual environment and start the backend on port 8001:
```bash
python -m uvicorn src.backend.main:app --port 8001 --reload
```

### 3. Start the React Frontend
Navigate to the frontend directory and start the Vite development server:
```bash
cd frontend
npm install
npm run dev
```
Access the dashboard at `http://localhost:5173/`.

### 4. Start the Edge Services
Open a new terminal for each of the following commands in the project root to simulate the hardware running at the junction:

**Heartbeat Monitor:**
```bash
python src/edge/heartbeat.py
```

**AI Inference:**
```bash
python src/edge/inference3.py
```

**Watchdog:**
```bash
python src/edge/watchdog.py
```
=======
> Instead of running the inference and heartbeat manually, you can test the self-healing system by just running `python src/edge/watchdog.py`. The watchdog will automatically spawn the AI and Heartbeat for you!

---

> You can replace sample2.mp4 with your own test video but keep your video in the same directory as sample2 and rename your video as sample2.mp4.



