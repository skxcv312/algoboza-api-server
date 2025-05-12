from pydantic import BaseModel


class KeywordDTO(BaseModel):
    keyword: str  # 키워드 이름
    score: float  # 키워드 점수


class CombinedKeywordsDTO(BaseModel):
    keyword: str | None = None
    options: list[str] | None = None
