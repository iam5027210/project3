from flask import Flask, render_template, Response,request, jsonify,session
from pymongo import MongoClient
import cv2
from finance_chatbot import Chatbot
import sys
from common import currTime,chat_with_openai,get_random_video
import mediapipe as mp
import numpy as np
#from face_processing import apply_filter
from datetime import datetime
import os
import time
import base64 
import atexit 
import uuid  # ✅ 고유한 세션 ID 생성을 위한 라이브러리
import openai
from markupsafe import Markup  # ✅ Flask가 아닌 markupsafe에서 가져오기
from deepface import DeepFace
from PIL import ImageFont, ImageDraw, Image
from flask_session import Session  # ✅ 세션 저장을 위한 Flask-Session 추가


# ✅ 한글 & 이모티콘 지원을 위한 폰트 설정
FONT_PATH_HANGUL = "fonts/NanumGothicBold.ttf"  # 한글 지원 폰트 파일 경로
FONT_PATH_EMOJI = "fonts/NotoColorEmoji.ttf"  # 이모티콘 지원 폰트 (Windows는 "Segoe UI Emoji")
FONT_SIZE = 60  # 폰트 크기 조절

# # ✅ 챗봇 인스턴스 생성
# jjinchin = Chatbot(
#     assistant_id="asst_vNuhpU0xp8lfJACH4HxRsuBT",
#     thread_id="thread_fs7NSkPuhqY37W1A8cnD0RjU"
# )


# try:
#     font = ImageFont.truetype("fonts/NanumGothicBold.ttf", 40)
#     print("✅ 폰트 로드 성공!")
# except Exception as e:
#     print(f"❌ 폰트 로드 실패: {e}")







app = Flask(__name__)
#app.secret_key = os.urandom(24)
# ✅ 고정된 SECRET_KEY 설정 (랜덤값이 아니라, 항상 동일한 값 사용)
app.secret_key = "super_secret_fixed_key"


# ✅ Flask 세션 설정 (서버에서 세션을 저장하여 유지)
app.config["SESSION_TYPE"] = "filesystem"  # ✅ 파일 시스템에 세션 저장
app.config["SESSION_PERMANENT"] = False  # ✅ 브라우저를 닫으면 세션 삭제
app.config["SESSION_USE_SIGNER"] = True  # ✅ 세션 데이터 서명 (보안 강화)
Session(app)  # ✅ 세션 적용



