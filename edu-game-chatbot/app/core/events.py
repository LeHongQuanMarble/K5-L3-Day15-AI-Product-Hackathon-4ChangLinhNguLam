"""EventBus: đẩy sự kiện tiến độ/message/state tới SSE theo session_id. (T18)

Định dạng event: {"type": "progress"|"message"|"state", ...} (ARCHITECTURE §4)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator


class EventBus:
    def __init__(self) -> None:
        """Khởi tạo danh sách subscriber (asyncio.Queue) theo session_id."""
        self._subs: dict[str, set[asyncio.Queue[dict]]] = {}

    async def publish(self, session_id: str, event: dict) -> None:
        """Gửi event tới mọi subscriber của phiên."""
        for q in list(self._subs.get(session_id, ())):
            q.put_nowait(event)

    async def subscribe(self, session_id: str) -> AsyncIterator[dict]:
        """Async generator trả event; tự huỷ đăng ký khi client ngắt."""
        q: asyncio.Queue[dict] = asyncio.Queue()
        self._subs.setdefault(session_id, set()).add(q)
        try:
            while True:
                yield await q.get()
        finally:
            subs = self._subs.get(session_id)
            if subs is not None:
                subs.discard(q)
                if not subs:
                    self._subs.pop(session_id, None)

    def subscriber_count(self, session_id: str) -> int:
        """Số subscriber đang nghe (phục vụ test)."""
        return len(self._subs.get(session_id, ()))
