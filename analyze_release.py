import argparse
import cv2
import math
from mediapipe.python.solutions import drawing_utils as mp_drawing
from mediapipe.python.solutions import pose as mp_pose

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="shot.mp4")
parser.add_argument("--output-image", default="release_analyzed.jpg")
parser.add_argument("--result", default="result.txt")
args = parser.parse_args()

input_video = args.input
output_image = args.output_image
result_path = args.result

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

cap = cv2.VideoCapture(input_video)

release_data = None
best_wrist_y = 999999

lowest_hip_y = -1
dip_data = None

frame_index = 0

with mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as pose:

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        if results.pose_landmarks:
            h, w, _ = frame.shape
            lm = results.pose_landmarks.landmark

            wrist = lm[mp_pose.PoseLandmark.RIGHT_WRIST]
            hip = lm[mp_pose.PoseLandmark.RIGHT_HIP]

            wrist_y = wrist.y * h
            hip_y = hip.y * h

            # 出手瞬间：用手腕最高点近似
            if wrist_y < best_wrist_y:
                best_wrist_y = wrist_y
                release_data = {
                    "frame": frame.copy(),
                    "landmarks": results.pose_landmarks,
                    "frame_index": frame_index,
                    "width": w,
                    "height": h
                }

            # 下蹲最低点：用右髋最高 y 值近似，y 越大代表越低
            if hip_y > lowest_hip_y:
                lowest_hip_y = hip_y
                dip_data = {
                    "frame_index": frame_index,
                    "landmarks": results.pose_landmarks,
                    "width": w,
                    "height": h
                }

        frame_index += 1

cap.release()

if not release_data or not dip_data:
    print("没有检测到完整人体动作")
    exit(1)

# ===== 出手瞬间数据 =====
frame = release_data["frame"]
lm = release_data["landmarks"].landmark
w = release_data["width"]
h = release_data["height"]

right_shoulder = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER]
right_elbow = lm[mp_pose.PoseLandmark.RIGHT_ELBOW]
right_wrist = lm[mp_pose.PoseLandmark.RIGHT_WRIST]
right_hip = lm[mp_pose.PoseLandmark.RIGHT_HIP]
right_knee = lm[mp_pose.PoseLandmark.RIGHT_KNEE]
right_ankle = lm[mp_pose.PoseLandmark.RIGHT_ANKLE]
nose = lm[mp_pose.PoseLandmark.NOSE]

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
dip_lm = dip_data["landmarks"].landmark
dw = dip_data["width"]
dh = dip_data["height"]

dip_hip_lm = dip_lm[mp_pose.PoseLandmark.RIGHT_HIP]
dip_knee_lm = dip_lm[mp_pose.PoseLandmark.RIGHT_KNEE]
dip_ankle_lm = dip_lm[mp_pose.PoseLandmark.RIGHT_ANKLE]

dip_hip = (dip_hip_lm.x * dw, dip_hip_lm.y * dh)
dip_knee = (dip_knee_lm.x * dw, dip_knee_lm.y * dh)
dip_ankle = (dip_ankle_lm.x * dw, dip_ankle_lm.y * dh)

dip_knee_angle = calc_angle(dip_hip, dip_knee, dip_ankle)

# 膝盖伸展幅度：越大说明下肢参与越明显
knee_extension = release_knee_angle - dip_knee_angle

# ===== 画图保存 =====
mp_drawing.draw_landmarks(
    frame,
    release_data["landmarks"],
    mp_pose.POSE_CONNECTIONS
)

cv2.putText(
    frame,
    f"Elbow: {elbow_angle:.1f}  Knee: {release_knee_angle:.1f}",
    (30, 50),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.9,
    (255, 255, 255),
    2
)

cv2.imwrite(output_image, frame)

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
