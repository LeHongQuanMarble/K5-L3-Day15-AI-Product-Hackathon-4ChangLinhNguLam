"""N3. Sinh HTML có đồ hoạ (GPT-6 Sol) + nhúng bộ câu hỏi. (T12)"""

from __future__ import annotations

from app.config import Settings
from app.core.llm import LLMClient
from app.core.models import Session, Version
from app.core.store import SessionStore


async def generate(llm: LLMClient, settings: Settings, store: SessionStore, session: Session) -> Version:
    """Prompt 'codegen' -> extract_html -> inject_bank(bộ câu hỏi thật)
    -> ghi sessions/<id>/v<n>/index.html -> thêm Version vào session (chưa save)."""
    raise NotImplementedError


def build_codegen_prompt(session: Session) -> str:
    """Design JSON + 2 câu mẫu (cấu trúc) + ngữ cảnh phiên."""
    raise NotImplementedError
