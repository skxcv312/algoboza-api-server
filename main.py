import random
from pprint import pprint
import asyncio

import uvicorn  # FastAPI 서버 실행에 필요
import openai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from typing import Tuple, List, Dict
from common.config.environment import *
from domain.controller.KeywordProcessing import init_KeywordProcessing_controller
from domain.controller.YouTubeVideoRecommend import init_YouTubeVideoRecommend_controller
from common.exceptionHandler.Handlers import init_exception_handler

# OpenAI API key 설정
openai.api_key = 'your-openai-api-key'

# FastAPI 앱 초기화
app = FastAPI()
init_YouTubeVideoRecommend_controller(app)
init_exception_handler(app)
init_KeywordProcessing_controller(app)


# 데이터 모델 정의
class InterestScore(BaseModel):
    keyword: str
    type: str  # 쇼핑 / 장소
    options: List[str]  # 추가 정보


class MetaData(BaseModel):
    location: str
    birth_date: str
    timestamp: str
    note: str


class UserData(BaseModel):
    user_id: int
    meta_data: MetaData
    interest_scores: List[InterestScore]


@app.post("/analyze")
async def analyze_user_data(user_data: UserData):
    # 관심 키워드에서 옵션 필터링 및 쇼핑/장소 분석
    print("/analyze")
    pprint(user_data)

    naver_results = {}
    naver_places = {}

    async def process_interest(interest: InterestScore):
        keyword = interest.keyword
        options = interest.options

        if interest.type == "shopping":
            shopping_results = await naver_shopping_search(keyword, options)
            if shopping_results:
                seen_titles = set()
                deduplicated = []
                for item in shopping_results:
                    title = item.get("title", "")
                    if title not in seen_titles:
                        seen_titles.add(title)
                        deduplicated.append(item)
                return "shopping", keyword, deduplicated

        elif interest.type == "place":
            place_results = await naver_places_search(keyword, options)
            if place_results:
                return "place", keyword, place_results

        return None, None, None

    tasks = [process_interest(interest) for interest in user_data.interest_scores]
    results = await asyncio.gather(*tasks)

    for result_type, keyword, data in results:
        if result_type == "shopping":
            naver_results[keyword] = data
        elif result_type == "place":
            naver_places[keyword] = data

    pprint(naver_results)
    pprint(naver_places)

    return {
        "user_id": user_data.user_id,
        "naver_results": naver_results,
        "naver_places": naver_places
    }


async def naver_shopping_search(query: str, options: List[str]):
    """네이버 쇼핑 API 호출"""
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }

    results = []
    search_targets = options if options else [""]

    async with httpx.AsyncClient() as client:
        for option in search_targets:
            query_with_option = option if option else query
            params = {"query": query_with_option, "display": 4, "sort": "sim"}

            response = await client.get(url, headers=headers, params=params)
            if response.status_code != 200:
                continue

            data = response.json()
            items = data.get("items", [])
            results.extend(items)

    return results


async def naver_places_search(query: str, options: List[str]):
    """네이버 지역 검색 API 호출"""
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }

    # 옵션 중 하나를 랜덤으로 선택
    random_option = random.choice(options) if options else ""

    # query와 붙이기
    query_with_random_option = f"{query} {random_option}"
    params = {"query": query_with_random_option, "display": 4, "sort": "random"}
    print("query_with_random_option" + query_with_random_option)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="네이버 지역 검색 API 호출 실패")

        data = response.json()
        places = data.get("items", [])

        # 장소 정보 반환시 link가 없으면 네이버 지도 링크 추가
        return [
            {
                "title": place["title"],
                "address": place["address"],
                "category": place["category"],
                "lng": float(place['mapx']) / 1e7,
                "lat": float(place['mapy']) / 1e7,
                "link": generate_naver_map_link(place)
            }
            for place in places
        ]


from urllib.parse import quote  # URL 인코딩을 위해 필요


def generate_naver_map_link(place: Dict) -> str:
    """장소 제목 기반 네이버 지도 검색 링크 생성"""
    title = place.get("title", "").replace("<b>", "").replace("</b>", "").strip()
    if not title:
        return "https://map.naver.com/v5"

    encoded_title = quote(title)  # URL 인코딩 (예: 홍대입구역 → %ED%99%8D%EB%8C%80%EC%9E%85%EA%B5%AC%EC%97%AD)
    return f"https://map.naver.com/p/search/{encoded_title}"


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
    """

    response = openai.Completion.create(
        model="gpt-3.5-turbo",  # 사용할 모델명 설정
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": ', '.join(keywords)}
        ],
        max_tokens=100
    )

    output_text = response['choices'][0]['message']['content']
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


# 실행 진입점
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

# TEST
