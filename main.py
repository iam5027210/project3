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
import time
import base64 
import atexit 

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
face_collection = db["faces"]



# ✅ 얼굴 데이터 저장 여부 (영상이 끝나면 False로 설정)
stop_saving_faces = False

@app.route('/start_saving_faces', methods=['POST'])
def start_saving_faces_api():
    """ video.html에서 얼굴 데이터 저장 시작 """
    global stop_saving_faces
    stop_saving_faces = False  # ✅ 얼굴 저장 시작
    print("✅ 얼굴 데이터 저장 시작됨")
    return jsonify({"status": "started"})

@app.route('/stop_saving_faces', methods=['POST'])
def stop_saving_faces_api():
    """ 영상이 끝나거나 index.html로 돌아오면 얼굴 데이터 저장 중지 """
    global stop_saving_faces
    stop_saving_faces = True  # ✅ 저장 중지
    print("🛑 얼굴 데이터 저장 중지됨")
    return jsonify({"status": "stopped"})





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


def save_face_data(original_frame, landmarks):
    """ 원본 얼굴 이미지를 저장하고, 랜드마크 값을 함께 MongoDB에 저장 """

    global stop_saving_faces

    if stop_saving_faces:
        print("🔴 얼굴 저장 중지됨 (index.html 또는 영상 종료)")
        return  # ✅ 영상이 끝나면 저장 중지


    _, buffer = cv2.imencode('.jpg', original_frame)  # 원본 이미지 저장
    face_image_base64 = base64.b64encode(buffer).decode('utf-8')  # Base64 인코딩

    face_data = {
        "timestamp": time.time(),  # 저장 시간
        "original_image": face_image_base64,  # ✅ 원본 얼굴 이미지 (배경 변경 ❌)
        "landmarks": landmarks  # ✅ 랜드마크 좌표 리스트
    }

    face_collection.insert_one(face_data)  # MongoDB에 저장
    print("✅ 원본 얼굴 이미지 & 랜드마크 저장 완료(video.html에서만 저장)")



def apply_filter(frame):
    """ 얼굴 필터 적용 + 배경을 하얀색으로 변경 + 표정 마크 추가 """

    global stop_saving_faces
    if stop_saving_faces:
        return frame  # ✅ 영상이 끝나면 원본 프레임만 반환 (저장 X)


    h, w, _ = frame.shape
    original_frame = frame.copy()  # ✅ 원본 이미지 저장

    # ✅ 1. 배경을 완전한 흰색으로 설정
    white_background = np.ones_like(frame, dtype=np.uint8) * 255  # 완전 흰색 이미지 생성

    # ✅ 2. 얼굴 감지 실행
    results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    landmarks_list = []


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
                
                # ✅ 랜드마크 데이터 저장
                landmarks_list.append({"x": landmark.x, "y": landmark.y, "z": landmark.z})

    # # ✅ 원본 얼굴 이미지를 저장 (사용자에게 보여지는 화면과 별개)
    # if results.detections:
    #     save_face_data(original_frame, landmarks_list)

    return white_background, original_frame, landmarks_list  # ✅ 저장 로직 제거하고, 반환값 변경

# ✅ 웹캠 한 번만 실행
cap = cv2.VideoCapture(0)




def generate_frames():
    """ 웹캠에서 프레임을 받아와 필터 적용 후 전송하는 함수 """
    global stop_saving_faces
    #cap = cv2.VideoCapture(0)
    
    while True:
        success, frame = cap.read()
        if not success:
            break

       # ✅ 필터 적용 (저장 X, 필터만 처리)
        filtered_frame, original_frame, landmarks = apply_filter(frame)  
        
        # ✅ landmarks가 리스트인지 확인 (안전한 처리)
        if not isinstance(landmarks, list):
            landmarks = []  # 만약 리스트가 아니라면 빈 리스트로 변환
            
        # # ✅ 영상 종료 후 얼굴 데이터 저장 중지
        # if stop_saving_faces:
        #     print("✅ 얼굴 저장 중지됨. 영상 종료 감지!")
        #     #cap.release()  # 웹캠 종료
        #     break  # ✅ 루프 종료 (웹캠 데이터 중단)

        # # ✅ index.html에서는 얼굴 저장 ❌ (video.html에서만 저장)
        # else:
        #     frame = apply_filter(frame)  # 얼굴 데이터 저장 활성화
   
        # # 필터 적용
        # frame = apply_filter(frame)    

        if not stop_saving_faces:
            save_face_data(original_frame, landmarks)  # ✅ 저장은 여기에서만 실행


        # 웹캠 화면을 전달할 수 있도록 변환
        ret, buffer = cv2.imencode('.jpg', filtered_frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/saved_faces')
def saved_faces():
    """ 저장된 얼굴 데이터 조회 API """
    faces = list(face_collection.find({}, {"_id": 0}))  # 모든 얼굴 데이터 조회
    return jsonify(faces)  # JSON 형태로 반환


# ✅ Flask 종료 시 MongoDB 연결 닫기 & 카메라 해제
@atexit.register
def close_resources():
    print("🔴 Flask 종료 - MongoDB 연결 닫음 & 카메라 해제")
    cap.release()  # 프로그램 종료 시에만 카메라 해제
    mongo_cluster.close()


if __name__ == '__main__':
    app.run(debug=True)