# ✅ MongoDB 연결
mongo_cluster = MongoClient("mongodb+srv://admin:admin1234@cluster0.uvix1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = mongo_cluster["jjinchin"]  # ✅ "jjinchin" 데이터베이스 선택
video_collection = db["videos"]  # ✅ "videos" 컬렉션 선택
face_collection = db["faces"]



@app.route('/get_session_id')
def get_session_id():
    """ 기존 세션이 있으면 유지, 없으면 새로 생성 """
    if 'session_id' in session:
        print(f"📢 기존 세션 유지: {session['session_id']}")
        return jsonify({"session_id": session['session_id']})
    
    
    
    # 새로운 세션 생성
    session['session_id'] = str(uuid.uuid4())
    print(f"🆕 새로운 세션 생성: {session['session_id']}")
    return jsonify({"session_id": session['session_id']})




# ✅ 얼굴 데이터 저장 여부 (영상이 끝나면 False로 설정)
stop_saving_faces = False

@app.route('/start_saving_faces', methods=['POST'])
def start_saving_faces_api():
    """ video.html에서 얼굴 데이터 저장 시작 """
    global stop_saving_faces
    stop_saving_faces = False  # ✅ 얼굴 저장 시작
    print("✅ stop_saving_faces = False")
    return jsonify({"status": "started"})

@app.route('/stop_saving_faces', methods=['POST'])
def stop_saving_faces_api():
    """ 영상이 끝나거나 index.html로 돌아오면 얼굴 데이터 저장 중지 """
    global stop_saving_faces
    stop_saving_faces = True  # ✅ 저장 중지
    print("🛑 stop_saving_faces = True")
    return jsonify({"status": "stopped"})





@app.route('/')
def home():
    videos = list(video_collection.find({}, {"_id": 0}))  # MongoDB에서 title 포함한 데이터 가져오기
    #print("📢 MongoDB에서 불러온 데이터:", videos)  # 디버깅 출력
    return render_template('index.html', videos=videos,messageTime=currTime())

@app.route('/video/<video_id>')
def video_page(video_id):
    # ✅ URL에서 analysis_mode 값을 가져옴 (없으면 기본값 None)
    analysis_mode = request.args.get("analysis_mode", None)
    
    print(f"📢 영상 페이지 로드됨 - 분석 모드: {analysis_mode}")
    return render_template('video.html', video_id=video_id, messageTime=currTime(), analysis_mode=analysis_mode)

@app.route('/chatbot_page')
def chatbot_page():
    return render_template('chatbot.html',messageTime=currTime())




@app.route('/chat-api', methods=['POST'])
def chat_api():
    global mbti_mode
    request_message = request.form.get("message")  
    analysis_mode = request.form.get("analysis_mode", request.args.get("analysis_mode", None))  # ✅ POST + GET 지원 
    print(f"📢 수신된 메시지: {request_message}, 현재 분석 모드: {analysis_mode}")

        # ✅ GPT 요청 중복 실행 방지
    if session.get("last_message") == request_message:
        print("⚠ 이미 같은 메시지를 처리했으므로 무시")
        return jsonify({"response_message": "⚠ 중복된 메시지는 처리되지 않습니다."})

    session["last_message"] = request_message  # ✅ 마지막 메시지 저장

    try:

        # ✅ 기본적인 페르소나 및 설정 (변경 가능!)
        auto_prompt_cmd = {
            "어투": "반말 사용 금지",
            "스타일": "유머러스하게",
            "길이": "짧게, 1줄로",
            "목적": "사용자의 질문에 알맞게 답변"
        }
        
        

        if "📢 분석 결과가 나왔어요!" in request_message:  # 가짜 챗봇 메세지를 바탕으로 gpt 응답 받기 (챗봇 구현 메세지 보내기 테스트용)
            # ✅ OpenAI GPT API를 통해 유머러스한 메시지 생성
            generated_analysis = chat_with_openai("이 사용자의 감정 분석 결과를 기반으로 유머러스하게 1줄,20자이내로 말해줘.")
            recommended_video_url = get_random_video()  # ✅ DB에서 Flask 라우트 형식의 영상 URL 가져오기
            response_message = f"👋 안녕하세요! 영상을 다 보셨네요! 😊 \n\n 🎭 **분석 결과:** {generated_analysis} \n\n 🎥 <a href='{recommended_video_url}' target='_top'>추천 영상 보러 가기</a>"  
        
        elif analysis_mode == "mbti":
            print("🔹 MBTI 모드 활성화됨 - MBTI 스타일로 GPT 응답 생성")
            # ✅ MBTI 스타일 감정 분석 요청
            prompt = f"""
            사용자의 감정 변화 데이터를 기반으로, MBTI 스타일 분석을 해줘.
            사용자의 감정 패턴을 MBTI 유형처럼 분류하고, 성격을 해석해줘.
            유머러스한 방식으로 작성해줘. 이모티콘도 적절히 추가하고, 1줄로 20자자 이내로 짧게 만들어줘!

            감정 변화 데이터:
            {request_message}
            """
        elif analysis_mode == "character":
            print("🔹 영화/게임 캐릭터 모드 활성화됨")
            prompt = f"""
            사용자의 감정 변화를 심리 테스트 결과처럼 분석해줘.
            유형을 재미있는 별명이나 성격 패턴으로 분류하고,
            감정을 롤러코스터, 게임 캐릭터, 점수 등으로 설명해줘.
            유머러스한 방식으로 작성해줘. 이모티콘도 적절히 추가하고, 1줄로 20자자 이내로 짧게 만들어줘!

            감정 변화 데이터:
            {request_message}
            """
        elif analysis_mode == "emotion":
            print("🔹 감정 유형 테스트 모드 활성화됨")
            prompt = f"""
            사용자의 감정 변화 데이터를 기반으로, 심리테스트 결과처럼 분석해줘.
            사용자의 감정 패턴을 재미있는 유형으로 분류하고, 그 사람의 성격을 해석해줘.
            유머러스한 방식으로 작성해줘. 이모티콘도 적절히 추가하고, 1줄로 20자자 이내로 짧게 만들어줘!

            감정 변화 데이터:
            {request_message}
            """

        # ✅ 일반적인 메시지 처리
        else:

            prompt = f"{request_message} ({auto_prompt_cmd})"
        
        response_message = chat_with_openai(prompt)

        print("📢 챗봇 응답:", response_message)
        return jsonify({"response_message": Markup(response_message)})  # ✅ HTML 태그 적용

    
    except Exception as e:
        print(f"❌ `chat-api` 오류 발생: {e}")
        return jsonify({"response_message": "⚠ 오류가 발생했습니다. 다시 시도해주세요!"})


# MediaPipe 얼굴 검출 모델 초기화

mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh  # 얼굴 표정을 위한 마크 감지
face_detection = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, min_detection_confidence=0.5)


