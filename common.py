import os
from openai import OpenAI
from dataclasses import dataclass
import pytz
from datetime import datetime, timedelta
from pymongo import MongoClient
import random


@dataclass(frozen=True)
class Model: 
    basic: str = "gpt-3.5-turbo-1106"
    advanced: str = "gpt-4-1106-preview"
    #basic_old: str = "gpt-3.5-turbo" 


#API 키 파일 경로 지정
api_key_path = "C:/ex/openai/api_key.txt"
#파일에서 API 키 읽기
with open(api_key_path, 'r') as file:
    #openai.api_key = file.read().strip()  # 줄바꿈 제거
    api_key = file.read().strip()  # 줄바꿈 제거

# #client = openai.OpenAI(api_key=api_key)


model = Model();    
client = OpenAI(api_key=api_key, timeout=30, max_retries=1)

def chat_with_openai(message,emotion_data=None, emotion_percentages=None):
    """ OpenAI GPT API를 사용하여 챗봇 대화 수행 """
    try:
        prompt = f"""
        사용자 메시지: {message}
        감정 변화 데이터: {emotion_data}
        감정 비율: {emotion_percentages}
        (중요!)사용자 메시지를 먼저 확인 하여, 답변 모드가 있는지 확인하고,
        답변모드가 있으면 답변 모드에 맞게 답변을 해줘.
        답변모드가 없으면, 질문에 맞는 대답과 함께 사용자에게 챗봇 상단에 제공된 버튼을 눌러 영상을 보도록 유도해줘.
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # ✅ GPT-3.5 사용 (비용 절감)
            messages=[
                {"role": "system", "content": "너 이름은 '찐반응 딜리버리봇'으로, 사용자 질문에 맞는 답변을 유머러스하고 친절하게 답변하는챗봇이야. 사용자가 질문하면, 감정변화 데이터와 감정비율 데이터터를 바탕으로 재밌게 답변해줘."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=120
        )
        return response.choices[0].message.content  # ✅ 올바른 방식으로 응답 추출
    except Exception as e:
        print(f"❌ OpenAI API 요청 중 오류 발생: {e}")
        return "[OpenAI API 요청 실패]"


def makeup_response(message, finish_reason="ERROR"):
    return {
                "choices": [
                    {
                        "finish_reason": finish_reason,
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": message
                        }                   
                    }
                ],
                "usage": {"total_tokens": 0},
            }

def today():
    korea = pytz.timezone('Asia/Seoul')# 한국 시간대를 얻습니다.
    now = datetime.now(korea)# 현재 시각을 얻습니다.
    return(now.strftime("%Y%m%d"))# 시각을 원하는 형식의 문자열로 변환합니다.

def yesterday():    
    korea = pytz.timezone('Asia/Seoul')# 한국 시간대를 얻습니다.
    now = datetime.now(korea)# 현재 시각을 얻습니다.
    one_day = timedelta(days=1)    # 하루 (1일)를 나타내는 timedelta 객체를 생성합니다.
    yesterday = now - one_day # 현재 날짜에서 하루를 빼서 어제의 날짜를 구합니다.
    return yesterday.strftime('%Y%m%d') # 어제의 날짜를 yyyymmdd 형식으로 변환합니다.

def currTime():
    # 한국 시간대를 얻습니다.
    korea = pytz.timezone('Asia/Seoul')
    # 현재 시각을 얻습니다.
    now = datetime.now(korea)
    # 시각을 원하는 형식의 문자열로 변환합니다.
    formatted_now = now.strftime("%Y.%m.%d %H:%M:%S")
    return(formatted_now)    



# ✅ MongoDB 연결
mongo_cluster = MongoClient("mongodb+srv://admin:admin1234@cluster0.uvix1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = mongo_cluster["wassup3"]  # ✅ "wassup3" 데이터베이스 선택
video_collection = db["videos"]  # ✅ "videos" 컬렉션 선택
face_collection = db["faces"]

def extract_video_id(raw_url):
    """ YouTube URL에서 video_id를 추출하는 함수 """
    if "watch?v=" in raw_url:
        return raw_url.split("?v=")[-1].split("&")[0]
    elif "/shorts/" in raw_url:
        return raw_url.split("/shorts/")[-1].split("?")[0]
    else:
        return raw_url.split("/")[-1].split("?")[0]

def get_random_video():
    """ MongoDB에서 랜덤한 영상 추천 (Flask 라우트 형식으로 변환) """
    
    video = video_collection.aggregate([{ "$sample": { "size": 1 } }])  # ✅ 1개의 랜덤 영상 가져오기
    video = list(video)  # Cursor를 리스트로 변환
    
    if video:
        video_data = video[0]

        if "url" in video_data:
            video_id = extract_video_id(video_data["url"])  # ✅ URL에서 video_id 추출
        else:
            print("⚠️ MongoDB에 'url' 필드가 없습니다. 기본 추천 영상을 반환합니다.")
            return "http://127.0.0.1:5000/video/default"  # ✅ 기본 추천 영상
        
        return f"http://127.0.0.1:5000/video/{video_id}"  # ✅ Flask 라우트 형식으로 변환
    
    return "http://127.0.0.1:5000/video/default"  # ✅ 영상이 없을 경우 기본 영상 반환ㅍ