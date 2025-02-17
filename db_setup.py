from pymongo import MongoClient
import requests

# MongoDB 연결
mongo_cluster = MongoClient("mongodb+srv://admin:admin1234@cluster0.uvix1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = mongo_cluster["jjinchin"]
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
    data = response.json()
    if "items" in data and len(data["items"]) > 0:
        return data["items"][0]["snippet"]["title"]
    return "Unknown Title"


# 유튜브 영상 리스트
new_videos  = [
    {"url": "https://www.youtube.com/shorts/VE1gnReqKsY"},
    {"url": "https://www.youtube.com/watch?v=99NQdS6VELU"},
    {"url": "https://www.youtube.com/watch?v=mOxLo5A8Y3E"},
    {"url": "https://www.youtube.com/watch?v=1Fk3UlaujNY"},
    {"url": "https://www.youtube.com/shorts/H-ROI37pVXU"},
    {"url": "https://www.youtube.com/shorts/N1zxJPaq2Vc"},
    {"url": "https://www.youtube.com/shorts/tdVerNcKlH0"},
    {"url": "https://www.youtube.com/shorts/3HKPyhATe3I"},
    {"url": "https://www.youtube.com/shorts/bm2CBCZdEy4"},
    {"url": "https://www.youtube.com/shorts/IzZ4-dYb4pE"},
    {"url": "https://www.youtube.com/shorts/zmS0dxGGS34"},
    {"url": "https://youtu.be/5yhRoEbSqjk"},
    {"url": "https://www.youtube.com/shorts/is3KHKNWPF0?feature=share"},
    {"url": "https://www.youtube.com/shorts/hgBF2yg_byE"},
    {"url": "https://www.youtube.com/watch?v=sjWONSB4Wic"},
    {"url": "https://www.youtube.com/shorts/qUtT8QfuJhI"},
    {"url": "https://www.youtube.com/watch?v=XMj8ty1eFe8"},
    {"url": "https://www.youtube.com/watch?v=J8enZyzFUg8"},
]


# ✅ 기존 MongoDB의 모든 영상에 `title` 추가
videos = list(video_collection.find({"title": {"$exists": False}}, {"_id": 0, "url": 1}))

for video in videos:
    video_id = video["url"].split("?v=")[-1].split("&")[0] if "watch?v=" in video["url"] else video["url"].split("/")[-1]
    title = get_youtube_title(video_id)

    video_collection.update_one({"url": video["url"]}, {"$set": {"title": title}})
    print(f"✅ 업데이트 완료: {title}")

print("✅ 모든 영상의 제목 업데이트 완료!")