# ✅ 영어 감정 분석 결과 → 한글 + 이모티콘 변환
emotion_translation = {
    "angry": "화남",
    "disgust": "역겨움",
    "fear": "두려움",
    "happy": "웃음",
    "sad": "슬픔",
    "surprise": "놀람",
    "neutral": "중립"
}



def save_face_data(original_frame,emotion, landmarks,video_id="unknown", session_id="default_session"):
    """ 원본 얼굴 이미지를 MongoDB와 로컬 폴더에 저장 """

    global stop_saving_faces

    if stop_saving_faces:
        print("🔴 얼굴 저장 중지됨 (index.html 또는 영상 종료)")
        return  # ✅ 영상이 끝나면 저장 중지

    # ✅ 현재 시간 생성 (타임스탬프)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # 예: 20250218_103845

    # ✅ 파일명 형식: 영상 ID_세션 ID_날짜시간.jpg
    filename = f"{video_id}_{session_id}_{timestamp}.jpg"

    # ✅ 저장 폴더 설정 (faces/{video_id}/)
    save_folder = os.path.join("faces", video_id)
    os.makedirs(save_folder, exist_ok=True)  # 폴더가 없으면 자동 생성

    # ✅ 로컬 파일 저장 경로
    save_path = os.path.join(save_folder, filename)

    # ✅ 원본 이미지 저장 (로컬)
    cv2.imwrite(save_path, original_frame)
    print(f"✅ 로컬 폴더에 이미지 저장 완료: {save_path}")

    _, buffer = cv2.imencode('.jpg', original_frame)  # 원본 이미지 저장
    face_image_base64 = base64.b64encode(buffer).decode('utf-8')  # Base64 인코딩

    face_data = {
        "timestamp": time.time(),  # 저장 시간 (Unix Timestamp)
        "video_id": video_id,
        "session_id": session_id,
        "image_filename": filename,  # ✅ 로컬 저장된 파일명 추가
        "image_path": save_path,  # ✅ 로컬 경로 추가
        #"original_image": face_image_base64,  # ✅ Base64 인코딩된 원본 이미지
        "landmarks": landmarks,  # ✅ 랜드마크 좌표 리스트
        "emotion" : emotion
    }

    face_collection.insert_one(face_data)  # MongoDB에 저장
    print("✅ 얼굴 데이터 & 랜드마크, 감정 분석 결과 저장 완료(video.html에서만 저장)")





