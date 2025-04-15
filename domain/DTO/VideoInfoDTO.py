# 요약 모델
from pydantic import BaseModel


class VideoInfo(BaseModel):
    id: str | None = None
    title: str | None = None
    duration: str | None = None
    url: str | None = None
    description: str | None = None
    channel: str | None = None
    published_at: str | None = None
    thumbnail: str | None = None
