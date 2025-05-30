from pprint import pprint
from typing import List

from fastapi import APIRouter, Header
from pydantic import BaseModel
from starlette.responses import JSONResponse

from domain.DTO.DTO import KeywordDTO
from domain.service.MergeKeywords import MargeKeywords

router = APIRouter()


def init_KeywordProcessing_controller(app):
    app.include_router(router, prefix="/api/keyword/processing")  # 기본 url 설정


@router.post("/shopping")
async def keyword_combinations(request: List[str]):
    data = await MargeKeywords.get_shopping_keywords(request)
    pprint(data)

    return JSONResponse(
        status_code=200,
        content=data
    )


@router.post("/place")
async def keyword_combinations(request: List[str]):
    data = await MargeKeywords.get_place_keywords(request)
    pprint(data)
    
    return JSONResponse(
        status_code=200,
        content=data
    )
