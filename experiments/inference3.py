import cv2
import requests
import threading
import time
from collections import Counter
from ultralytics import YOLO
from queue import Queue
import psutil
import sys

def startmodel():
    MODEL_PATH = "best.pt"
    VIDEO_PATH = "sample2.mp4"
    BACKEND_URL = "http://127.0.0.1:8000/detections"
    JUNCTION_ID = "J1"


    print("[INFO] Loading YOLO model...")
    model = YOLO(MODEL_PATH)

    # Video source
    cap = cv2.VideoCapture(VIDEO_PATH)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 270)

    if not cap.isOpened():
        print("[ERROR] Failed to open video source.")
        sys.exit(1)

    FRAME_SKIP = 2
    frame_id = 0

    send_queue = Queue()

    def backend_worker():

        while True:
            payload = send_queue.get()
            if payload is None:
                break
            try:
                r = requests.post(BACKEND_URL, json=payload, timeout=1)
                print(f"[BACKEND RESPONSE] {r.status_code}: {r.text[:80]}")
            except Exception as e:
                print("[ERROR] Backend POST failed:", e)
            send_queue.task_done()


    threading.Thread(target=backend_worker, daemon=True).start()

    print("[INFO] Model started. Press 'q' to stop.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[INFO] End of video or camera disconnected.")
                break

            frame_id += 1
            if frame_id % FRAME_SKIP != 0:
                continue

            start_time = time.time()
            results = model.predict(frame, imgsz=480, conf=0.25, device=0, verbose=False)

            detections = []
            class_names = model.names
            vehicle_labels = []

            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls)
                    conf = float(box.conf)
                    xyxy = [float(x) for x in box.xyxy[0]]
                    detections.append({"cls": cls_id, "conf": conf, "xyxy": xyxy})
                    vehicle_labels.append(class_names[cls_id])

            counts = dict(Counter(vehicle_labels))
            payload = {
                "junction_id": JUNCTION_ID,
                "ts": time.time(),
                "detections": detections,
                "counts": counts
            }


            send_queue.put(payload)


            annotated_frame = results[0].plot()


            fps = 1 / (time.time() - start_time)
            cv2.putText(annotated_frame, f"FPS: {fps:.2f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)


            cv2.putText(annotated_frame, f"Counts: {counts}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            cv2.imshow("Fast Detections", annotated_frame)


            if frame_id % 50 == 0:
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                print(f"[INFO] CPU: {cpu}% | RAM: {ram}% | FPS: {fps:.2f}")

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[INFO] Exiting...")
                break

    except KeyboardInterrupt:
        print("[INFO] Interrupted by user.")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        send_queue.put(None)  # Stop backend thread
        print("[INFO] Resources released. Program ended.")

if __name__ == "__main__":
    startmodel()
