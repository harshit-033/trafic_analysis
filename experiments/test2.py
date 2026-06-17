import cv2
import numpy as np
from ultralytics import YOLO
import argparse
import os


class ImagePersonCounter:
    def __init__(self):
        # Load YOLOv8 model
        try:
            self.model = YOLO('yolov8n.pt')  # Lightweight version for faster processing
        except:
            print("Downloading YOLOv8 model...")
            self.model = YOLO('yolov8n.pt')  # This will download the model if not present

        # Display settings
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.7
        self.font_thickness = 2

        # Colors (BGR format)
        self.bbox_color = (0, 255, 0)  # Green for bounding boxes
        self.text_color = (255, 255, 255)  # White for text
        self.bg_color = (0, 0, 0)  # Black background for text

    def detect_persons(self, image):
        """Detect persons using YOLOv8"""
        results = self.model(image, verbose=False)
        persons_detected = 0
        detections = []

        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # Class 0 is 'person' in COCO dataset
                    if int(box.cls) == 0:  # Person class
                        confidence = float(box.conf)
                        if confidence > 0.5:  # Confidence threshold
                            persons_detected += 1

                            # Get bounding box coordinates
                            x1, y1, x2, y2 = map(int, box.xyxy[0])

                            detections.append({
                                'bbox': (x1, y1, x2, y2),
                                'confidence': confidence
                            })

        return persons_detected, detections

    def draw_detections(self, image, detections):
        """Draw bounding boxes and labels on the image"""
        annotated_image = image.copy()

        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            confidence = detection['confidence']

            # Draw bounding box
            cv2.rectangle(annotated_image, (x1, y1), (x2, y2), self.bbox_color, 2)

            # Draw confidence score
            label = f'Person: {confidence:.2f}'
            label_size = cv2.getTextSize(label, self.font, self.font_scale, self.font_thickness)[0]
            cv2.rectangle(annotated_image, (x1, y1 - label_size[1] - 10),
                          (x1 + label_size[0], y1), self.bg_color, -1)
            cv2.putText(annotated_image, label, (x1, y1 - 5),
                        self.font, self.font_scale, self.text_color, self.font_thickness)

        return annotated_image

    def add_count_text(self, image, person_count):
        """Add person count text to the image"""
        annotated_image = image.copy()

        # Add person count at the top
        count_text = f"Persons detected: {person_count}"
        text_size = cv2.getTextSize(count_text, self.font, 1.0, 2)[0]

        # Add background rectangle for better visibility
        cv2.rectangle(annotated_image, (10, 10),
                      (text_size[0] + 20, text_size[1] + 20),
                      self.bg_color, -1)

        cv2.putText(annotated_image, count_text, (15, text_size[1] + 15),
                    self.font, 1.0, (0, 255, 255), 2)  # Yellow text

        return annotated_image

    def process_image(self, image_path, show_result=True, save_result=False, output_path=None):
        """Process a single image and return person count"""

        # Check if image file exists
        if not os.path.exists(image_path):
            print(f"Error: Image file '{image_path}' not found.")
            return None

        # Load the image
        try:
            image = cv2.imread(image_path)
            if image is None:
                print(f"Error: Could not load image from '{image_path}'")
                return None
        except Exception as e:
            print(f"Error loading image: {e}")
            return None

        print(f"Processing image: {image_path}")
        print(f"Image dimensions: {image.shape[1]}x{image.shape[0]}")

        # Detect persons
        person_count, detections = self.detect_persons(image)

        print(f"Number of persons detected: {person_count}")

        if person_count > 0:
            print("Detection details:")
            for i, detection in enumerate(detections, 1):
                x1, y1, x2, y2 = detection['bbox']
                confidence = detection['confidence']
                print(f"  Person {i}: Confidence {confidence:.2f}, "
                      f"BBox ({x1}, {y1}, {x2}, {y2})")

        # Create annotated image
        if show_result or save_result:
            annotated_image = self.draw_detections(image, detections)
            annotated_image = self.add_count_text(annotated_image, person_count)

            if show_result:
                # Display the result
                cv2.imshow('Person Detection Result', annotated_image)
                print("\nPress any key to close the window...")
                cv2.waitKey(0)
                cv2.destroyAllWindows()

            if save_result:
                if output_path is None:
                    # Generate output filename
                    name, ext = os.path.splitext(image_path)
                    output_path = f"{name}_detected{ext}"

                cv2.imwrite(output_path, annotated_image)
                print(f"Annotated image saved to: {output_path}")

        return person_count


def main():
    parser = argparse.ArgumentParser(description='Count persons in an image using YOLOv8')
    parser.add_argument('4.png', help='Path to the input image')
    parser.add_argument('--no-show', action='store_true',
                        help='Don\'t display the result image')
    parser.add_argument('--save', action='store_true',
                        help='Save the annotated image')
    parser.add_argument('--output', '-o', type=str,
                        help='Output path for the annotated image')

    args = parser.parse_args()

    # Create counter instance
    counter = ImagePersonCounter()

    try:
        # Process the image
        person_count = counter.process_image(
            image_path=args.image_path,
            show_result=not args.no_show,
            save_result=args.save,
            output_path=args.output
        )

        if person_count is not None:
            print(f"\nFinal count: {person_count} person(s) detected in the image.")

    except Exception as e:
        print(f"Error occurred: {e}")


# Alternative simple function for direct use
def count_persons_in_image(image_path):
    """Simple function to count persons in an image and return the count"""
    counter = ImagePersonCounter()
    return counter.process_image(image_path, show_result=False, save_result=False)


if __name__ == "__main__":
    main()