def apply_filter(frame):
    """ 얼굴 필터 적용 + 배경을 하얀색으로 변경 + 표정 마크 추가 """

    global stop_saving_faces
    if stop_saving_faces:
        return frame, frame, [], "해석 불가"  # ✅ 기본값 반환


    h, w, _ = frame.shape
    original_frame = frame.copy()  # ✅ 원본 이미지 저장

    # ✅ 1. 배경을 완전한 흰색으로 설정
    white_background = np.ones_like(frame, dtype=np.uint8) * 255  # 완전 흰색 이미지 생성

    # ✅ 2. 얼굴 감지 실행
    results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    landmarks_list = []
    emotion_result = "🙂 중립"  # 기본값 설정


    if results.detections:
        for detection in results.detections:
            bboxC = detection.location_data.relative_bounding_box
            x, y, w_box, h_box = (int(bboxC.xmin * w), int(bboxC.ymin * h), 
                                  int(bboxC.width * w), int(bboxC.height * h))

            # ✅ 3. 얼굴 부분만 잘라서 배경이 흰색인 이미지에 넣기
            face_roi = frame[y:y+h_box, x:x+w_box]
            white_background[y:y+h_box, x:x+w_box] = face_roi
            

            # ✅ 4. DeepFace 감정 분석 수행, # ✅ 감정 분석 실행 (한글 변환 적용)
            emotion_result = analyze_emotion_with_deepface(face_roi)

            # # ✅ 글자 크기(Font Scale) & 색상(BGR 값) 수정
            # font_scale = 1.5  # 글자 크기 키우기
            # font_color = (0, 166, 255)  # 글자 색상 (BGR: )
            # thickness = 3  # 글자 두께 증가

            # # ✅ 5. 감정 분석 결과를 화면에 표시
            # cv2.putText(white_background, f"{emotion_result.upper()}", 
            #             (x, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 
            #             font_scale, font_color, thickness, cv2.LINE_AA)
            

            # # ✅ OpenCV 대신 Pillow로 한글 & 이모티콘 출력
            frame_pil = Image.fromarray(white_background)  # OpenCV → PIL 변환
            draw = ImageDraw.Draw(frame_pil)
            font = ImageFont.truetype(FONT_PATH_HANGUL, FONT_SIZE)

            # # ✅ 한글 & 이모티콘 표시 (폰트 크기 & 색상 조절)
            draw.text((x, y - 80), emotion_result, font=font, fill=(101,31,212))  # (RGB)
            white_background = np.array(frame_pil)  # PIL → OpenCV 변환


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


    return white_background, original_frame, landmarks_list,emotion_result   # ✅ 감정 분석 결과 추가 반환





# ✅ 웹캠 한 번만 실행
cap = cv2.VideoCapture(0)




def generate_frames(video_id="unknown", session_id="unknown_session"):
    """ 웹캠에서 프레임을 받아와 필터 적용 후 전송하는 함수 """
    global stop_saving_faces
    #cap = cv2.VideoCapture(0)
    last_saved_time = 0 # 마지막으로 저장된 시간

    # ✅ video_id가 "none"이면 기본값 설정
    if video_id in ["none", "unknown"]:
        print("⚠ `generate_frames()`에서 video_id가 'none'으로 감지됨 → 기본값으로 설정")
        video_id = "main"
    
    print(f"📷 `generate_frames()` 시작됨 - video_id: {video_id}, session_id: {session_id}, {stop_saving_faces}")

   
    while True:
        success, frame = cap.read()
        if not success:
                print("❌ 카메라에서 프레임을 읽을 수 없음")
                continue  

        # ✅ 필터 적용 (반환값 개수 검증 추가)
        filter_result = apply_filter(frame)

        if len(filter_result) != 4:
            print(f"⚠ `apply_filter()`의 반환값 개수 오류: {len(filter_result)}개 반환됨")
            continue  # 다음 프레임 처리

        filtered_frame, original_frame, landmarks, emotions = filter_result  

        
        # ✅ landmarks가 리스트인지 확인 (안전한 처리)
        if not isinstance(landmarks, list):
            landmarks = []  # 만약 리스트가 아니라면 빈 리스트로 변환

        # ✅ 현재 시간 확인
        current_time = time.time()



        # ✅ video_id가 'unknown'이면 저장 ❌ (메인 페이지에서 저장 방지)
        if not stop_saving_faces and video_id not in ( "unknown", "none","main") and (current_time - last_saved_time >= 1.0):
            save_face_data(original_frame,emotions, landmarks,video_id, session_id)  # ✅ 저장은 여기에서만 실행
            last_saved_time = current_time  # ✅ 마지막 저장 시간을 업데이트
        elif stop_saving_faces  and video_id not in ( "unknown", "none","main"):
            pass

        # 웹캠 화면을 전달할 수 있도록 변환
        ret, buffer = cv2.imencode('.jpg', filtered_frame)
            
        if not ret:
            print("❌ 프레임 인코딩 실패")
            continue  # ✅ 다음 프레임 처리
        
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')



