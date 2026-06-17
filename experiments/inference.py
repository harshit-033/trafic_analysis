# ai/inference.py
import cv2, time, requests
from ultralytics import YOLO
from collections import Counter

MODEL = "Weapon.pt"
BACKEND_URL = "http://127.0.0.1:8000/detections"  # Backend API
JUNCTION_ID = "J1"

# Load YOLO model
model = YOLO(MODEL)
cap = cv2.VideoCapture("weapon.mp4")  # Replace with RTSP for live

while True:
    ret, frame = cap.read()
    if not ret:
        print("[INFO] End of video or camera disconnected.")
        break

    # Run inference
    results = model(frame, imgsz=640, conf=0.25)[0]

    detections = []
    class_names = model.names  # {0:'person',1:'bicycle',2:'car',...}
    vehicle_labels = []

    for box in results.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        xyxy = [float(x) for x in box.xyxy[0].tolist()]

        detections.append({"cls": cls_id, "conf": conf, "xyxy": xyxy})
        vehicle_labels.append(class_names[cls_id])

        # Optional: draw boxes for debugging
        cv2.rectangle(frame, (int(xyxy[0]), int(xyxy[1])),
                             (int(xyxy[2]), int(xyxy[3])), (0,255,0), 2)
        cv2.putText(frame, f"{class_names[cls_id]} {conf:.2f}",
                    (int(xyxy[0]), int(xyxy[1]-5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

    # Count vehicles per class
    counts = dict(Counter(vehicle_labels))

    # Create payload
    payload = {
        "junction_id": JUNCTION_ID,
        "ts": time.time(),
        "detections": detections,
        "counts": counts
    }

    try:
        r = requests.post(BACKEND_URL, json=payload, timeout=1.0)
        print("[POSTED]", payload)
    except Exception as e:
        print("Post failed:", e)

    # Show debug window (comment out if running headless on edge device)
    cv2.imshow("Inference", frame)

    # Control FPS (adjust as needed)
    time.sleep(0.5)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
