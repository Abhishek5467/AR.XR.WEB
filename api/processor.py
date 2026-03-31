import cv2
import numpy as np
from ultralytics import YOLO
import mediapipe as mp

# utils
from utils import Distance, MidPoint
from utils import check_multiple_people  
from utils import draw_dotted_line       

YOLO_MODEL_PATH = "models/yolov8n.pt"

CONF_THRESHOLD = 0.6
MIN_BOX_AREA_RATIO = 0.10

CIRCLE_MIN_RADIUS = 15
CIRCLE_MAX_RADIUS = 35


class Processor:
    def __init__(self):
        # Models
        self.yolo_model = YOLO(YOLO_MODEL_PATH)

        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            min_detection_confidence=0.5,
            model_complexity=0,
        )

        # State
        self.prev_circle = None
        self.frame_counter = 0
        self.multi_person_detected = False

    def detect_pose(self, frame):
        results = self.pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        landmarks = []
        if results.pose_landmarks:
            for lm in results.pose_landmarks.landmark:
                landmarks.append([
                    lm.x * frame.shape[1],
                    lm.y * frame.shape[0],
                    lm.z
                ])

        return landmarks, results

    def detect_circle(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (17, 17), 0)

        circles = cv2.HoughCircles(
            blur,
            cv2.HOUGH_GRADIENT,
            1.2,
            75,
            param1=100,
            param2=75,
            minRadius=CIRCLE_MIN_RADIUS,
            maxRadius=CIRCLE_MAX_RADIUS,
        )

        chosen = None

        if circles is not None:
            circles = np.uint16(np.around(circles))

            for c in circles[0, :]:
                if chosen is None:
                    chosen = c

                if self.prev_circle is not None:
                    if Distance((chosen[0], chosen[1]), self.prev_circle[:2]) <= \
                       Distance((c[0], c[1]), self.prev_circle[:2]):
                        chosen = c

            self.prev_circle = chosen

        return chosen

    def process(self, frame):
        self.frame_counter += 1

        metadata = {
            "valve": None,
            "warnings": [],
            "multi_person": False
        }

        h, w, _ = frame.shape
        left_limit = w * 0.25
        right_limit = w * 0.75

        if self.frame_counter % 30 == 0:
            count = check_multiple_people(frame, self.yolo_model)
            self.multi_person_detected = count > 1

        metadata["multi_person"] = self.multi_person_detected

        circle = self.detect_circle(frame)

        if circle is not None:
            cv2.circle(frame, (circle[0], circle[1]), circle[2], (255, 0, 255), 2)

        landmarks, results = self.detect_pose(frame)

        if not landmarks or not results.pose_landmarks:
            return frame, metadata

        lm = results.pose_landmarks.landmark
        mp_pose = self.mp_pose

        # visibility
        def vis(idx):
            return lm[idx].visibility > 0.5

        hips_visible = vis(mp_pose.PoseLandmark.LEFT_HIP.value) and \
                       vis(mp_pose.PoseLandmark.RIGHT_HIP.value)

        shoulders_visible = vis(mp_pose.PoseLandmark.LEFT_SHOULDER.value) and \
                            vis(mp_pose.PoseLandmark.RIGHT_SHOULDER.value)

        nose_visible = vis(mp_pose.PoseLandmark.NOSE.value)

        # ---------- Face forward ----------
        face_forward = True

        if not (nose_visible and shoulders_visible):
            face_forward = False
        else:
            nose = landmarks[mp_pose.PoseLandmark.NOSE.value]
            left_sh = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            right_sh = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]

            shoulder_mid_x = (left_sh[0] + right_sh[0]) / 2
            shoulder_width = abs(left_sh[0] - right_sh[0])
            nose_offset = abs(nose[0] - shoulder_mid_x)

            if nose_offset > shoulder_width * 0.35:
                face_forward = False

        # ---------- Warnings ----------
        if not hips_visible:
            metadata["warnings"].append("Hips not visible")

        if not shoulders_visible:
            metadata["warnings"].append("Shoulders not visible")

        if not face_forward:
            metadata["warnings"].append("Face not forward")

        # ---------- Valve Logic ----------
        if shoulders_visible and hips_visible:

            mid_shoulder = MidPoint(
                landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value],
                landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value],
            )

            mid_hip = MidPoint(
                landmarks[mp_pose.PoseLandmark.LEFT_HIP.value],
                landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value],
            )

            x, y, _ = mid_shoulder
            d = Distance(mid_shoulder, mid_hip)

            if x < left_limit or x > right_limit:
                metadata["warnings"].append("Stand in center")

            valve_points = {
                "Aortic": (int(x - d / 16), int(y + d / 8)),
                "Pulmonary": (int(x + d / 16), int(y + d / 8)),
                "Tricuspid": (int(x + d / 16), int(y + d / 4)),
                "Mitral": (int(x + (d * 3) / 16), int(y + (d * 9) / 32)),
            }

            # draw
            for name, pt in valve_points.items():
                cv2.circle(frame, pt, 10, (0, 255, 0), 2)

            # ---------- Detection ----------
            if circle is not None:
                cx, cy = circle[0], circle[1]

                for name, pt in valve_points.items():
                    if Distance((cx, cy), pt) < 50:
                        metadata["valve"] = name
                        break

        # ---------- Guides ----------
        cx = w // 2
        cy = h // 2

        cv2.line(frame, (cx, 0), (cx, h), (0, 255, 255), 1)
        cv2.line(frame, (0, cy), (w, cy), (0, 255, 255), 1)

        draw_dotted_line(frame, left_limit)
        draw_dotted_line(frame, right_limit)

        return frame, metadata