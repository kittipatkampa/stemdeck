from __future__ import annotations

import hashlib
import os
import secrets

from fastapi import HTTPException, Request, Response

COOKIE_NAME = "karaoke_access"
COOKIE_AGE_SECONDS = 30 * 24 * 60 * 60


def access_code() -> str:
    return os.environ.get("ACCESS_CODE", "")


def _cookie_value(code: str) -> str:
    return hashlib.sha256(f"karaoke-access-v1:{code}".encode()).hexdigest()


def is_authorized(request: Request) -> bool:
    code = access_code()
    if not code:
        return True
    return secrets.compare_digest(
        request.cookies.get(COOKIE_NAME, ""), _cookie_value(code)
    )


def require_access(request: Request) -> None:
    if not is_authorized(request):
        raise HTTPException(status_code=401, detail="Access code required")


def unlock(code: str, response: Response) -> None:
    expected = access_code()
    if not expected or not secrets.compare_digest(code, expected):
        raise HTTPException(status_code=401, detail="Incorrect access code")
    response.set_cookie(
        COOKIE_NAME,
        _cookie_value(expected),
        max_age=COOKIE_AGE_SECONDS,
        path="/api",
        httponly=True,
        secure=bool(os.environ.get("K_SERVICE")),
        samesite="lax",
    )
