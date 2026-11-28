"""SSE stream tiến độ theo phiên. (T19)"""

from __future__ import annotations

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/api/sessions", tags=["events"])


@router.get("/{session_id}/events")
async def stream_events(session_id: str, request: Request) -> EventSourceResponse:
    """Subscribe EventBus, đẩy từng event dạng JSON; dừng khi client ngắt. 404 nếu không có phiên."""
    raise NotImplementedError
