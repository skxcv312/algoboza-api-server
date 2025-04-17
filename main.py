import json
import os

import uvicorn  # FastAPI 서버 실행에 필요
from dotenv import load_dotenv
from fastapi import FastAPI
from openai import OpenAI

from domain.controller.YouTubeVideoRecommend import init_YouTubeVideoRecommend_controller
from common.exceptionHandler.Handlers import init_exception_handler
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from pprint import pprint
from typing import List, Dict, Tuple
from typing import List, Dict

# .env 로드
load_dotenv()

# controller에 fastAPI 할당

client = OpenAI()
app = FastAPI()
init_YouTubeVideoRecommend_controller(app)
init_exception_handler(app)

# 환경 변수 할당
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_PLACE_SEARCH_URL = os.getenv("NAVER_PLACE_SEARCH_URL")
BACKEND_URL = os.getenv("BACKEND_URL")


class InterestScore(BaseModel):
    keyword: str
    score: int


class Exploration(BaseModel):
    view: List[Dict]
    search: List[Dict]
    category: List[Dict]
    purchase: List[Dict]


class UserData(BaseModel):
    user_id: int
    timestamp: str
    exploration: Exploration
    interest_scores: List[InterestScore]


@app.post("/analyze/")
async def analyze_user_data(user_data: UserData):
    # 관심 점수 50 이상 키워드만 사용
    interest_keywords = [item.keyword for item in user_data.interest_scores if item.score > 50]

    if not interest_keywords:
        raise HTTPException(status_code=400, detail="관심 키워드가 없습니다.")

    # 사용자 의도 분석 (쇼핑 or 장소 추천)
    user_intent, intent_type = analyze_intent_with_type(interest_keywords)

    # 결과 저장 변수
    naver_results = []
    naver_places = []

    # 사용자가 쇼핑을 원하면 네이버 쇼핑 API 호출
    if intent_type == "shopping":
        naver_results = await naver_shopping_search(user_intent)

    # 사용자가 장소 추천을 원하면 네이버 지역 검색 API 호출
    elif intent_type == "places":
        naver_places = await naver_places_search(user_intent)

    return {
        "user_intent": user_intent,
        "intent_type": intent_type,
        "naver_results": naver_results,
        "naver_places": naver_places
    }


def analyze_intent_with_type(keywords: List[str]) -> Tuple[str, str]:
    """키워드를 기반으로 사용자의 의도와 검색 유형(쇼핑/장소 추천) 구분"""
    system_prompt = f"""
    사용자의 관심 키워드는 다음과 같아: {', '.join(keywords)}.
    사용자가 원하는 것이 '쇼핑'인지 '위치 추천'인지 판단해서 반환해줘.

    예시:
    - '운동화, 나이키, 러닝화' → 'shopping'
    - '한식, 맛집, 서울 맛집' → 'places'

    'shopping' 또는 'places' 중 하나를 선택하고,
    사용자가 검색할 구체적인 문장도 함께 만들어줘.

    출력 형식:
    - 쇼핑 예시: "나이키 운동화", "shopping"
    - 장소 추천 예시: "서울 한식당", "places"
    
    단 이거는 예시일 뿐 따라할 필요는 없어
    """

    response = client.responses.create(
        model="gpt-3.5-turbo",
        input=[
            {
                "role": "system",  # 시스템 프롬포트로 더 일관된 답변 얻을 수 잇음
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": str(', '.join(keywords))
            }
        ]
    )

    output_text = response.model_dump()["output"][0]["content"][0]["text"]
    print("output_text : " + output_text)

    parts = output_text.rsplit(",", 1)  # 마지막 콤마 기준으로 분리

    if len(parts) == 2:
        search_query = parts[0].strip().strip('"')
        intent_type = parts[1].strip().strip('"')
        if intent_type not in ["shopping", "places"]:
            intent_type = "shopping"  # 기본값 설정
    else:
        search_query = output_text.strip()
        intent_type = "shopping"

    return search_query, intent_type


async def naver_shopping_search(query: str):
    """네이버 쇼핑 API 호출"""
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {"query": query, "display": 5, "sort": "sim"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="네이버 쇼핑 API 호출 실패")

        data = response.json()
        return data.get("items", [])[:5]  # 최대 5개 반환


async def naver_places_search(query: str):
    """네이버 지역 검색 API 호출"""
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {"query": query, "display": 5, "sort": "random"}

    async with httpx.AsyncClient() as client:
        response = await client.get(NAVER_PLACE_SEARCH_URL, headers=headers, params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="네이버 지역 검색 API 호출 실패")

        data = response.json()
        places = data.get("items", [])

        return [
            {
                "title": place["title"],
                "address": place["address"],
                "category": place["category"],
                "link": place["link"]
            }
            for place in places
        ]


# 실행 진입점
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