def analyze_emotion_with_deepface(face_roi):
    """ DeepFace를 사용하여 감정을 분석한 후 한글 & 이모티콘 변환 """
    try:
        analysis = DeepFace.analyze(face_roi, actions=['emotion'], enforce_detection=False)
        dominant_emotion = analysis[0]['dominant_emotion']
        #print(f"🎭 감정 분석 결과 (영어): {dominant_emotion}")

        # ✅ 영어 감정을 한글 + 이모티콘으로 변환
        translated_emotion = emotion_translation.get(dominant_emotion, "해석 불가")
        print(f"🎭 감정 분석 결과 : {translated_emotion}") # 한글

        return translated_emotion
    except Exception as e:
        print(f"⚠ 감정 분석 실패: {e}")
        return "해석 불가"  # ✅ 오류 발생 시 "해석불가" 반환





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

#@app.route('/video_feed/', defaults={'video_id': 'none', 'session_id': 'unknown_session'})    
  
@app.route('/video_feed/<video_id>/<session_id>')
def video_feed(video_id, session_id):
    """ 영상 ID와 세션 ID를 전달하여 프레임 생성 """
    print(f"📷 웹캠 스트리밍 요청 - video_id: {video_id}, session_id: {session_id}")
    return Response(generate_frames(video_id, session_id), mimetype='multipart/x-mixed-replace; boundary=frame')
# @app.route('/video_feed')
# def video_feed():
#     return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_emotion_analysis/<video_id>/<session_id>')
def get_emotion_analysis(video_id, session_id):
    
    """ MongoDB에서 특정 영상 & 세션의 감정 데이터를 가져와 분석 """
    
    print(f"📢 감정 분석 요청: video_id={video_id}, session_id={session_id}")
    
    # ✅ 해당 영상 & 세션에 대한 얼굴 감정 데이터 가져오기
    face_data = list(face_collection.find(
        {"video_id": video_id, "session_id": session_id},
        {"_id": 0, "timestamp": 1, "emotion": 1}
    ))

    if not face_data:
        return jsonify({"error": "해당 영상의 감정 데이터가 없음"}), 404

    # ✅ 시간순으로 정렬
    face_data.sort(key=lambda x: x["timestamp"])

    # ✅ 감정 변화 분석 (시간순)
    emotions_over_time = [{"timestamp": entry["timestamp"], "emotion": entry["emotion"]} for entry in face_data]

    # ✅ 감정 비율 분석
    emotion_counts = {}
    for entry in face_data:
        emotion = entry["emotion"]
        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

    total_count = sum(emotion_counts.values())
    emotion_percentages = {emotion: round((count / total_count) * 100, 2) for emotion, count in emotion_counts.items()}

    # ✅ 추천 영상 추가 (여기서 추천 영상을 추가)
    recommended_video_url = get_random_video()

    # ✅ 분석 결과 반환 (추천 영상 포함)
    return jsonify({
        "emotions_over_time": emotions_over_time,
        "emotion_percentages": emotion_percentages,
        "recommended_video_url": recommended_video_url,  # ✅ 추천 영상 URL 추가!
    })



if __name__ == '__main__':
    app.run(debug=True)

