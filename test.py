from deepface import DeepFace
import cv2

cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # 감정 분석 실행
    emotions = DeepFace.analyze(frame, actions=["emotion"], enforce_detection=False)
    print(emotions)

    # 첫 번째 항목에서 감정 정보 추출
    dominant_emotion = emotions[0]['dominant_emotion']
    print(f"Dominant Emotion: {dominant_emotion}")

    # 실시간 영상에 감정 표시
    cv2.putText(frame, f"Emotion: {dominant_emotion}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow('Emotion Detection', frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
