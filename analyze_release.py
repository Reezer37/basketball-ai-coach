import argparse
import math
import os
import sys
import types
from itertools import chain
from pathlib import Path
from urllib.request import urlretrieve
import imageio.v3 as iio
import numpy as np
from PIL import Image, ImageDraw

# Newer MediaPipe imports optional drawing utilities that import cv2 at package
# import time. The app does not use OpenCV, and Streamlit Cloud may not provide
# libGL for cv2, so this stub prevents an optional import from failing startup.
sys.modules.setdefault("cv2", types.ModuleType("cv2"))

POSE_BACKEND = None
mp = None
mp_pose = None
mp_tasks_python = None
mp_tasks_vision = None

try:
    import mediapipe as mp

    if (
        not bool(int(os.getenv("FORCE_MEDIAPIPE_TASKS", "0")))
        and hasattr(mp, "solutions")
        and hasattr(mp.solutions, "pose")
    ):
        mp_pose = mp.solutions.pose
        POSE_BACKEND = "solutions"
except ModuleNotFoundError:
    mp = None

force_tasks = bool(int(os.getenv("FORCE_MEDIAPIPE_TASKS", "0")))

if POSE_BACKEND is None and not force_tasks:
    try:
        from mediapipe.python.solutions import pose as mp_pose

        POSE_BACKEND = "solutions"
    except (AttributeError, ModuleNotFoundError):
        pass

if POSE_BACKEND is None:
    try:
        if mp is None:
            import mediapipe as mp
        from mediapipe.tasks import python as mp_tasks_python
        from mediapipe.tasks.python import vision as mp_tasks_vision

        POSE_BACKEND = "tasks"
    except Exception as exc:
        print("MediaPipe pose backend is unavailable.")
        print(f"MediaPipe import error: {exc}")
        exit(2)

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="shot.mp4")
parser.add_argument("--output-image", default="release_analyzed.jpg")
parser.add_argument("--result", default="result.txt")
args = parser.parse_args()

input_video = args.input
output_image = args.output_image
result_path = args.result

POSE_CONNECTIONS = [
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
    (11, 23),
    (12, 24),
    (23, 24),
    (23, 25),
    (25, 27),
    (27, 29),
    (29, 31),
    (24, 26),
    (26, 28),
    (28, 30),
    (30, 32),
]

POSE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)
POSE_MODEL_PATH = Path("/tmp/basketball_ai_coach_pose_landmarker_lite.task")

RIGHT_SHOULDER = 12
RIGHT_ELBOW = 14
RIGHT_WRIST = 16
RIGHT_HIP = 24
RIGHT_KNEE = 26
RIGHT_ANKLE = 28
NOSE = 0


class SolutionsPoseDetector:
    def __enter__(self):
        self.pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.pose.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self.pose.__exit__(exc_type, exc, tb)

    def process(self, rgb):
        results = self.pose.process(rgb)
        if not results.pose_landmarks:
            return None
        return results.pose_landmarks.landmark


class TasksPoseDetector:
    def __enter__(self):
        ensure_pose_model()
        base_options = mp_tasks_python.BaseOptions(model_asset_path=str(POSE_MODEL_PATH))
        options = mp_tasks_vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_tasks_vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=False,
        )
        self.detector = mp_tasks_vision.PoseLandmarker.create_from_options(options)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.detector.close()

    def process(self, rgb):
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.detector.detect(image)
        if not result.pose_landmarks:
            return None
        return result.pose_landmarks[0]


def ensure_pose_model():
    if POSE_MODEL_PATH.exists() and POSE_MODEL_PATH.stat().st_size > 0:
        return
    try:
        urlretrieve(POSE_MODEL_URL, POSE_MODEL_PATH)
    except Exception as exc:
        print("Unable to download MediaPipe pose model.")
        print(f"Model download error: {exc}")
        exit(2)


def create_pose_detector():
    print("MediaPipe pose backend:", POSE_BACKEND)
    if POSE_BACKEND == "solutions":
        return SolutionsPoseDetector()
    return TasksPoseDetector()

def calc_angle(a, b, c):
    ab = [a[0] - b[0], a[1] - b[1]]
    cb = [c[0] - b[0], c[1] - b[1]]

    dot = ab[0] * cb[0] + ab[1] * cb[1]
    mag_ab = math.sqrt(ab[0] ** 2 + ab[1] ** 2)
    mag_cb = math.sqrt(cb[0] ** 2 + cb[1] ** 2)

    if mag_ab * mag_cb == 0:
        return None

    cos_angle = max(-1, min(1, dot / (mag_ab * mag_cb)))
    return math.degrees(math.acos(cos_angle))

try:
    frames = iio.imiter(input_video)
    first_frame = next(frames)
except Exception as exc:
    print(f"无法打开视频文件: {input_video}")
    print(f"视频读取错误: {exc}")
    exit(1)

try:
    metadata = iio.immeta(input_video)
except Exception:
    metadata = {}

video_height, video_width = first_frame.shape[:2]
fps = metadata.get("fps", 0)
frame_count = metadata.get("nframes", 0)
print(f"视频信息: {video_width}x{video_height}, fps={float(fps or 0):.2f}, frames={frame_count}")

release_data = None
best_wrist_y = 999999

lowest_hip_y = -1
dip_data = None

frame_index = 0
pose_frames = 0

