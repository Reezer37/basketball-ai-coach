import cv2
import mediapipe as mp
import math

input_video = "shot.mp4"

mp_pose = mp.solutions.pose

def calc_angle(a, b, c):
    ab = [a[0] - b[0], a[1] - b[1]]
    cb = [c[0] - b[0], c[1] - b[1]]

    dot = ab[0]*cb[0] + ab[1]*cb[1]
    mag_ab = math.sqrt(ab[0]**2 + ab[1]**2)
    mag_cb = math.sqrt(cb[0]**2 + cb[1]**2)

    if mag_ab * mag_cb == 0:
        return 0

    angle = math.degrees(math.acos(dot / (mag_ab * mag_cb)))
    return angle

cap = cv2.VideoCapture(input_video)

elbow_angles = []

with mp_pose.Pose() as pose:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)

        if results.pose_landmarks:
            h, w, _ = frame.shape

            landmarks = results.pose_landmarks.landmark

            # 右肩、右肘、右腕
            shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
            elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
            wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]

            s = (shoulder.x * w, shoulder.y * h)
            e = (elbow.x * w, elbow.y * h)
            w_ = (wrist.x * w, wrist.y * h)

            angle = calc_angle(s, e, w_)
            elbow_angles.append(angle)

cap.release()

if elbow_angles:
    avg_angle = sum(elbow_angles) / len(elbow_angles)
    print("平均手肘角度:", round(avg_angle, 2))

    if avg_angle > 150:
        print("👉 手肘可能过直（出手太推）")
    elif avg_angle < 70:
        print("👉 手肘弯曲过多")
    else:
        print("👉 手肘角度正常 👍")
else:
    print("没有检测到动作")
