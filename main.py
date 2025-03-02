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
from tensorflow.keras.models import load_model
from tensorflow.keras.layers import InputLayer
from tensorflow.keras.optimizers import Adam

try:
    print("🔍 감정 분석 모델 로드 중...")
    MODEL_PATH = "models/final_vggface_wgtImgNet_finetune_0228.h5_e10.h5"
    
    # ✅ InputLayer를 명시적으로 추가하여 `batch_shape` 오류 방지
    emotion_model = load_model(MODEL_PATH, custom_objects={"InputLayer": InputLayer})

    # ✅ 모델이 제대로 로드되었는지 확인
    print("✅ 감정 분석 모델 로드 완료!")

    # ✅ 모델을 다시 컴파일 (튜닝 시 사용한 설정 유지)
    emotion_model.compile(
        optimizer=Adam(learning_rate=0.0001),  # 🔹 튜닝 시 사용한 optimizer 적용
        loss="categorical_crossentropy",  # 🔹 튜닝 시 사용한 loss 적용
        metrics=["accuracy"]  # 🔹 튜닝 시 사용한 metrics 적용
    )
    print("✅ 모델 컴파일 완료!")
    
except Exception as e:
    print(f"❌ 모델 로드 실패: {e}")
    exit(1)  # 실행 종료

# # ✅ VGGFace 기반 감정 분석 모델 로드

# emotion_model = load_model(MODEL_PATH)

