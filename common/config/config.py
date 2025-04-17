# 필요한 환경 변수들을 전역 상수로 정리
from dotenv import load_dotenv
import os

# .env 파일 로딩
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_PLACE_SEARCH_URL = os.getenv("NAVER_PLACE_SEARCH_URL")
BACKEND_URL = os.getenv("BACKEND_URL")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
PROXY_USERNAME = os.getenv("PROXY_USERNAME")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")