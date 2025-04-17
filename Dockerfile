# Python 3.12 slim 이미지 기반
FROM python:3.12-slim

# 시스템 패키지 설치 (예: gcc, libffi 등 필요 시)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# uv 설치
RUN curl -Ls https://astral.sh/uv/install.sh | sh

# uv 명령어를 PATH에 추가
ENV PATH="/root/.local/bin:$PATH"

# pyproject.toml, uv.lock 복사 후 의존성 설치
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync --frozen

# 앱 소스 복사
COPY . .

# 포트 노출
EXPOSE 8000

# FastAPI 앱 실행 명령어
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]