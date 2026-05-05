import argparse
import json
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
parser.add_argument("--stability", default="")
parser.add_argument("--segments", default="")
args = parser.parse_args()

input_video = args.input
output_image = args.output_image
result_path = args.result
stability_path = args.stability
segments_path = args.segments

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
LEFT_SHOULDER = 11
LEFT_ELBOW = 13
LEFT_WRIST = 15
LEFT_HIP = 23
LEFT_ANKLE = 27
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


def calc_release_metrics(release_record, dip_record):
    lm = release_record["landmarks"]
    w = release_record["width"]
    h = release_record["height"]

    right_shoulder = lm[RIGHT_SHOULDER]
    left_shoulder = lm[LEFT_SHOULDER]
    right_elbow = lm[RIGHT_ELBOW]
    right_wrist = lm[RIGHT_WRIST]
    right_hip = lm[RIGHT_HIP]
    left_hip = lm[LEFT_HIP]
    right_knee = lm[RIGHT_KNEE]
    right_ankle = lm[RIGHT_ANKLE]
    left_ankle = lm[LEFT_ANKLE]
    nose = lm[NOSE]

    s = (right_shoulder.x * w, right_shoulder.y * h)
    e = (right_elbow.x * w, right_elbow.y * h)
    wr = (right_wrist.x * w, right_wrist.y * h)
    hip = (right_hip.x * w, right_hip.y * h)
    knee = (right_knee.x * w, right_knee.y * h)
    ankle = (right_ankle.x * w, right_ankle.y * h)

    elbow_angle = calc_angle(s, e, wr)
    release_knee_angle = calc_angle(hip, knee, ankle)

    dip_lm = dip_record["landmarks"]
    dw = dip_record["width"]
    dh = dip_record["height"]
    dip_hip_lm = dip_lm[RIGHT_HIP]
    dip_knee_lm = dip_lm[RIGHT_KNEE]
    dip_ankle_lm = dip_lm[RIGHT_ANKLE]

    dip_hip = (dip_hip_lm.x * dw, dip_hip_lm.y * dh)
    dip_knee = (dip_knee_lm.x * dw, dip_knee_lm.y * dh)
    dip_ankle = (dip_ankle_lm.x * dw, dip_ankle_lm.y * dh)
    dip_knee_angle = calc_angle(dip_hip, dip_knee, dip_ankle)

    if elbow_angle is None or release_knee_angle is None or dip_knee_angle is None:
        return None

    release_height = (nose.y * h) - (right_wrist.y * h)
    body_lean = (right_shoulder.x * w) - (right_hip.x * w)
    knee_extension = release_knee_angle - dip_knee_angle
    flow_frames = release_record["frame_index"] - dip_record["frame_index"]
    body_points = [nose, left_shoulder, right_shoulder, left_hip, right_hip, left_ankle, right_ankle]
    min_y = min(point.y * h for point in body_points)
    max_y = max(point.y * h for point in body_points)
    body_height_px = max(1.0, max_y - min_y)
    body_center_x = (
        left_shoulder.x * w + right_shoulder.x * w + left_hip.x * w + right_hip.x * w
    ) / 4
    shoulder_width_px = abs((left_shoulder.x - right_shoulder.x) * w)
    hip_width_px = abs((left_hip.x - right_hip.x) * w)

    return {
        "frame_index": release_record["frame_index"],
        "elbow_angle": elbow_angle,
        "release_height": release_height,
        "body_lean": body_lean,
        "dip_knee_angle": dip_knee_angle,
        "release_knee_angle": release_knee_angle,
        "knee_extension": knee_extension,
        "flow_frames": flow_frames,
        "body_center_x_norm": body_center_x / w,
        "body_height_norm": body_height_px / h,
        "shoulder_width_ratio": shoulder_width_px / body_height_px,
        "hip_width_ratio": hip_width_px / body_height_px,
    }


def stddev(values):
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def get_joint_y(landmarks, landmark_index, height):
    return landmarks[landmark_index].y * height


def get_visibility(landmark):
    return float(getattr(landmark, "visibility", 1.0) or 0.0)


