import cv2
import mediapipe as mp

input_video = "shot.mp4"
output_image = "release_frame.jpg"

mp_pose = mp.solutions.pose
cap = cv2.VideoCapture(input_video)

best_frame = None
best_wrist_y = 999999
best_frame_index = 0
frame_index = 0

with mp_pose.Pose() as pose:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        if results.pose_landmarks:
            h, w, _ = frame.shape
            landmarks = results.pose_landmarks.landmark

            wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
            wrist_y = wrist.y * h

            # y 越小，手腕越高。先用“手腕最高点”近似出手瞬间
            if wrist_y < best_wrist_y:
                best_wrist_y = wrist_y
                best_frame = frame.copy()
                best_frame_index = frame_index

        frame_index += 1

cap.release()

if best_frame is not None:
    cv2.imwrite(output_image, best_frame)
    print("已找到近似出手瞬间")
    print("帧号:", best_frame_index)
    print("已保存截图:", output_image)
else:
    print("没有检测到出手瞬间")
