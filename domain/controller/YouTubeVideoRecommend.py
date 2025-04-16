import json
import os
import time

from dotenv import load_dotenv
from fastapi import APIRouter, Header
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.responses import JSONResponse

from domain.service.OpenAI import create_interest_keyword
from domain.service.Youtube import VideoInfo, search_videos_by_keyword_list, get_video_details, get_video_description, \
    init_proxy

load_dotenv()
API_KEY = os.getenv("API_KEY")
router = APIRouter()


def init_YouTubeVideoRecommend_controller(app):
    app.include_router(router, prefix="/api/recommend/youtube")


class CapWords(BaseModel):
    interest_scores: dict[str, int] | None = None


def auth(api: str):
    if not api == API_KEY:
        raise RequestValidationError("API_KEY is invalid")


@router.post("")
async def recommend_video_list(request: CapWords,
                               max_search_keyword: int = 1,
                               max_results: int = 5,
                               api_key: str = Header(None)):
    auth(api_key)

    if request.interest_scores is None:
        raise RequestValidationError("interest_list is None")

    # # 시작 시간 계산
    start_time = time.time()

    keyword = json.dumps(request.interest_scores)
    interest_keyword = await create_interest_keyword(keyword, max_search_keyword)
    # 전체 비디오
    videos_for_keyword: list[VideoInfo] = await search_videos_by_keyword_list(interest_keyword, max_results)

    video_data = [video.model_dump() for video in videos_for_keyword]

    end_time = time.time()  # 끝 시간 저장
    print(f"\n전체 실행 시간: {end_time - start_time:.2f}초")

    return JSONResponse(
        status_code=200,
        content={
            "meta": {
                "search_keyword": interest_keyword,
                "running_time": end_time - start_time
            },
            "data": video_data
        }
    )


@router.get("/summary")
async def video_summary(video_id: str,
                        api_key: str = Header(None),
                        proxy_username: str = Header(None),
                        proxy_password: str = Header(None)
                        ):
    auth(api_key)
    print(f"video_id: {video_id}")
    print(f"proxy_username: {proxy_username}")
    print(f"proxy_password: {proxy_password}")

    # # 시작 시간 계산
    start_time = time.time()
    video_info: VideoInfo = (await get_video_details([video_id])).pop()

    print(f"video_info: {video_info}")

    # 프록시 초기화
    ytt_api = init_proxy(proxy_username, proxy_password)

    video_info.description = await get_video_description(video_info, ytt_api)

    # if video_info.description is None:
    #     video_info.description = "설명과 자막이 모두 제공되지 않았습니다."

    end_time = time.time()  # 끝 시간 저장
    print(f"\n전체 실행 시간: {end_time - start_time:.2f}초")

    return JSONResponse(
        status_code=200,
        content={
            "meta": {
                "video_id": video_id,
                "running_time": end_time - start_time
            },
            "data": {
                "description": video_info.description
            }
        }
    )
