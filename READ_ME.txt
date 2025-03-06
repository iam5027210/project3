# FacePick 프로젝트

##  개요
FacePick은 **DeepFace 기반 얼굴 감정 분석 & 추천 시스템**을 구현하는 웹 애플리케이션입니다.  
Flask 백엔드를 기반으로, MongoDB, OpenAI API, TensorFlow 등을 활용하여 감정 분석 및 챗봇 기능을 제공합니다.

---

##  가상환경 설정 방법

# Conda 환경 생성
conda create --name facepick_env --file requirement_deepface_pj_df.txt

# 가상환경 활성화
conda activate facepick_env


# 가상환경 생성 (파이썬 >=3.9 필요)
python -m venv facepick_env

# 필요 패키지 설치
pip install -r pip_requirements_deepface_pj_df.txt


#Flask 실행
python main.py


## API 키는 2개 (OpenAI API, Youtube API) 가 필요!!
#OpenAI API 키
#API 키 파일 경로 지정
api_key_path = "C:/ex/openai/api_key.txt"


#  유튜브 API 키 설정
api_key_path = "C:/ex/openai/youtube_api_key.txt"