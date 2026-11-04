"""HTTP Basic 인증 미들웨어. 브라우저가 로그인 창을 띄우고, fetch()도 자동으로 따라간다.

JOBHUNT_PASSWORD 설정 시 /healthz 를 제외한 모든 경로를 보호한다.
JOBHUNT_ENV=production 인데 비밀번호가 없으면 서버가 시작되지 않는다(실수로 공개되는 것 방지).
"""
from __future__ import annotations
import base64, hmac, os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse

PUBLIC_PATHS = {"/healthz"}


def check_startup() -> None:
    if os.environ.get("JOBHUNT_ENV") == "production" and not os.environ.get("JOBHUNT_PASSWORD"):
        raise RuntimeError("production 환경에서는 JOBHUNT_PASSWORD 설정이 필수입니다.")


def _valid(header: str | None, password: str, user: str) -> bool:
    if not header or not header.lower().startswith("basic "):
        return False
    try:
        u, _, p = base64.b64decode(header[6:]).decode("utf-8").partition(":")
    except Exception:
        return False
    # 둘 다 항상 비교해서 타이밍 차이를 줄인다
    ok_u = hmac.compare_digest(u.encode(), user.encode())
    ok_p = hmac.compare_digest(p.encode(), password.encode())
    return ok_u and ok_p


class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        password = os.environ.get("JOBHUNT_PASSWORD")
        if not password or request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        if _valid(request.headers.get("authorization"), password, os.environ.get("JOBHUNT_USER", "admin")):
            return await call_next(request)
        return PlainTextResponse("Unauthorized", status_code=401,
                                 headers={"WWW-Authenticate": 'Basic realm="Job Hunt"'})