def pose_quality(landmarks, width, height):
    core_indices = [NOSE, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP]
    limb_indices = core_indices + [LEFT_WRIST, RIGHT_WRIST, LEFT_ANKLE, RIGHT_ANKLE]
    core_visibility = sum(get_visibility(landmarks[index]) for index in core_indices) / len(core_indices)
    visible_points = [landmarks[index] for index in limb_indices if get_visibility(landmarks[index]) > 0.2]

    if core_visibility < 0.35 or len(visible_points) < 6:
        return {"valid": False, "reason": "low_visibility"}

    xs = [point.x * width for point in visible_points]
    ys = [point.y * height for point in visible_points]
    box_width = max(xs) - min(xs)
    box_height = max(ys) - min(ys)
    body_height_norm = box_height / height
    box_aspect = box_width / max(box_height, 1)

    left_shoulder = landmarks[LEFT_SHOULDER]
    right_shoulder = landmarks[RIGHT_SHOULDER]
    left_hip = landmarks[LEFT_HIP]
    right_hip = landmarks[RIGHT_HIP]
    shoulder_center_y = (left_shoulder.y + right_shoulder.y) * height / 2
    hip_center_y = (left_hip.y + right_hip.y) * height / 2
    torso_height_norm = abs(hip_center_y - shoulder_center_y) / height

    if body_height_norm < 0.16:
        return {"valid": False, "reason": "pose_too_small"}
    if box_aspect > 1.65:
        return {"valid": False, "reason": "unrealistic_pose_width"}
    if torso_height_norm < 0.04:
        return {"valid": False, "reason": "flat_torso"}

    return {
        "valid": True,
        "body_height_norm": body_height_norm,
        "box_aspect": box_aspect,
        "core_visibility": core_visibility,
    }


def get_shooting_side_measurements(landmarks, height):
    nose_y = get_joint_y(landmarks, NOSE, height)
    right_wrist_y = get_joint_y(landmarks, RIGHT_WRIST, height)
    left_wrist_y = get_joint_y(landmarks, LEFT_WRIST, height)
    right_shoulder_y = get_joint_y(landmarks, RIGHT_SHOULDER, height)
    left_shoulder_y = get_joint_y(landmarks, LEFT_SHOULDER, height)

    right_release_height = nose_y - right_wrist_y
    left_release_height = nose_y - left_wrist_y
    if left_release_height > right_release_height:
        return {
            "side": "left",
            "wrist_y": left_wrist_y,
            "elbow_y": get_joint_y(landmarks, LEFT_ELBOW, height),
            "shoulder_y": left_shoulder_y,
            "release_height": left_release_height,
        }

    return {
        "side": "right",
        "wrist_y": right_wrist_y,
        "elbow_y": get_joint_y(landmarks, RIGHT_ELBOW, height),
        "shoulder_y": right_shoulder_y,
        "release_height": right_release_height,
    }


def load_segments(path):
    if not path:
        return []
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

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
rejected_pose_frames = 0
pose_motion = []

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
            quality = pose_quality(landmarks, rgb.shape[1], rgb.shape[0])
            if not quality["valid"]:
                rejected_pose_frames += 1
                frame_index += 1
                continue

            pose_frames += 1
            h, w, _ = rgb.shape
            lm = landmarks

            hip = lm[RIGHT_HIP]
            nose = lm[NOSE]
            shooting = get_shooting_side_measurements(lm, h)

            hip_y = hip.y * h
            nose_y = nose.y * h
            wrist_y = shooting["wrist_y"]
            release_height_now = shooting["release_height"]

            pose_motion.append(
                {
                    "frame_index": frame_index,
                    "wrist_y": wrist_y,
                    "elbow_y": shooting["elbow_y"],
                    "shoulder_y": shooting["shoulder_y"],
                    "nose_y": nose_y,
                    "hip_y": hip_y,
                    "release_height": release_height_now,
                    "shooting_side": shooting["side"],
                    "body_height_norm": quality["body_height_norm"],
                    "box_aspect": quality["box_aspect"],
                    "landmarks": landmarks,
                    "width": w,
                    "height": h,
                }
            )

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
print("过滤掉低质量姿态帧数:", rejected_pose_frames)

if not release_data or not dip_data:
    print("没有检测到完整人体动作")
    exit(1)