with create_pose_detector() as pose:
    for frame in chain([first_frame], frames):
        frame = np.asarray(frame)
        if frame.ndim == 2:
            frame = np.stack([frame] * 3, axis=-1)
        if frame.shape[2] == 4:
            frame = frame[:, :, :3]

        rgb = np.ascontiguousarray(frame)
        landmarks = pose.process(rgb)

        if landmarks:
            pose_frames += 1
            h, w, _ = rgb.shape
            lm = landmarks

            wrist = lm[RIGHT_WRIST]
            hip = lm[RIGHT_HIP]

            wrist_y = wrist.y * h
            hip_y = hip.y * h

            # 出手瞬间：用手腕最高点近似
            if wrist_y < best_wrist_y:
                best_wrist_y = wrist_y
                release_data = {
                    "frame": rgb.copy(),
                    "landmarks": landmarks,
                    "frame_index": frame_index,
                    "width": w,
                    "height": h
                }

            # 下蹲最低点：用右髋最高 y 值近似，y 越大代表越低
            if hip_y > lowest_hip_y:
                lowest_hip_y = hip_y
                dip_data = {
                    "frame_index": frame_index,
                    "landmarks": landmarks,
                    "width": w,
                    "height": h
                }

        frame_index += 1

print("检测到人体姿态的帧数:", pose_frames)

if not release_data or not dip_data:
    print("没有检测到完整人体动作")
    exit(1)

# ===== 出手瞬间数据 =====
frame = release_data["frame"]
lm = release_data["landmarks"]
w = release_data["width"]
h = release_data["height"]

right_shoulder = lm[RIGHT_SHOULDER]
right_elbow = lm[RIGHT_ELBOW]
right_wrist = lm[RIGHT_WRIST]
right_hip = lm[RIGHT_HIP]
right_knee = lm[RIGHT_KNEE]
right_ankle = lm[RIGHT_ANKLE]
nose = lm[NOSE]

s = (right_shoulder.x * w, right_shoulder.y * h)
e = (right_elbow.x * w, right_elbow.y * h)
wr = (right_wrist.x * w, right_wrist.y * h)

hip = (right_hip.x * w, right_hip.y * h)
knee = (right_knee.x * w, right_knee.y * h)
ankle = (right_ankle.x * w, right_ankle.y * h)

elbow_angle = calc_angle(s, e, wr)
release_knee_angle = calc_angle(hip, knee, ankle)

# 出手高度：手腕比头高多少，正数越大越高
release_height = (nose.y * h) - (right_wrist.y * h)

# 身体前倾：肩膀相对髋部的水平偏移
body_lean = (right_shoulder.x * w) - (right_hip.x * w)

# ===== 下蹲最低点膝盖角度 =====
dip_lm = dip_data["landmarks"]
dw = dip_data["width"]
dh = dip_data["height"]

dip_hip_lm = dip_lm[RIGHT_HIP]
dip_knee_lm = dip_lm[RIGHT_KNEE]
dip_ankle_lm = dip_lm[RIGHT_ANKLE]

dip_hip = (dip_hip_lm.x * dw, dip_hip_lm.y * dh)
dip_knee = (dip_knee_lm.x * dw, dip_knee_lm.y * dh)
dip_ankle = (dip_ankle_lm.x * dw, dip_ankle_lm.y * dh)

dip_knee_angle = calc_angle(dip_hip, dip_knee, dip_ankle)

# 膝盖伸展幅度：越大说明下肢参与越明显
knee_extension = release_knee_angle - dip_knee_angle

image = Image.fromarray(frame)
draw = ImageDraw.Draw(image)
landmarks = release_data["landmarks"]

for start, end in POSE_CONNECTIONS:
    a = landmarks[start]
    b = landmarks[end]
    ax, ay = int(a.x * w), int(a.y * h)
    bx, by = int(b.x * w), int(b.y * h)
    draw.line((ax, ay, bx, by), fill=(245, 245, 245), width=3)

for landmark in landmarks:
    x, y = int(landmark.x * w), int(landmark.y * h)
    draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(220, 0, 0), outline=(255, 255, 255), width=1)

draw.text((30, 30), f"Elbow: {elbow_angle:.1f}  Knee: {release_knee_angle:.1f}", fill=(255, 255, 255))
image.save(output_image)

print("出手瞬间帧号:", release_data["frame_index"])
print("下蹲最低点帧号:", dip_data["frame_index"])

flow_frames = release_data["frame_index"] - dip_data["frame_index"]
print("发力到出手帧数:", flow_frames)

print("出手瞬间手肘角度:", round(elbow_angle, 1))
print("出手高度（相对头部）:", round(release_height, 1))
print("身体前倾程度:", round(body_lean, 1))
print("最低点膝盖角度:", round(dip_knee_angle, 1))
print("出手时膝盖角度:", round(release_knee_angle, 1))
print("膝盖伸展幅度:", round(knee_extension, 1))
print("已保存分析截图:", output_image)

with open(result_path, "w") as f:
    f.write(
        f"{round(elbow_angle,1)},"
        f"{round(release_height,1)},"
        f"{round(body_lean,1)},"
        f"{round(dip_knee_angle,1)},"
        f"{round(release_knee_angle,1)},"
        f"{round(knee_extension,1)},"
	f"{flow_frames}"
    )
