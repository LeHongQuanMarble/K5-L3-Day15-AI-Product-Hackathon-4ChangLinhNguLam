"""Phục vụ HTML game để giáo viên chơi thử trong iframe (N5). (T19)"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/preview", tags=["preview"])

PREVIEW_CSP = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
    "img-src data: blob:; font-src data:; media-src data: blob:"
)


@router.get("/{session_id}/v{number}", response_class=HTMLResponse)
async def preview_game(session_id: str, number: int, request: Request) -> HTMLResponse:
    """Trả index.html của phiên bản <number> kèm header Content-Security-Policy=PREVIEW_CSP. 404 nếu không có."""
    raise NotImplementedError
