"""ChatEngine: state machine hội thoại (SPEC §3). (T18)
Dispatch bằng bảng {State: handler}; handler xử lý input và gọi _transition/_reply."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

from app.config import Settings
from app.core.events import EventBus
from app.core.llm import LLMClient
from app.core.models import Message, Session, State, Version
from app.core.store import SessionStore
from app.nodes.n4_test import TestReport

Tester = Callable[[Session, Version, Settings], Awaitable[TestReport]]
Handler = Callable[[Session, str | None, str | None], Awaitable[None]]


class ChatEngine:
    def __init__(
        self,
        store: SessionStore,
        llm: LLMClient,
        bus: EventBus,
        settings: Settings,
        tester: Tester | None = None,
    ) -> None:
        """tester mặc định = n4_test.run_tests (test inject tester giả). Dựng self._handlers."""
        raise NotImplementedError

    # ---------- public ----------
    async def start_session(self) -> Session:
        """Tạo phiên mới + message GREETING, state AWAIT_REQUEST."""
        raise NotImplementedError

    async def handle(self, session_id: str, text: str | None = None, action: str | None = None) -> None:
        """Ghi message người dùng (nếu có text), lấy lock phiên, dispatch theo state.
        State bận -> BUSY; state kết thúc -> SESSION_ENDED; FAILED + action retry -> _on_retry."""
        raise NotImplementedError

    async def wait_idle(self, session_id: str) -> None:
        """Chờ mọi background task của phiên xong (phục vụ test)."""
        raise NotImplementedError

    # ---------- handlers theo state ----------
    async def _on_await_request(self, s: Session, text: str | None, action: str | None) -> None:
        """check_educational: không -> REJECTED; có -> lưu subject/grade, hỏi nguồn -> AWAIT_SOURCE."""
        raise NotImplementedError

    async def _on_await_source(self, s: Session, text: str | None, action: str | None) -> None:
        """Nhận nút nguồn (hoặc classify_intent) -> AWAIT_SOURCE_INPUT với câu hỏi phù hợp."""
        raise NotImplementedError

    async def _on_await_source_input(self, s: Session, text: str | None, action: str | None) -> None:
        """user/document: chờ action file_uploaded; topic: text là chủ đề (+ số câu nếu có).
        Đủ dữ liệu -> BUILDING_QUESTIONS + chạy pipeline.run_build_questions nền."""
        raise NotImplementedError

    async def _on_await_question_approval(self, s: Session, text: str | None, action: str | None) -> None:
        """qb_approve -> READY_TO_DESIGN + chạy pipeline.run_design_cycle; qb_regenerate -> hỏi góp ý / tạo lại."""
        raise NotImplementedError

    async def _on_await_review(self, s: Session, text: str | None, action: str | None) -> None:
        """approve (chỉ khi test pass) -> EXPORTING + run_export; revise -> AWAIT_REVISION_TEXT; cancel -> CANCELLED."""
        raise NotImplementedError

    async def _on_await_revision_text(self, s: Session, text: str | None, action: str | None) -> None:
        """Lưu revision; vượt MAX_REVISION_ROUNDS -> FAILED; còn lại -> PIPELINE_RUNNING + run_design_cycle(revision)."""
        raise NotImplementedError

    async def _on_retry(self, s: Session) -> None:
        """Từ FAILED: chạy lại bước đã lỗi gần nhất (ghi trong s.events)."""
        raise NotImplementedError

    # ---------- tiện ích ----------
    async def _transition(self, s: Session, new_state: State) -> None:
        """Đổi state, save, publish event {'type':'state'}."""
        raise NotImplementedError

    async def _reply(self, s: Session, message: Message) -> None:
        """Thêm message bot, save, publish event {'type':'message'}."""
        raise NotImplementedError

    def _run_background(self, session_id: str, coro: Coroutine[Any, Any, None]) -> asyncio.Task[None]:
        """create_task + giữ reference trong set (tránh GC) + bắt exception -> FAILED."""
        raise NotImplementedError
