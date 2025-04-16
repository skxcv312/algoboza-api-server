import os
import re
import traceback
from itertools import islice

from dotenv import load_dotenv
from fastapi.exceptions import RequestValidationError
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
from googleapiclient.discovery import build
from youtube_transcript_api.proxies import WebshareProxyConfig

from domain.DTO.VideoInfoDTO import VideoInfoDTO
from domain.service.OpenAI import OpenAIService


class YoutubeService:
    # 클래스 변수 초기화
    API_KEY = os.getenv("YOUTUBE_API_KEY")
    PROXY_USERNAME = os.getenv("PROXY_USERNAME")  # 프록시 설정
    PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")

    # 자막중에서 gpt에게 전달할 문자열 길이 변수
    START_SENTENCE = 20  # 시작 문장
    END_SENTENCE = 220  # 마지막 문장

    MIN_VIDEO_LENGTH = 90  # 최소 영상 길이 (sec)

    youtube = build("youtube", "v3", developerKey=API_KEY)  # youtube api 설정
    ytt_api = YouTubeTranscriptApi(  # youtube proxy 설정
        proxy_config=WebshareProxyConfig(
            proxy_username=PROXY_USERNAME,
            proxy_password=PROXY_PASSWORD,
        )
    )

    # 시간 정규화
    @staticmethod
    async def format_duration(duration: str) -> tuple[str, int]:
        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
        if not match:
            return "00:00", 0

        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        seconds = int(match.group(3)) if match.group(3) else 0

        # tuple 형태로 00:00:00(영상 길이),0(영상 총 sec)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}", hours * 3600 + minutes * 60 + seconds

    @staticmethod
    async def format_published_at(published_at: str) -> str:
        return published_at.replace("T", " ").replace("Z", "")

    # 쿼리 인자로 유튜브 검색
    @classmethod
    async def search_youtube(cls, query: str = None, max_results: int = 1) -> list[str]:
        if not query:
            raise RequestValidationError("query is required")
        try:
            response = cls.youtube.search().list(
                q=query,
                part="id",
                maxResults=max_results,
                type="video"
            ).execute()
            return [item["id"]["videoId"] for item in response.get("items", [])]
        except Exception:
            raise Exception("YouTube API token limit exceeded")

    # 유튜브 자막 추출
    @classmethod
    async def get_video_subtitles(cls, video_details: VideoInfoDTO) -> str:
        video_id = video_details.id

        try:
            transcript_list = cls.ytt_api.list(video_id)
            try:
                transcript = transcript_list.find_manually_created_transcript(['ko'])  # 이미 작성된 자막 있는지 확인
            except NoTranscriptFound:
                transcript = transcript_list.find_generated_transcript(['ko'])  # 작성된 자막이 없을 시 자동 자막 확인

            snippets = transcript.fetch().snippets
            filtered_snippets = islice(snippets, cls.START_SENTENCE, cls.END_SENTENCE)  # 자막 구간 설정
            normalized = [re.sub(r'\s+', '', snippet.text) for snippet in filtered_snippets]  # 불필요한 문자열 제거
            return " ".join(normalized).strip()

        except Exception as e:
            print("Error: 예외 발생")
            print(f"예외 타입: {type(e)}")
            print(f"예외 메시지: {str(e)}")
            traceback.print_exc()
            return None

    # 유튜브 설명 추출
    @classmethod
    async def get_video_description(cls, video_details: VideoInfoDTO) -> str:
        if not video_details:
            raise RequestValidationError("video_details is required")

        description = video_details.description
        subtitles = await cls.get_video_subtitles(video_details)  # 자막 추출

        if not subtitles or subtitles.strip() == "":  # 자막이 없으면 설명란으로 대체
            return await OpenAIService.create_summary(description)  # 자막 요약
        else:
            return await OpenAIService.create_summary(subtitles)  # 설명란 요약

    # 유튜브 상세 정보 추출
    @classmethod
    async def get_video_details(cls, video_ids: list[str]) -> list[VideoInfoDTO]:
        if not video_ids:
            raise RequestValidationError("video_ids is required")

        response = cls.youtube.videos().list(
            part="snippet,contentDetails",
            id=",".join(video_ids)
        ).execute()

        try:
            video_info_list = []
            for item in response.get("items", []):
                snippet = item.get("snippet", {})
                content = item.get("contentDetails", {})
                duration, sec = await cls.format_duration(content.get("duration", "PT0M0S"))

                if cls.is_short_video(sec):  # 짧은 영상 pass
                    continue

                video_info = VideoInfoDTO(  # DTO 작성
                    id=item.get("id", ""),
                    title=snippet.get("title", "제목 없음"),
                    duration=duration,
                    url=f"https://www.youtube.com/watch?v={item.get('id', '')}",
                    channel=str(snippet.get("channelTitle", "")),
                    published_at=await cls.format_published_at(snippet.get("publishedAt", "")),
                    thumbnail=snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                )
                video_info_list.append(video_info)

            return video_info_list
        except Exception:
            raise Exception("YouTube API token limit exceeded")

    # 검색된 영상 id 추출
    @classmethod
    async def get_youtube_ids(cls, keyword_list: list[str], max_results: int = 5) -> list[str]:
        video_id_list = []
        for keyword in keyword_list:
            video_ids = await cls.search_youtube(query=keyword, max_results=max_results)
            video_id_list.extend(video_ids)
        return list(set(video_id_list))

    # 키워드 리스트로 영상 검색
    @classmethod
    async def search_videos_by_keyword_list(cls, keyword_list: list[str], max_results: int = 5) -> list[VideoInfoDTO]:
        video_id_list = await cls.get_youtube_ids(keyword_list, max_results)
        return await cls.get_video_details(video_id_list)

    # 쇼츠 영상인지 확인
    @classmethod
    def is_short_video(cls, sec: int) -> bool:
        try:
            return sec < cls.MIN_VIDEO_LENGTH
        except Exception:
            return True
