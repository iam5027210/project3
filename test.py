import cv2
import mediapipe as mp
import numpy as np

mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

with mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5) as face_mesh:
    reference_landmarks = None  # 무표정 기준값 저장
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                h, w, _ = frame.shape
                
                # 기준점 설정 (코 끝과 양 눈 사이 거리)
                nose_tip = face_landmarks.landmark[1]  # 코 끝 (Landmark ID: 1)
                left_eye = face_landmarks.landmark[33]  # 왼쪽 눈 중앙 (ID: 33)
                right_eye = face_landmarks.landmark[263]  # 오른쪽 눈 중앙 (ID: 263)
                
                nose_x, nose_y = int(nose_tip.x * w), int(nose_tip.y * h)
                left_x, left_y = int(left_eye.x * w), int(left_eye.y * h)
                right_x, right_y = int(right_eye.x * w), int(right_eye.y * h)
                
                eye_distance = np.linalg.norm([right_x - left_x, right_y - left_y])  # 눈 사이 거리 (기준값)
                
                # 감지할 주요 랜드마크 (입꼬리, 입술 위아래, 눈 상하좌우)
                feature_ids = {
                    "left_mouth": 61, "right_mouth": 291, "upper_lip": 13, "lower_lip": 14,
                    "left_eye_top": 159, "left_eye_bottom": 145, "left_eye_left": 130, "left_eye_right": 133,
                    "right_eye_top": 386, "right_eye_bottom": 374, "right_eye_left": 362, "right_eye_right": 263
                }
                
                feature_points = {}
                for key, idx in feature_ids.items():
                    x, y = int(face_landmarks.landmark[idx].x * w), int(face_landmarks.landmark[idx].y * h)
                    feature_points[key] = (x, y)
                    cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)
                
                # 무표정 기준 저장 (한 번만 수행)
                if reference_landmarks is None:
                    reference_landmarks = feature_points.copy()
                    reference_eye_distance = eye_distance
                    
                # 표정 변화 계산 (눈 사이 거리로 정규화)
                changes = {}
                for key in feature_points:
                    ref_x, ref_y = reference_landmarks[key]
                    cur_x, cur_y = feature_points[key]
                    dx, dy = (cur_x - ref_x) / reference_eye_distance, (cur_y - ref_y) / reference_eye_distance
                    changes[key] = (dx, dy)
                
                # 화면에 변화된 값 출력
                y_offset = 30
                for key, (dx, dy) in changes.items():
                    text = f"{key}: ({dx:.2f}, {dy:.2f})"
                    cv2.putText(frame, text, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                    y_offset += 20
        
        cv2.imshow('Face Landmark Tracker', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
