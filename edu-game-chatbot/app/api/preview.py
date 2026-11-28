"""Phục vụ HTML game để giáo viên chơi thử trong iframe (N5). (T19)"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/preview", tags=["preview"])

PREVIEW_CSP = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
    "img-src data: blob:; font-src data:; media-src data: blob: mediastream:"
)


@router.get("/{session_id}/v{number}", response_class=HTMLResponse)
async def preview_game(session_id: str, number: int, request: Request) -> HTMLResponse:
    """Trả index.html của phiên bản <number> kèm header Content-Security-Policy=PREVIEW_CSP. 404 nếu không có."""
    store = request.app.state.store
    if not store.exists(session_id):
        raise HTTPException(404, "Không tìm thấy phiên")
    session = store.get(session_id)
    version = next((v for v in session.versions if v.number == number), None)
    if version is None:
        raise HTTPException(404, "Không tìm thấy phiên bản")
    path = Path(version.html_path)
    try:
        html = await asyncio.to_thread(path.read_text, encoding="utf-8")
    except OSError:
        raise HTTPException(404, "Không tìm thấy phiên bản") from None
    return HTMLResponse(
        html,
        headers={"Content-Security-Policy": PREVIEW_CSP},
    )