detected_ratio = pose_frames / max(frame_index, 1)
lowest_wrist_y = max((item["wrist_y"] for item in pose_motion), default=best_wrist_y)
wrist_lift = lowest_wrist_y - best_wrist_y
release_frame_motion = next(
    (item for item in pose_motion if item["frame_index"] == release_data["frame_index"]),
    None,
)
release_above_head = bool(release_frame_motion and release_frame_motion["release_height"] > -0.04 * video_height)
release_above_shoulder = bool(
    release_frame_motion and release_frame_motion["wrist_y"] < release_frame_motion["shoulder_y"] + 0.03 * video_height
)
enough_lift = wrist_lift > 0.08 * video_height

if detected_ratio < 0.2 or not enough_lift or not (release_above_head or release_above_shoulder):
    print("NO_SHOOTING_MOTION")
    print("没有识别到清晰的投篮出手动作")
    print(f"姿态检测比例: {detected_ratio:.2f}")
    print(f"手腕上升距离: {wrist_lift:.1f}px")
    exit(3)

pose_records = sorted(pose_motion, key=lambda item: item["frame_index"])
fps_value = float(fps or 25)
dip_window_frames = max(30, int(fps_value * 12))


def is_release_posture(record):
    return (
        record["release_height"] > -0.04 * video_height
        or record["wrist_y"] < record["shoulder_y"] + 0.03 * video_height
    )


def find_release_candidates(records):
    if not records:
        return []

    min_window_frames = max(3, int(fps_value * 0.12))
    merge_gap_frames = max(6, int(fps_value * 0.25))
    min_recovery_frames = max(12, int(fps_value * 0.5))
    recovery_drop_px = max(28, video_height * 0.08)
    events = []
    active_event = []
    last_high_frame = None

    for record in records:
        if is_release_posture(record):
            if active_event and last_high_frame is not None and record["frame_index"] - last_high_frame > merge_gap_frames:
                events.append(active_event)
                active_event = []
            active_event.append(record)
            last_high_frame = record["frame_index"]
        elif active_event and last_high_frame is not None and record["frame_index"] - last_high_frame > merge_gap_frames:
            events.append(active_event)
            active_event = []
            last_high_frame = None

    if active_event:
        events.append(active_event)

    candidates = []
    for event in events:
        if event[-1]["frame_index"] - event[0]["frame_index"] + 1 < min_window_frames:
            continue

        candidate = min(event, key=lambda item: item["wrist_y"])
        if candidates:
            previous = candidates[-1]
            between_records = [
                item
                for item in records
                if previous["frame_index"] < item["frame_index"] < candidate["frame_index"]
            ]
            recovered = any(
                item["wrist_y"] > min(previous["wrist_y"], candidate["wrist_y"]) + recovery_drop_px
                or item["wrist_y"] > item["shoulder_y"] + 0.02 * video_height
                for item in between_records
            )
            enough_gap = candidate["frame_index"] - previous["frame_index"] >= max(
                min_recovery_frames, int(fps_value * 1.2)
            )
            if not recovered and not enough_gap:
                if candidate["wrist_y"] < previous["wrist_y"]:
                    candidates[-1] = candidate
                continue

        candidates.append(candidate)

    return candidates


release_candidates = find_release_candidates(pose_records)

shot_metrics = []
segments = load_segments(segments_path)
if segments:
    grouped_candidates = []
    for segment in segments:
        segment_records = [
            item
            for item in pose_records
            if segment.get("start_frame", 0) <= item["frame_index"] < segment.get("end_frame", 0)
        ]
        segment_candidates = [
            item
            for item in release_candidates
            if segment.get("start_frame", 0) <= item["frame_index"] < segment.get("end_frame", 0)
        ]
        if len(segment_candidates) > 1:
            segment_candidates = [min(segment_candidates, key=lambda item: item["wrist_y"])]
        if not segment_candidates:
            segment_candidates = [
                item
                for item in segment_records
                if is_release_posture(item)
            ]
        if segment_candidates:
            grouped_candidates.append(min(segment_candidates, key=lambda item: item["wrist_y"]))
    release_candidates = grouped_candidates

for candidate in release_candidates[:12]:
    dip_candidates = [
        item
        for item in pose_records
        if candidate["frame_index"] - dip_window_frames <= item["frame_index"] <= candidate["frame_index"]
    ]
    if not dip_candidates:
        continue

    local_dip = max(dip_candidates, key=lambda item: item["hip_y"])
    metrics_for_shot = calc_release_metrics(candidate, local_dip)
    if metrics_for_shot and metrics_for_shot["flow_frames"] >= max(5, int(fps_value * 0.15)):
        shot_metrics.append(metrics_for_shot)

