import cv2, requests
from ultralytics import YOLO

MODEL = "runs/detect/train7/weights/best.pt"
BACKEND_URL = "http://127.0.0.1:8000/detections"
JUNCTION_ID = "J1"

model = YOLO(MODEL)

cap = cv2.VideoCapture("data/sample.mp4")
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

FRAME_SKIP = 2   # process every 3rd frame
frame_id = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame_id += 1
    if frame_id % FRAME_SKIP != 0:
        continue

    # Run YOLO inference
    results = model.predict(
        frame,
        imgsz=640,
        conf=0.3,       # lowered so you see more boxes
        device=0,       # use GPU if available
        verbose=False
    )

    detections = []
    for r in results:
        for box in r.boxes:
            detections.append({
                "cls": int(box.cls),
                "conf": float(box.conf),
                "xyxy": box.xyxy.tolist()
            })

    # Draw results on frame
    annotated_frame = results[0].plot()

    # Show the frame
    cv2.imshow("Detections", annotated_frame)

    # Send results to backend
    try:
        requests.post(
            BACKEND_URL,
            json={"junction": JUNCTION_ID, "detections": detections},
            timeout=0.5
        )
    except Exception as e:
        print(f"[WARN] Backend not reachable: {e}")

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
