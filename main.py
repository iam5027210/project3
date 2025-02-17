from flask import Flask, render_template, Response,request, jsonify
from pymongo import MongoClient
import cv2
from finance_chatbot import Chatbot
import sys
from common import currTime
import mediapipe as mp
import numpy as np
#from face_processing import apply_filter
from datetime import datetime
import os

# ✅ 챗봇 인스턴스 생성
jjinchin = Chatbot(
    assistant_id="asst_vNuhpU0xp8lfJACH4HxRsuBT",
    thread_id="thread_fs7NSkPuhqY37W1A8cnD0RjU"
)



app = Flask(__name__)



# ✅ MongoDB 연결
mongo_cluster = MongoClient("mongodb+srv://admin:admin1234@cluster0.uvix1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = mongo_cluster["jjinchin"]  # ✅ "jjinchin" 데이터베이스 선택
video_collection = db["videos"]  # ✅ "videos" 컬렉션 선택


@app.route('/')
def home():
    videos = list(video_collection.find({}, {"_id": 0}))  # MongoDB에서 title 포함한 데이터 가져오기
    #print("📢 MongoDB에서 불러온 데이터:", videos)  # 디버깅 출력
    return render_template('index.html', videos=videos,messageTime=currTime())

@app.route('/video/<video_id>')
def video_page(video_id):
    return render_template('video.html', video_id=video_id,messageTime=currTime())

@app.route('/chatbot_page')
def chatbot_page():
    return render_template('chatbot.html',messageTime=currTime())

@app.route('/chat-api', methods=['POST'])
def chat_api():
    request_message = request.form.get("message")     
    print("request_message:", request_message)
    try: 
        jjinchin.add_user_message(request_message)
        run = jjinchin.create_run()
        _, response_message = jjinchin.get_response_content(run)
        response_python_code = jjinchin.get_interpreted_code(run.id)
    except Exception as e:
        print("assistants ai error", e)
        response_message = "[Assistants API 오류가 발생했습니다]"
            
    print("response_message:", response_message)
    return {"response_message": response_message, "response_python_code": response_python_code}



# MediaPipe 얼굴 검출 모델 초기화

mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh  # 얼굴 표정을 위한 마크 감지
face_detection = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, min_detection_confidence=0.5)

def apply_filter(frame):
    """ 얼굴 필터 적용 + 배경을 하얀색으로 변경 + 표정 마크 추가 """

    h, w, _ = frame.shape

    # ✅ 1. 배경을 완전한 흰색으로 설정
    white_background = np.ones_like(frame, dtype=np.uint8) * 255  # 완전 흰색 이미지 생성

    # ✅ 2. 얼굴 감지 실행
    results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    if results.detections:
        for detection in results.detections:
            bboxC = detection.location_data.relative_bounding_box
            x, y, w_box, h_box = (int(bboxC.xmin * w), int(bboxC.ymin * h), 
                                  int(bboxC.width * w), int(bboxC.height * h))

            # ✅ 3. 얼굴 부분만 잘라서 배경이 흰색인 이미지에 넣기
            face_roi = frame[y:y+h_box, x:x+w_box]
            white_background[y:y+h_box, x:x+w_box] = face_roi

    # ✅ 4. 얼굴 표정 감지를 위한 FaceMesh 실행
    mesh_results = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    if mesh_results.multi_face_landmarks:
        for face_landmarks in mesh_results.multi_face_landmarks:
            for landmark in face_landmarks.landmark:
                x_pos, y_pos = int(landmark.x * w), int(landmark.y * h)
                
                # ✅ 표정 감지 마크 표시 (기본적인 점)
                cv2.circle(white_background, (x_pos, y_pos), 2, (0, 255, 0), -1)  # 초록색 점

    return white_background  # 최종 필터 적용된 영상 반환





def generate_frames():
    """ 웹캠에서 프레임을 받아와 필터 적용 후 전송하는 함수 """
    cap = cv2.VideoCapture(0)
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        # 필터 적용
        frame = apply_filter(frame)

        # 웹캠 화면을 전달할 수 있도록 변환
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')





if __name__ == '__main__':
    app.run(debug=True)

