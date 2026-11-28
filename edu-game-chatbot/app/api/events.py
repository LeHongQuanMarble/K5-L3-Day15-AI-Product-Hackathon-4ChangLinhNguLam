"""SSE stream tiến độ theo phiên. (T19)"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/api/sessions", tags=["events"])


@router.get("/{session_id}/events")
async def stream_events(session_id: str, request: Request) -> EventSourceResponse:
    """Subscribe EventBus, đẩy từng event dạng JSON; dừng khi client ngắt. 404 nếu không có phiên."""
    if not request.app.state.store.exists(session_id):
        raise HTTPException(404, "Không tìm thấy phiên")
    bus = request.app.state.bus

    async def gen():
        async for event in bus.subscribe(session_id):
            yield {"data": json.dumps(event, ensure_ascii=False, default=str)}

    return EventSourceResponse(gen(), ping=15)
