import cv2
import mediapipe as mp
import numpy as np
from ultralytics import YOLO

def Distance(p1, p2):
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def MidPoint(p1, p2):
    return [(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2, 0]

def check_multiple_people(frame, yolo_model):
    results = yolo_model(frame, verbose=False)[0]

    person_count = 0
    h, w, _ = frame.shape

    for box in results.boxes:

        cls_id = int(box.cls[0])
        conf = float(box.conf[0])

        if cls_id != 0:
            continue

        # ---------- FILTER 1: confidence ----------
        if conf < 0.6:
            continue

        # ---------- FILTER 2: size ----------
        x1, y1, x2, y2 = box.xyxy[0]
        box_area = (x2 - x1) * (y2 - y1)
        frame_area = w * h

        # ignore tiny "people"
        if box_area < 0.10 * frame_area:
            continue

        person_count += 1

    return person_count

def draw_dotted_line(img, x, color=(0, 180, 0), gap=30):

    h, _ = img.shape[:2]

    x = int(x)
    y = 0
    while y < h:
        cv2.line(img, (x, y), (x, min(y + 10, h)), color, 1)
        y += gap
