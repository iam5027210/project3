from pymongo import MongoClient
import requests

# MongoDB 연결
mongo_cluster = MongoClient("mongodb+srv://admin:admin1234@cluster0.uvix1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = mongo_cluster["wassup3"]
video_collection = db["videos"]


# ✅ 유튜브 API 키 설정
api_key_path = "C:/ex/openai/youtube_api_key.txt"
#파일에서 API 키 읽기
with open(api_key_path, 'r') as file:
    #openai.api_key = file.read().strip()  # 줄바꿈 제거
    API_KEY = file.read().strip()  # 줄바꿈 제거

# ✅ 유튜브 제목 가져오기 함수

def get_youtube_title(video_id):
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={API_KEY}"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"❌ 유튜브 API 호출 실패! 상태 코드: {response.status_code}")
        return "Unknown Title"
    
    data = response.json()
    
    if "items" in data and len(data["items"]) > 0:
        return data["items"][0]["snippet"]["title"]
    
    print(f"⚠ 제목을 찾을 수 없음: {video_id}")
    return "Unknown Title"


# 유튜브 영상 리스트 (중복 제거 및 정리된 형식)
videos = [
    {"url": "https://www.youtube.com/watch?v=rMbehw7yO6w"},
    {"url": "https://www.youtube.com/watch?v=ToDXWIxrggE"},
    {"url": "https://www.youtube.com/watch?v=TojU5kOr5H0"},
    {"url": "https://www.youtube.com/watch?v=a53aJIuQ1ck"},
    {"url": "https://www.youtube.com/watch?v=q6qQbLqw3dQ"},
    {"url": "https://www.youtube.com/watch?v=iuIzniSa1Hs"},
    {"url": "https://www.youtube.com/watch?v=lEqjUJuG96o"},
    {"url": "https://www.youtube.com/watch?v=ERuG8GXW3tE"},
    {"url": "https://www.youtube.com/watch?v=FQZhehVRSXQ"},
    {"url": "https://www.youtube.com/watch?v=2Yw8lKEzJmk"},
    {"url": "https://www.youtube.com/watch?v=C6TR5PLcGho"},
    {"url": "https://www.youtube.com/watch?v=xuipMVkGnzY"},
    {"url": "https://www.youtube.com/watch?v=cY04XjQEJyE"},
    {"url": "https://www.youtube.com/watch?v=35DbAy41w7k"},
    {"url": "https://www.youtube.com/watch?v=YAATBERHY1k"},
    {"url": "https://www.youtube.com/watch?v=pcKumFEpePs"},
    {"url": "https://www.youtube.com/watch?v=gQmmS5E-_gg"},
    {"url": "https://www.youtube.com/watch?v=ivjr4WYE5Ic"},
    {"url": "https://www.youtube.com/watch?v=Nh6K29xTBIw"},
    {"url": "https://www.youtube.com/watch?v=6xZpYcQe4aQ"},
    {"url": "https://www.youtube.com/watch?v=7xZpYcQe4bB"},
    {"url": "https://www.youtube.com/watch?v=8xZpYcQe4cC"},
    {"url": "https://www.youtube.com/watch?v=9xZpYcQe4dD"},
    {"url": "https://www.youtube.com/watch?v=AxZpYcQe4eE"},
    {"url": "https://www.youtube.com/watch?v=BxZpYcQe4fF"},
    {"url": "https://www.youtube.com/watch?v=CxZpYcQe4gG"},
    {"url": "https://www.youtube.com/watch?v=DxZpYcQe4hH"},
    {"url": "https://www.youtube.com/watch?v=ExZpYcQe4iI"},
    {"url": "https://www.youtube.com/watch?v=FxZpYcQe4jJ"}
]


# ✅ 기존 MongoDB의 모든 영상에 `title` 추가
videos = list(video_collection.find({"title": {"$exists": False}}, {"_id": 0, "url": 1}))

for video in videos:
    video_id = video["url"].split("?v=")[-1].split("&")[0] if "watch?v=" in video["url"] else video["url"].split("/")[-1]
    title = get_youtube_title(video_id)


    result = video_collection.update_one({"url": video["url"]}, {"$set": {"title": title}})
    if result.matched_count > 0:
        print(f"✅ 업데이트 성공: {title} ({video['url']})")
    else:
        print(f"⚠ 업데이트 실패: {video['url']} (DB에서 찾을 수 없음)")
    print(f"✅ 업데이트 완료: {title}")

print("✅ 모든 영상의 제목 업데이트 완료!")

