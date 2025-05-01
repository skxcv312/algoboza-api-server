FROM python:3.12-slim

# 필수 패키지 설치 및 uv 설치
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    build-essential \
    libffi-dev \
 && curl -Ls https://astral.sh/uv/install.sh | sh \
 && apt-get purge -y curl \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리
WORKDIR /app

# uv와 .venv 경로를 모두 PATH에 등록
ENV PATH="/root/.local/bin:/app/.venv/bin:$PATH"

# 의존성 파일 복사
COPY pyproject.toml .
COPY uv.lock .

# Docker 내부에서 .venv 생성 및 의존성 설치
RUN uv sync --frozen

# 소스 복사
COPY . .

# 포트 노출
EXPOSE 8000

# FastAPI 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]