shot_count = len(shot_metrics)
stability_score = None
stability_confidence = "low"
metric_variability = {}
consistency_check = {
    "status": "limited",
    "warning": False,
    "position_std": 0.0,
    "body_scale_std": 0.0,
    "shoulder_ratio_std": 0.0,
    "hip_ratio_std": 0.0,
}

if shot_count >= 2:
    metric_variability = {
        "elbow_angle_std": stddev([item["elbow_angle"] for item in shot_metrics]),
        "release_height_std": stddev([item["release_height"] for item in shot_metrics]),
        "body_lean_std": stddev([item["body_lean"] for item in shot_metrics]),
        "knee_extension_std": stddev([item["knee_extension"] for item in shot_metrics]),
        "flow_frames_std": stddev([item["flow_frames"] for item in shot_metrics]),
    }
    variability_index = (
        metric_variability["elbow_angle_std"] / 12
        + metric_variability["release_height_std"] / max(20, video_height * 0.08)
        + metric_variability["body_lean_std"] / max(20, video_width * 0.08)
        + metric_variability["knee_extension_std"] / 18
        + metric_variability["flow_frames_std"] / max(8, fps_value * 0.35)
    )
    stability_score = max(0, min(100, round(100 - variability_index * 20)))
    consistency_check = {
        "status": "consistent",
        "warning": False,
        "position_std": stddev([item["body_center_x_norm"] for item in shot_metrics]),
        "body_scale_std": stddev([item["body_height_norm"] for item in shot_metrics]),
        "shoulder_ratio_std": stddev([item["shoulder_width_ratio"] for item in shot_metrics]),
        "hip_ratio_std": stddev([item["hip_width_ratio"] for item in shot_metrics]),
    }
    if (
        consistency_check["position_std"] > 0.18
        or consistency_check["body_scale_std"] > 0.12
        or consistency_check["shoulder_ratio_std"] > 0.12
        or consistency_check["hip_ratio_std"] > 0.10
    ):
        consistency_check["status"] = "inconsistent_capture"
        consistency_check["warning"] = True
        stability_confidence = "low"

if shot_count >= 5 and not consistency_check["warning"]:
    stability_confidence = "high"
elif shot_count >= 3 and not consistency_check["warning"]:
    stability_confidence = "medium"

stability_payload = {
    "detected_shots": shot_count,
    "recommended_shots": 5,
    "stability_score": stability_score,
    "confidence": stability_confidence,
    "consistency_check": {
        "status": consistency_check["status"],
        "warning": consistency_check["warning"],
        "position_std": round(consistency_check["position_std"], 3),
        "body_scale_std": round(consistency_check["body_scale_std"], 3),
        "shoulder_ratio_std": round(consistency_check["shoulder_ratio_std"], 3),
        "hip_ratio_std": round(consistency_check["hip_ratio_std"], 3),
    },
    "metric_variability": {key: round(value, 1) for key, value in metric_variability.items()},
    "shots": [
        {
            "frame_index": item["frame_index"],
            "elbow_angle": round(item["elbow_angle"], 1),
            "release_height": round(item["release_height"], 1),
            "body_lean": round(item["body_lean"], 1),
            "knee_extension": round(item["knee_extension"], 1),
            "flow_frames": int(item["flow_frames"]),
            "body_center_x_norm": round(item["body_center_x_norm"], 3),
            "body_height_norm": round(item["body_height_norm"], 3),
        }
        for item in shot_metrics
    ],
}

if stability_path:
    with open(stability_path, "w", encoding="utf-8") as f:
        json.dump(stability_payload, f, ensure_ascii=False, indent=2)

release_local_dip_candidates = [
    item
    for item in pose_records
    if release_data["frame_index"] - dip_window_frames <= item["frame_index"] <= release_data["frame_index"]
]
if release_local_dip_candidates:
    local_dip = max(release_local_dip_candidates, key=lambda item: item["hip_y"])
    dip_data = {
        "frame_index": local_dip["frame_index"],
        "landmarks": local_dip["landmarks"],
        "width": local_dip["width"],
        "height": local_dip["height"],
    }

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
