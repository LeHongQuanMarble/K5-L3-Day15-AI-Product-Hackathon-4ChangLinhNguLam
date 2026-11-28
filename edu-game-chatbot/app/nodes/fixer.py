"""AI sửa lỗi (pipeline giới hạn tối đa MAX_FIX_ATTEMPTS lần). (T14)"""

from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.core.llm import LLMClient, extract_html
from app.core.models import Session, Version
from app.core.prompts import load_prompt
from app.domain.contract import CONTRACT_TEXT, inject_bank

MAX_ERRORS_IN_PROMPT = 20


async def fix(
    llm: LLMClient, settings: Settings, session: Session, version: Version, errors: list[str]
) -> None:
    """Prompt 'fix' -> extract_html -> inject_bank -> ghi đè file của CÙNG version; fix_attempts += 1."""
    html = _read(version.html_path)
    system = load_prompt("fix", CONTRACT=CONTRACT_TEXT)
    raw = await llm.complete(system=system, user=build_fix_prompt(html, errors), model=settings.fix_model)
    _write(version.html_path, inject_bank(extract_html(raw), session.question_bank))
    version.fix_attempts += 1


def build_fix_prompt(html: str, errors: list[str]) -> str:
    """'LỖI CẦN SỬA' (≤ MAX_ERRORS_IN_PROMPT) + HTML hiện tại."""
    lines = "\n".join(f"- {e}" for e in errors[:MAX_ERRORS_IN_PROMPT])
    return f"LỖI CẦN SỬA:\n{lines}\n\nHTML HIỆN TẠI:\n{html}"


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _write(path: str, html: str) -> None:
    Path(path).write_text(html, encoding="utf-8")
