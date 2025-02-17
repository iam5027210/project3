import cv2
import numpy as np
import mediapipe as mp

mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh  
face_detection = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, min_detection_confidence=0.5)

def apply_filter(frame):
    """ 얼굴 감지 + 배경을 흰색으로 변경 """
    h, w, _ = frame.shape
    white_background = np.ones_like(frame, dtype=np.uint8) * 255  
    results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    if results.detections:
        for detection in results.detections:
            bboxC = detection.location_data.relative_bounding_box
            x, y, w_box, h_box = (int(bboxC.xmin * w), int(bboxC.ymin * h), 
                                  int(bboxC.width * w), int(bboxC.height * h))

            face_roi = frame[y:y+h_box, x:x+w_box]
            white_background[y:y+h_box, x:x+w_box] = face_roi

    return white_background
