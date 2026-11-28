"""EventBus: đẩy sự kiện tiến độ/message/state tới SSE theo session_id. (T18)

Định dạng event: {"type": "progress"|"message"|"state", ...} (ARCHITECTURE §4)."""

from __future__ import annotations

from collections.abc import AsyncIterator


class EventBus:
    def __init__(self) -> None:
        """Khởi tạo danh sách subscriber (asyncio.Queue) theo session_id."""
        raise NotImplementedError

    async def publish(self, session_id: str, event: dict) -> None:
        """Gửi event tới mọi subscriber của phiên."""
        raise NotImplementedError

    async def subscribe(self, session_id: str) -> AsyncIterator[dict]:
        """Async generator trả event; tự huỷ đăng ký khi client ngắt."""
        raise NotImplementedError
        yield {}  # pragma: no cover

    def subscriber_count(self, session_id: str) -> int:
        """Số subscriber đang nghe (phục vụ test)."""
        raise NotImplementedError
