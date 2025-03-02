from pymongo import MongoClient

# ✅ MongoDB 연결 설정

# MongoDB 연결
mongo_cluster = MongoClient("mongodb+srv://admin:admin1234@cluster0.uvix1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = mongo_cluster["wassup3"]
video_collection = db["videos"]

# ✅ 삽입할 유튜브 영상 데이터
# 유튜브 영상 리스트 (중복 제거 및 정리된 형식)
new_videos = [
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

# ✅ 중복된 URL을 방지하고 데이터 삽입 (중복 검사 후 삽입)
for video in new_videos:
    if not video_collection.find_one({"url": video["url"]}):  # 같은 URL이 없을 경우만 추가
        video_collection.insert_one(video)
        print(f"✅ 삽입 완료: {video['url']}")
    else:
        print(f"⚠ 이미 존재하는 데이터: {video['url']}")

print("✅ 모든 영상 데이터 삽입 완료!")
