import os
import uuid
import cv2
import easyocr
import numpy as np
from ultralytics import YOLO

# Model path relative to project
MODEL_PATH = os.path.join('runs', 'detect', 'train2', 'weights', 'best.pt')
model = YOLO(MODEL_PATH)

# EasyOCR reader
reader = easyocr.Reader(['en'], gpu=False)

# Folder for cropped images
CROPPED_FOLDER = os.path.join('static', 'uploads')
os.makedirs(CROPPED_FOLDER, exist_ok=True)


def merge_boxes(boxes, threshold=50):
    merged = []

    for box in boxes:
        x1, y1, x2, y2 = box
        found = False
        for i, m in enumerate(merged):
            mx1, my1, mx2, my2 = m
            if (abs(mx1 - x1) < threshold and abs(my1 - y1) < threshold) or \
               (abs(mx2 - x2) < threshold and abs(my2 - y2) < threshold):
                merged[i] = [min(mx1, x1), min(my1, y1),
                             max(mx2, x2), max(my2, y2)]
                found = True
                break
        if not found:
            merged.append([x1, y1, x2, y2])
    return merged


def process_license_plate(image_path):
    image = cv2.imread(image_path)
    results = model.predict(source=image_path, conf=0.25, verbose=False)[0]

    detections = results.boxes.xyxy.cpu().numpy() if results.boxes is not None else []
    if len(detections) == 0:
        return []

    # Merge overlapping or nearby boxes
    merged_boxes = merge_boxes(detections.tolist(), threshold=50)

    final_results = []

    for box in merged_boxes:
        x1, y1, x2, y2 = map(int, box)
        cropped = image[y1:y2, x1:x2]

        # Save cropped plate image
        filename = f"cropped_{uuid.uuid4().hex}.jpg"
        cropped_path = os.path.join(CROPPED_FOLDER, filename)
        cv2.imwrite(cropped_path, cropped)

        # Run OCR on cropped image
        gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
        ocr_result = reader.readtext(gray, detail=0)

        if ocr_result:
            # Merge multi-line text into one line
            detected_text = ''.join(
                [text.strip().upper().replace(" ", "") for text in ocr_result])
        else:
            detected_text = "No text detected"

        final_results.append({
            'image': cropped_path.replace("\\", "/"),  # for web view
            'text': detected_text
        })

    return final_results
