import cv2, requests, threading
from ultralytics import YOLO

MODEL = "weapon.pt"
BACKEND_URL = "http://127.0.0.1:8000/detections"
JUNCTION_ID = "J1"

model = YOLO(MODEL)

cap = cv2.VideoCapture("weapon.mp4")
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)   # smaller resolution → faster
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 270)

FRAME_SKIP = 3   # process every 4th frame
frame_id = 0

def send_async(payload):
    """Send detections to backend without blocking main loop"""
    try:
        requests.post(BACKEND_URL, json=payload, timeout=0.3)
    except:
        pass

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame_id += 1
    if frame_id % FRAME_SKIP != 0:
        continue

    # Run YOLO inference with smaller imgsz
    results = model.predict(
        frame,
        imgsz=480,     # smaller than 640 → faster
        conf=0.25,     # more detections, less strict
        device=0,      # GPU if available
        verbose=False
    )

    detections = []
    for r in results:
        for box in r.boxes:
            detections.append({
                "cls": int(box.cls),
                "conf": float(box.conf),
                "xyxy": [float(x) for x in box.xyxy[0]]
            })

    # Draw detections (disable if only backend needed)
    annotated_frame = results[0].plot()
    cv2.imshow("Fast Detections", annotated_frame)

    # Send detections asynchronously
    threading.Thread(
        target=send_async,
        args=({"junction": JUNCTION_ID, "detections": detections},),
        daemon=True
    ).start()

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
