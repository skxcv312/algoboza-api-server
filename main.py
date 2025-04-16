import os

import uvicorn  # FastAPI 서버 실행에 필요
from dotenv import load_dotenv
from fastapi import FastAPI

from domain.controller.YouTubeVideoRecommend import init_YouTubeVideoRecommend_controller
from common.exceptionHandler.Handlers import init_exception_handler

# .env 로드
load_dotenv()

app = FastAPI()
init_YouTubeVideoRecommend_controller(app)
init_exception_handler(app)

# 실행 진입점
# 테스트 서버 실행
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
