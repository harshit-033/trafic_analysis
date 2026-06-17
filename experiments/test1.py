import cv2
import time
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from ultralytics import YOLO
import threading


class FaceCounter:
    def __init__(self):
        # Load YOLOv8 model (you can use yolov8n.pt, yolov8s.pt, yolov8m.pt, yolov8l.pt, yolov8x.pt)
        try:
            self.model = YOLO('yolov8n.pt')  # Lightweight version for faster processing
        except:
            print("Downloading YOLOv8 model...")
            self.model = YOLO('yolov8n.pt')  # This will download the model if not present

        # Initialize camera
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Counters and timing
        self.minute_counts = defaultdict(int)
        self.current_faces = 0
        self.last_minute_report = datetime.now()
        self.total_detections = 0

        # Display settings
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.7
        self.font_thickness = 2

        # Colors (BGR format)
        self.bbox_color = (0, 255, 0)  # Green for bounding boxes
        self.text_color = (255, 255, 255)  # White for text
        self.bg_color = (0, 0, 0)  # Black background for text

    def detect_faces(self, frame):
        """Detect faces using YOLOv8 (person class)"""
        results = self.model(frame, verbose=False)
        faces_detected = 0

        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # Class 0 is 'person' in COCO dataset
                    if int(box.cls) == 0:  # Person class
                        confidence = float(box.conf)
                        if confidence > 0.5:  # Confidence threshold
                            faces_detected += 1

                            # Get bounding box coordinates
                            x1, y1, x2, y2 = map(int, box.xyxy[0])

                            # Draw bounding box
                            cv2.rectangle(frame, (x1, y1), (x2, y2), self.bbox_color, 2)

                            # Draw confidence score
                            label = f'Person: {confidence:.2f}'
                            label_size = cv2.getTextSize(label, self.font, self.font_scale, self.font_thickness)[0]
                            cv2.rectangle(frame, (x1, y1 - label_size[1] - 10),
                                          (x1 + label_size[0], y1), self.bg_color, -1)
                            cv2.putText(frame, label, (x1, y1 - 5),
                                        self.font, self.font_scale, self.text_color, self.font_thickness)

        return faces_detected, frame

    def update_counts(self, faces_count):
        """Update face counts and check if a minute has passed"""
        self.current_faces = faces_count
        current_time = datetime.now()
        current_minute = current_time.replace(second=0, microsecond=0)

        # Update minute count with maximum faces seen in this minute
        self.minute_counts[current_minute] = max(self.minute_counts[current_minute], faces_count)

        # Check if a minute has passed since last report
        if current_time - self.last_minute_report >= timedelta(minutes=1):
            self.print_minute_report()
            self.last_minute_report = current_time

    def print_minute_report(self):
        """Print minute-by-minute face count report"""
        print("\n" + "=" * 50)
        print("MINUTE-BY-MINUTE FACE COUNT REPORT")
        print("=" * 50)

        # Sort by time and display last 10 minutes
        sorted_times = sorted(self.minute_counts.keys(), reverse=True)[:10]

        for minute_time in sorted_times:
            count = self.minute_counts[minute_time]
            time_str = minute_time.strftime("%H:%M")
            print(f"{time_str} - Max faces detected: {count}")

        print("=" * 50)

    def add_overlay_text(self, frame):
        """Add informational overlay to the frame"""
        height, width = frame.shape[:2]

        # Create semi-transparent overlay for text background
        overlay = frame.copy()

        # Current face count
        face_text = f"Current Faces: {self.current_faces}"
        cv2.putText(overlay, face_text, (10, 30),
                    self.font, self.font_scale, self.text_color, self.font_thickness)

        # Current time
        current_time = datetime.now().strftime("%H:%M:%S")
        time_text = f"Time: {current_time}"
        cv2.putText(overlay, time_text, (10, 60),
                    self.font, self.font_scale, self.text_color, self.font_thickness)

        # Instructions
        instruction_text = "Press 'q' to quit, 'r' for report"
        cv2.putText(overlay, instruction_text, (10, height - 20),
                    self.font, 0.5, self.text_color, 1)

        return overlay

    def run(self):
        """Main loop for face detection"""
        print("Starting YOLOv8 Face Detection...")
        print("Press 'q' to quit")
        print("Press 'r' to see minute report")
        print("Generating reports every minute automatically...\n")

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Could not read frame from camera")
                break

            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)

            # Detect faces
            faces_count, processed_frame = self.detect_faces(frame)

            # Update counts
            self.update_counts(faces_count)

            # Add overlay information
            final_frame = self.add_overlay_text(processed_frame)

            # Display the frame
            cv2.imshow('YOLOv8 Face Detection', final_frame)

            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.print_minute_report()

        # Cleanup
        self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        print("\nFinal Report:")
        self.print_minute_report()

        self.cap.release()
        cv2.destroyAllWindows()
        print("Face detection stopped.")


def main():
    detector = FaceCounter()
    try:
        detector.run()
    except KeyboardInterrupt:
        print("\nDetection interrupted by user")
        detector.cleanup()
    except Exception as e:
        print(f"Error occurred: {e}")
        detector.cleanup()


if __name__ == "__main__":
    main()