"""Các bước chạy nền của chatbot (ARCHITECTURE §5). (T18)
Mỗi hàm tự lấy lock phiên khi ghi session và phát progress trước mỗi node."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.models import Session

if TYPE_CHECKING:
    from .engine import ChatEngine


async def run_build_questions(engine: ChatEngine, session_id: str, feedback: str = "") -> None:
    """N1 (nếu nguồn document) -> N1b. Nguồn user: hiện preview, sang READY_TO_DESIGN và chạy luôn
    run_design_cycle. Nguồn document/topic: hiện preview + nút duyệt -> AWAIT_QUESTION_APPROVAL.
    BankFileError -> báo lỗi, quay lại AWAIT_SOURCE_INPUT."""
    raise NotImplementedError


async def run_design_cycle(engine: ChatEngine, session_id: str, revision: str | None = None) -> None:
    """N2 -> (question_edit? -> n1b.edit) -> N3 -> N4 -> while fail and fix_attempts < MAX: FIX -> N4
    -> N5 review message -> AWAIT_REVIEW."""
    raise NotImplementedError


async def run_export(engine: ChatEngine, session_id: str) -> None:
    """N6 export -> notify_main -> message exported (+ link zip) -> DONE."""
    raise NotImplementedError


async def emit_progress(engine: ChatEngine, session: Session, node: str, detail: str = "") -> None:
    """Ghi event vào session + publish {'type':'progress','node','text'}."""
    raise NotImplementedError
