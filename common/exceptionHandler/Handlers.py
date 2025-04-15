import logging
import traceback

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)


def init_exception_handler(app):
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)


def error_response(status_code: int, exc: Exception):
    # traceback 정보 추출
    stack_summary = traceback.extract_tb(exc.__traceback__)

    # 마지막 스택(= 예외 발생 위치)
    last_trace = stack_summary[-1] if stack_summary else None

    # 메소드 이름, 파일명, 줄번호 등
    detail = {
        "line": last_trace.lineno if last_trace else None,
        "method": last_trace.name if last_trace else None
    }

    return JSONResponse(
        status_code=status_code,
        content={
            "error": str(exc),
            "detail": detail
        },
    )


# ValidationError 전역 처리 (요청 바디 유효성 오류 등)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    log.error(f"ValidationError: {exc.errors()}")
    return error_response(exc=exc, status_code=400)


# 일반 Exception 처리 (예외 누락 방지)
async def generic_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled exception:")
    return error_response(exc=exc, status_code=500)
