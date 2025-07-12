import cv2
import pytesseract
import numpy as np
import os
import uuid
from difflib import SequenceMatcher

# Tesseract config
tess_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

# Path to store cropped plates
CROPPED_FOLDER = os.path.join('static', 'cropped')
os.makedirs(CROPPED_FOLDER, exist_ok=True)


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def non_max_suppression(boxes, overlapThresh=0.3):
    if len(boxes) == 0:
        return []
    boxes = np.array(boxes)
    if boxes.dtype.kind == "i":
        boxes = boxes.astype("float")
    pick = []
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 0] + boxes[:, 2]
    y2 = boxes[:, 1] + boxes[:, 3]
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = np.argsort(y2)
    while len(idxs) > 0:
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)
        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)
        overlap = (w * h) / area[idxs[:last]]
        idxs = np.delete(idxs, np.concatenate(
            ([last], np.where(overlap > overlapThresh)[0])))
    return boxes[pick].astype("int")


def detect_license_regions(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.bilateralFilter(gray, 11, 17, 17)
    edged = cv2.Canny(blur, 30, 200)
    contours, _ = cv2.findContours(
        edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if 2 < w/h < 8 and w > 100 and h > 30:
            boxes.append((x, y, w, h))
    return non_max_suppression(boxes)


def process_license_plate(image_path):
    image = cv2.imread(image_path)
    detected_boxes = detect_license_regions(image)
    results = []
    cropped_paths = []

    for i, (x, y, w, h) in enumerate(detected_boxes):
        roi = image[y:y+h, x:x+w]
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(
            gray_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(
            thresh, config=tess_config).strip().replace(" ", "").upper()
        if 6 <= len(text) <= 12:
            cropped_filename = f"{uuid.uuid4().hex}.png"
            cropped_path = os.path.join(CROPPED_FOLDER, cropped_filename)
            cv2.imwrite(cropped_path, roi)
            results.append(text)
            cropped_paths.append(cropped_path)

    # Deduplicate similar texts
    final_results = []
    for text in results:
        if all(similar(text, existing) < 0.85 for existing in final_results):
            final_results.append(text)

    return final_results, cropped_paths