# # ✅ 감정 클래스 레이블 (새 모델 기준)
emotion_labels = ["anger", "happy", "normal", "panic", "sadness"]


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
db = mongo_cluster["wassup3"]  # ✅ "jjinchin" 데이터베이스 선택
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
    emotion_data = request.form.get("emotion_data")
    emotion_percentages = request.form.get("emotion_percentages")
    print(f"📢 사용자 메시지: {request_message}")
    print(f"📊 감정 변화 데이터: {emotion_data}")
    print(f"📊 감정 퍼센트 데이터: {emotion_percentages}")


        # ✅ GPT 요청 중복 실행 방지
    if session.get("last_message") == request_message:
        print("⚠ 이미 같은 메시지를 처리했으므로 무시")
        return jsonify({"response_message": "⚠ 중복된 메시지는 처리되지 않습니다."})

    session["last_message"] = request_message  # ✅ 마지막 메시지 저장

    try:

        # ✅ 기본적인 페르소나 및 설정 (변경 가능!)
        auto_prompt_cmd = {
            "어투": "'~해요' 또는 '~하세요' 형태로 답변해주세요.",
            "스타일": "친절하고,공손하게",
            "길이": "짧게, 1줄로",
            "목적": "사용자의 질문에 알맞게 답변해줘"
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
            [답변모드 : MBTI 모드]사용자의 감정 변화 데이터를 기반으로, MBTI 스타일 분석을 해줘.
            사용자의 감정 패턴을 MBTI 유형처럼 분류하고, 성격을 해석해줘.
            유머러스한 방식으로 작성해줘. 이모티콘도 적절히 추가하고, 1줄로 20자 이내로 짧게 만들어줘!
            💡 **예시**
            - 감정이 급격히 변하고 활발함 → "넌 ENFP 유형! 🎉 감정 롤러코스터 🎢"
            - 차분하고 감정 변화가 적음 → "넌 ISTJ 유형! 📚 감정이 늘 안정적이야 🧘‍♂️"
            - 웃음이 많고 감정이 긍정적 → "넌 ESFJ 유형! 😆 사람들에게 에너지를 주는 감성 리더!"
            - 감정 표현이 적고 중립적 → "넌 INTP 유형! 🤖 감정보다는 논리를 우선하는 타입!"
            - 놀람과 두려움 반응이 많음 → "넌 INFJ 유형! 🧐 감정이 예민한 예측가!"

            사용자의 감정 데이터를 분석하고, 위의 예시와 유사한 방식으로 MBTI 스타일을 짧고 재미있게 설명해줘.
            감정 변화 데이터:
            {request_message}
            """
        elif analysis_mode == "character":
            print("🔹 영화/게임 캐릭터 모드 활성화됨")
            prompt = f"""
            [답변모드 : 영화/게임 캐릭터 모드]사용자의 감정 변화를 분석해서, 가장 닮은 영화 또는 게임 캐릭터를 찾아줘.  
            감정 패턴을 기반으로 캐릭터의 성격과 분위기를 유머러스하게 매칭해줘.  
            너무 진지하지 않게, 이모티콘을 적절히 추가해서 1줄 (20자 이내)로 작성해줘!  

            💡 예시  
            - 감정이 롤러코스터처럼 변함 → "넌 ‘조커’ 스타일! 🤡"  
            - 차분하고 침착한 감정 유지 → "넌 ‘스네이프 교수’ 스타일! 🧙‍♂️"  
            - 항상 행복하고 긍정적인 감정 → "넌 ‘슈퍼 마리오’ 스타일! 🍄"  
            - 강한 감정을 표현하고 열정적 → "넌 ‘아이언맨’ 스타일! 🦾"  

            감정 변화 데이터:
            {request_message}
            """
        elif analysis_mode == "emotion":
            print("🔹 감정 유형 테스트 모드 활성화됨")
            prompt = f"""
            [답변 모드 : 감정 유형 테스트 모드]사용자의 감정 변화 데이터를 기반으로, 심리테스트 결과처럼 분석해줘.
            사용자의 감정 패턴을 재미있는 유형으로 분류하고, 그 사람의 성격을 해석해줘.
            유머러스한 방식으로 작성해줘. 이모티콘도 적절히 추가하고, 1줄로 20자 이내로 짧게 만들어줘!

            💡 **예시**
            - 감정 변화가 롤러코스터처럼 심함 → "넌 감정 폭풍형! 🌪️ 하루에도 열두 번 변해요!"  
            - 웃음 반응이 많음 → "넌 긍정 에너자이저! 😆 웃음 없이 못 사는 타입!"  
            - 슬픔 반응이 많음 → "넌 감성 시인! 🎭 작은 일에도 깊이 공감하는 타입!"  
            - 놀람 반응이 자주 나타남 → "넌 감정 탐험가! 🚀 세상이 늘 신기한 모험 같아!"  
            - 감정 변화가 거의 없음 → "넌 득도한 자! 🏯 아무 일에도 동요하지 않아!"  
    

            감정 변화 데이터:
            {request_message}
            """
        elif analysis_mode == "poem":
            print("🔹 찐반응 시인봇 모드 활성화됨")
            prompt = f"""
            [답변 모드 : 찐반응 시인봇 모드]너는 용자의 표정 변화 데이터를 기반으로 **재미있고 감성적인 시**를 지어줘.
            짧고 리듬감 있는 문장으로 감정을 표현하고, 유머를 추가하면 더 좋아.  
            각 줄마다 ✨이모티콘✨을 적절히 넣어서 감성을 살려줘.
            
            💡 **포맷 예시**
            📝 "기쁨이 있는 그대 얼굴 또 보고 싶은데, 😆  
            놀람이 찾아와 나를 놀라게 하네 😲  
            슬픔이 지나가며 아픈 그대 마음 😢  
            그대 얼굴은 감정의 폭풍으로 휘몰아치네 🌪️"
    
            감정 변화 데이터:
            {request_message}
            """
        # ✅ 일반적인 메시지 처리
        else:

            prompt = f"""
            사용자가 질문이 있는지 먼저 확인 후, 질문에 맞는 대답을 해줘.
            사용자 질문이 없으면, 사용자의 감정 변화를 분석해서 가장 높은 감정을 바탕으로 '감정변화 분석 답변'을 간단하게 작성해줘.
            1줄로 20자 이내로 짧게 작성해줘
            
            **감정변화 분석 답변 포맷 예시**
            - "웃음이 60% 라니, 이 영상, 개그 고수 인정? 😆"
            - "슬픔이 70%라니, 눈물 짓게 한 영상이었죠? 이젠 웃을 시간! 다음 영상 GO!" 
            - "놀람 80%! 무슨 일이죠? 😱 헉! 심장 괜찮아요? 😱"  
            - "중립 90%?! 감정 컨트롤 무엇? 무표정 고수 등장! 😐"
            - "분노 70%?! 분노 게이지 MAX! 진정하세요~"  

            ** 사용자의 질문 여부 확인 후, 답변 생성!**

            - 사용자의 감정 변화 데이터: {emotion_data}
            - 감정 비율: {emotion_percentages}
            - 사용자가 보낸 메시지: {request_message}
            - {auto_prompt_cmd}"""
        
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
    #"disgust": "역겨움",
    #"fear": "두려움",
    "happy": "웃음",
    "sadness": "슬픔",
    "panic": "놀람",
    "normal": "중립"
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


def analyze_emotion_with_vggface(face_roi):
    """ VGGFace 기반 감정 분석 """
    try:
        if face_roi is None or face_roi.size == 0:
            print("⚠ 감정 분석 실패: face_roi가 비어 있음")
            return "해석 불가"

        # ✅ 이미지 전처리
        #print(f"📷 얼굴 감정 분석 중... 입력 크기: {face_roi.shape}")  # 입력 데이터 확인
        face_roi = cv2.resize(face_roi, (224, 224))  # 모델 입력 크기에 맞춤
        face_roi = np.expand_dims(face_roi, axis=0)  # 배치 차원 추가
        face_roi = face_roi / 255.0  # 정규화

        # ✅ 모델 예측 수행
        preds = emotion_model.predict(face_roi)[0]  
        #print(f"📊 감정 분석 결과: {preds}")  # 모델 출력 확인

        emotion_idx = np.argmax(preds)
        #print(f"🎭 감정 인덱스: {emotion_idx}")  # 감정 인덱스 확인

        # ✅ 감정 레이블이 제대로 정의되어 있는지 확인
        if 'emotion_labels' not in globals():
            print("⚠ 감정 분석 실패: emotion_labels가 정의되지 않음")
            return "해석 불가"

        predicted_emotion = emotion_labels[emotion_idx]

        # ✅ 영어 감정을 한글로 변환하여 반환
        translated_emotion = emotion_translation.get(predicted_emotion, "해석 불가")

        print(f"✅ 감정 분석 결과 (한글 변환됨): {translated_emotion}")

        return translated_emotion  # ✅ 한글 변환된 감정 반환

    except Exception as e:
        print(f"⚠ 감정 분석 실패: {e}")
        return "해석 불가"




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
            

            # ✅ 4. DeepFace 감정 분석 수행, # ✅ 감정 분석 실행 (한글 변환 적용) ==> 튜닝 모델 적용
            #emotion_result = analyze_emotion_with_deepface(face_roi)
            emotion_result = analyze_emotion_with_vggface(face_roi)
            #✅ 영어 감정 결과를 한글로 변환#
            #emotion_result_kor = emotion_translation.get(emotion_result, "해석 불가")

           

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
    global emotion_model # ✅ 전역 변수 사용하여 모델이 다시 로드되지 않도록 함.
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

@app.route('/get_video_emotion_stats')
def get_video_emotion_stats():
    """ MongoDB에서 모든 영상의 감정 통계를 가져와 정렬하여 반환 """

    # ✅ 모든 영상 목록 가져오기 (감정 데이터 없는 영상도 포함)
    all_videos = list(video_collection.find({}, {"_id": 0, "url": 1, "title": 1}))

    # ✅ 감정 데이터 가져오기
    pipeline = [
        {"$group": {"_id": "$video_id", "emotions": {"$push": "$emotion"}}}
    ]
    results = list(face_collection.aggregate(pipeline))

    # ✅ 감정 통계 계산
    video_emotion_stats = {}
    video_total_counts = {}  # ✅ 각 영상별 총 감정 데이터 개수 저장

    excluded_emotions = {"중립", "두려움", "해석 불가"}

    for entry in results:
        video_id = entry["_id"]
        emotion_list = entry["emotions"]

        emotion_counts = {}
        for emotion in emotion_list:
            if emotion not in excluded_emotions:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        video_total_counts[video_id] = sum(emotion_counts.values())

        total = video_total_counts[video_id]
        if total > 0:
            emotion_percentages = {
                emotion: round((count / total) * 100, 2) 
                for emotion, count in sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)
            }
        else:
            emotion_percentages = {}

        video_emotion_stats[video_id] = emotion_percentages

    # ✅ 영상 ID -> 제목 매핑
    video_titles = {video["url"].split("?v=")[-1]: video["title"] for video in all_videos}

    # ✅ 감정 데이터 없는 영상도 포함하여 title 추가
    sorted_videos = []
    for video in all_videos:
        video_id = video["url"].split("?v=")[-1].split("&")[0]
        title = video.get("title", "제목 없음")
        emotions = video_emotion_stats.get(video_id, {})
        sorted_videos.append({"video_id": video_id, "title": title, "emotions": emotions})

    # ✅ 감정 데이터 개수가 많은 순으로 정렬
    sorted_videos.sort(key=lambda x: video_total_counts.get(x["video_id"], 0), reverse=True)

    return jsonify({"sorted_videos": sorted_videos})





if __name__ == '__main__':
    try:
        print("🚀 Flask 서버 시작 중...")
        #app.run(debug=False, use_reloader=False,threaded=False) # ✅ 멀티스레딩 비활성화
        app.run(debug=False) # ✅ 멀티스레딩 비활성화
    except Exception as e:
        print(f"❌ Flask 실행 중 오류 발생: {e}")
        traceback.print_exc()  # ✅ 예외의 전체 트레이스백을 출력