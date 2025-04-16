import os
import re
import traceback
from itertools import islice

from dotenv import load_dotenv
from fastapi.exceptions import RequestValidationError
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, FetchedTranscriptSnippet
from googleapiclient.discovery import build
from youtube_transcript_api.proxies import WebshareProxyConfig

from domain.DTO.VideoInfoDTO import VideoInfo
from domain.service.OpenAI import create_summary

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=API_KEY)


# 포맷 보조 함수
async def format_duration(duration: str) -> tuple[str, int]:
    # ISO 8601 형식: PT#H#M#S
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return "00:00", 0

    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}", hours * 3600 + minutes * 60 + seconds


async def format_published_at(published_at: str) -> str:
    return published_at.replace("T", " ").replace("Z", "")


# 영상 검색
async def search_youtube(query: str = None, max_results: int = 1) -> list[str]:
    if not query:
        raise RequestValidationError("query is required")
    try:
        response = youtube.search().list(
            q=query,
            part="id",
            maxResults=max_results,
            type="video"
        ).execute()
        return [item["id"]["videoId"] for item in response.get("items", [])]
    except Exception:
        raise Exception("YouTube API token limit exceeded")


# 자막 가져오기 (자막 없는 경우 None)
async def get_video_subtitles(video_details: VideoInfo, ytt_api):
    video_id = video_details.id
    try:
        transcript_list = ytt_api.list(video_id)
        try:
            transcript = transcript_list.find_manually_created_transcript(['ko'])
        except NoTranscriptFound:
            transcript = transcript_list.find_generated_transcript(['ko'])
        # subtitles = [text.text for text in islice(transcript.fetch().snippets, 20, 120)]

        # 자막을 특정 구간(20~120)까지 가져오기
        snippets = transcript.fetch().snippets
        filtered_snippets = islice(snippets, 20, 320)

        # 자막 텍스트만 추출하고 공백을 제거
        normalized = [re.sub(r'\s+', '', snippet.text) for snippet in filtered_snippets]

        # 자막을 하나로 합치기
        joined_text = " ".join(normalized).strip()
        return joined_text
    except Exception as e:
        print("Error: 예외 발생")
        print(f"예외 타입: {type(e)}")
        print(f"예외 메시지: {str(e)}")
        traceback.print_exc()
        return None


# 프록시 설정
def init_proxy(proxy_username, proxy_password):
    ytt_api = YouTubeTranscriptApi(
        proxy_config=WebshareProxyConfig(
            proxy_username=proxy_username,
            proxy_password=proxy_password,
        )
    )
    return ytt_api


# 자막이 없으면 설명 요약
async def get_video_description(video_details: VideoInfo, ytt_api) -> str:
    if not video_details:
        raise RequestValidationError("video_details is required")

    description = video_details.description
    subtitles = await get_video_subtitles(video_details, ytt_api)

    print(f"description: {description}")
    print(f"subtitles: {subtitles}")

    if not subtitles or subtitles.strip() == "":
        return await create_summary(description)
    else:
        return await create_summary(subtitles)


# 영상 상세 정보 가져오기 (batch)
async def get_video_details(video_ids: list[str]) -> list[VideoInfo]:
    if not video_ids:
        raise RequestValidationError("video_ids is required")

    response = youtube.videos().list(
        part="snippet,contentDetails",
        id=",".join(video_ids)
    ).execute()
    try:
        video_info_list = []
        for item in response.get("items", []):
            print(item)
            snippet = item.get("snippet", {})
            content = item.get("contentDetails", {})
            duration, sec = await format_duration(content.get("duration", "PT0M0S"))
            if sec < 90:  # 쇼츠 영상 제거
                continue

            video_info = VideoInfo(
                id=item.get("id", ""),
                title=snippet.get("title", "제목 없음"),
                duration=duration,
                url=f"https://www.youtube.com/watch?v={item.get('id', '')}",
                channel=str(snippet.get("channelTitle", "")),
                published_at=await format_published_at(snippet.get("publishedAt", "")),
                # description=snippet.get("description", None),
                thumbnail=snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            )
            video_info_list.append(video_info)

        return video_info_list
    except Exception:
        raise Exception("YouTube API token limit exceeded")


# YouTube에서 키워드 목록으로 영상 ID들 검색
async def get_youtube_ids(keyword_list: list[str], max_results: int = 5) -> list[str]:
    video_id_list = []
    for keyword in keyword_list:
        video_ids = await search_youtube(query=keyword, max_results=max_results)
        video_id_list.extend(video_ids)
    return video_id_list


# 키워드 리스트로 영상 상세 정보 목록 반환
async def search_videos_by_keyword_list(keyword_list: list[str], max_results: int = 5) -> list[VideoInfo]:
    video_id_list = await get_youtube_ids(keyword_list, max_results)

    # 중복 제거
    video_id_list = list(set(video_id_list))
    return await get_video_details(video_id_list)


def is_short_video(video_details: VideoInfo) -> bool:
    try:
        hours, minutes, seconds = map(int, video_details.duration.split(":"))
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds < 90  # 1분 30초
    except Exception:
        return True  # 파싱 오류시 기본적으로 short 처리
