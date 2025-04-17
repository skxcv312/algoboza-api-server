import json
import os
import time

from fastapi import APIRouter, Header
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.responses import JSONResponse

from domain.DTO.VideoInfoDTO import VideoInfoDTO
from domain.service.OpenAI import OpenAIService
from domain.service.Youtube import YoutubeService

# 과금 방지를 위해 api key를 따로 만들었으나 필요 없을듯

router = APIRouter()


# main app을 라우팅
def init_YouTubeVideoRecommend_controller(app):
    app.include_router(router, prefix="/api/recommend/youtube")  # 기본 url 설정


# api키 확인
# API_KEY = os.getenv("API_KEY")
# def auth(api: str):
#     if not api == API_KEY:
#         raise RequestValidationError("API_KEY is invalid")
#

# 관심사 키워드 DTO
class CapWordsDTO(BaseModel):
    interest_scores: dict[str, int] | None = None


# 비디오 추천 controller
@router.post("")
async def recommend_video_list(request: CapWordsDTO,
                               max_search_keyword: int = 1,  # 값이 없을 경우 기본 1
                               max_results: int = 5,  # 값이 없을 경우 기본 5
                               api_key: str = Header(None)):
    # auth(api_key)

    if request.interest_scores is None:
        raise RequestValidationError("interest_list is None")

    # # 시작 시간 계산
    start_time = time.time()

    keyword = json.dumps(request.interest_scores)
    interest_keyword = await OpenAIService.create_interest_keyword(keyword, max_search_keyword)
    # 키워드로 검색한 VideoInfDTO 리스트
    videos_for_keyword: list[VideoInfoDTO] = await YoutubeService.search_videos_by_keyword_list(interest_keyword,
                                                                                                max_results)

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


# 비디오 요약 controller
@router.get("/summary")
async def video_summary(video_id: str,
                        api_key: str = Header(None)):
    # auth(api_key)

    # # 시작 시간 계산
    start_time = time.time()
    video_info: VideoInfoDTO = (await YoutubeService.get_video_details([video_id])).pop()

    print(f"video_info: {video_info}")

    # 비디오 요약 본문 얻기
    video_info.description = await YoutubeService.get_video_description(video_info)

    end_time = time.time()  # 끝 시간 저장
    print(f"\n전체 실행 시간: {end_time - start_time:.2f}초")

    return JSONResponse(
        status_code=200,
        content={
            "meta": {
                "video_id": video_id,
                "running_time": end_time - start_time  # 총 실행 시간
            },
            "data": {
                "description": video_info.description
            }
        }
    )
