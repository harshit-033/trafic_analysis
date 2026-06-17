#!/usr/bin/env python3
"""
Server runner and WebSocket simulator for Traffic Signal Timing System
Run this script to start the API server and WebSocket simulator
"""

import asyncio
import websockets
import json
import random
import time
import threading
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dataclasses import dataclass
from enum import Enum


# Same classes as main application
class SystemStatus(Enum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


@dataclass
class VehicleCount:
    bike: int = 0
    car: int = 0
    bus: int = 0
    truck: int = 0


@dataclass
class TimingResult:
    approach: str
    lane: str
    green_time: float
    weighted_count: float
    timestamp: datetime


class DynamicTimingAlgorithm:
    """Simple dynamic timing algorithm implementation"""

    def __init__(self, base_time: float = 10.0, k_factor: float = 30.0, max_capacity: float = 20.0):
        self.base_time = base_time
        self.k_factor = k_factor
        self.max_capacity = max_capacity

        # Vehicle type weights
        self.weights = {
            'bike': 0.5,
            'car': 1.0,
            'bus': 2.5,
            'truck': 2.0
        }

    def compute_weighted_count(self, counts: VehicleCount) -> float:
        """Compute weighted vehicle count based on vehicle types"""
        weighted_count = (
                counts.bike * self.weights['bike'] +
                counts.car * self.weights['car'] +
                counts.bus * self.weights['bus'] +
                counts.truck * self.weights['truck']
        )
        return weighted_count

    def compute_green_time(self, counts: VehicleCount) -> float:
        """Compute green time using dynamic timing algorithm"""
        weighted_count = self.compute_weighted_count(counts)
        green_time = self.base_time + self.k_factor * (weighted_count / self.max_capacity)
        return max(green_time, self.base_time)  # Ensure minimum base time


# Global state for the server
class ServerState:
    def __init__(self):
        self.detections = {}
        self.timings = {}
        self.system_status = SystemStatus.OK
        self.simulate_failure = False
        self.last_update = None
        self.timing_algorithm = DynamicTimingAlgorithm()
        self.websocket_clients = set()


server_state = ServerState()

# FastAPI Application
app = FastAPI(title="Traffic Signal Timing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": server_state.system_status.value,
        "timestamp": datetime.now().isoformat(),
        "simulate_failure": server_state.simulate_failure
    }


@app.post("/simulate_failure")
async def simulate_failure():
    """Simulate system failure for testing"""
    server_state.simulate_failure = not server_state.simulate_failure
    server_state.system_status = SystemStatus.OFFLINE if server_state.simulate_failure else SystemStatus.OK
    return {
        "simulate_failure": server_state.simulate_failure,
        "status": server_state.system_status.value
    }


@app.get("/compute_timing")
async def compute_timing():
    """Compute timing for all approaches/lanes"""
    if server_state.simulate_failure:
        raise HTTPException(status_code=503, detail="System is in failure mode")

    timings = []
    current_time = datetime.now()

    # Sample approaches and lanes
    approaches = ["North", "South", "East", "West"]
    lanes = ["Left", "Through", "Right"]

    for approach in approaches:
        for lane in lanes:
            # Get detection data for this approach/lane
            detection_key = f"{approach}_{lane}"
            counts = server_state.detections.get(detection_key, VehicleCount())

            # Compute timing
            green_time = server_state.timing_algorithm.compute_green_time(counts)
            weighted_count = server_state.timing_algorithm.compute_weighted_count(counts)

            timing_result = TimingResult(
                approach=approach,
                lane=lane,
                green_time=green_time,
                weighted_count=weighted_count,
                timestamp=current_time
            )

            timings.append({
                "approach": timing_result.approach,
                "lane": timing_result.lane,
                "green_time": round(timing_result.green_time, 1),
                "weighted_count": round(timing_result.weighted_count, 1),
                "timestamp": timing_result.timestamp.isoformat()
            })

    server_state.timings = {f"{t['approach']}_{t['lane']}": t for t in timings}
    return {"timings": timings}


# WebSocket Server for broadcasting detection data
async def websocket_handler(websocket, path):
    """Handle WebSocket connections"""
    print(f"New WebSocket connection from {websocket.remote_address}")
    server_state.websocket_clients.add(websocket)

    try:
        await websocket.wait_closed()
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        server_state.websocket_clients.discard(websocket)
        print(f"WebSocket connection closed: {websocket.remote_address}")


async def broadcast_detections():
    """Broadcast simulated detection data to all connected WebSocket clients"""
    approaches = ["North", "South", "East", "West"]
    lanes = ["Left", "Through", "Right"]

    while True:
        try:
            if server_state.websocket_clients and not server_state.simulate_failure:
                # Generate random detection data
                approach = random.choice(approaches)
                lane = random.choice(lanes)

                detections = {
                    "bike": random.randint(0, 5),
                    "car": random.randint(1, 12),
                    "bus": random.randint(0, 3),
                    "truck": random.randint(0, 2)
                }

                message = {
                    "approach": approach,
                    "lane": lane,
                    "detections": detections,
                    "timestamp": datetime.now().isoformat()
                }

                # Update server state
                detection_key = f"{approach}_{lane}"
                server_state.detections[detection_key] = VehicleCount(
                    bike=detections["bike"],
                    car=detections["car"],
                    bus=detections["bus"],
                    truck=detections["truck"]
                )
                server_state.last_update = datetime.now()

                # Broadcast to all connected clients
                if server_state.websocket_clients:
                    message_str = json.dumps(message)
                    disconnected = set()

                    for client in server_state.websocket_clients:
                        try:
                            await client.send(message_str)
                        except websockets.exceptions.ConnectionClosed:
                            disconnected.add(client)

                    # Remove disconnected clients
                    server_state.websocket_clients -= disconnected

                    print(
                        f"Broadcasted: {approach} {lane} - Cars: {detections['car']}, Total clients: {len(server_state.websocket_clients)}")

            await asyncio.sleep(2)  # Send updates every 2 seconds

        except Exception as e:
            print(f"Broadcast error: {e}")
            await asyncio.sleep(5)


def run_websocket_server():
    """Run WebSocket server"""

    async def main():
        # Start WebSocket server
        server = await websockets.serve(websocket_handler, "localhost", 8765)
        print("WebSocket server started on ws://localhost:8765")

        # Start broadcasting detection data
        broadcast_task = asyncio.create_task(broadcast_detections())

        try:
            await asyncio.gather(
                server.wait_closed(),
                broadcast_task
            )
        except KeyboardInterrupt:
            print("Shutting down WebSocket server...")
            broadcast_task.cancel()
            server.close()
            await server.wait_closed()

    asyncio.run(main())


def run_api_server():
    """Run FastAPI server"""
    print("Starting API server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    print("🚦 Traffic Signal Timing System Server")
    print("=" * 50)

    # Start WebSocket server in background thread
    websocket_thread = threading.Thread(target=run_websocket_server, daemon=True)
    websocket_thread.start()

    # Small delay to let WebSocket server start
    time.sleep(1)

    print("\nServers starting:")
    print("- API Server: http://localhost:8000")
    print("- WebSocket Server: ws://localhost:8765")
    print("- Health Check: http://localhost:8000/health")
    print("- Compute Timing: http://localhost:8000/compute_timing")
    print("\nTo run the Streamlit dashboard:")
    print("streamlit run traffic_dashboard.py")
    print("\nPress Ctrl+C to stop")

    try:
        # Run API server (this will block)
        run_api_server()
    except KeyboardInterrupt:
        print("\nShutting down servers...")