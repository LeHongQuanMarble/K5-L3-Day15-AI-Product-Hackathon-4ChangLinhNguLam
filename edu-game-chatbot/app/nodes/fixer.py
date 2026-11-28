"""AI sửa lỗi (pipeline giới hạn tối đa MAX_FIX_ATTEMPTS lần). (T14)"""

from __future__ import annotations

from app.config import Settings
from app.core.llm import LLMClient
from app.core.models import Session, Version

MAX_ERRORS_IN_PROMPT = 20


async def fix(
    llm: LLMClient, settings: Settings, session: Session, version: Version, errors: list[str]
) -> None:
    """Prompt 'fix' -> extract_html -> inject_bank -> ghi đè file của CÙNG version; fix_attempts += 1."""
    raise NotImplementedError


def build_fix_prompt(html: str, errors: list[str]) -> str:
    """'LỖI CẦN SỬA' (≤ MAX_ERRORS_IN_PROMPT) + HTML hiện tại."""
    raise NotImplementedError
