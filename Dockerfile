# Python 3.12 slim 이미지 기반
FROM python:3.12.9

# 시스템 패키지 설치 (예: gcc, libffi 등 필요 시)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
#RUN  pip install -r requirements.txt

# 앱 소스 복사
COPY . .

# 포트 노출
EXPOSE 8000

# FastAPI 앱 실행 명령어
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]