"""N2. Phân tích & thiết kế game (GPT-6 Sol), đọc/ghi Session Memory. (T11)"""

from __future__ import annotations

from app.config import Settings
from app.core.llm import LLMClient
from app.core.models import Session

REQUIRED_KEYS = ("title", "game_type", "mechanics", "visual_style", "scoring", "result_screen")
SAMPLE_QUESTIONS = 3


async def design(llm: LLMClient, settings: Settings, session: Session, revision: str | None = None) -> dict:
    """Prompt 'design' (json_mode) -> dict; thiếu REQUIRED_KEYS -> LLMFormatError.
    Đẩy session.design cũ vào design_history, gán design mới (chưa save)."""
    raise NotImplementedError


def build_design_prompt(session: Session, revision: str | None) -> str:
    """Ngữ cảnh phiên + thống kê bộ câu hỏi (số câu, loại, maxScore, 3 câu mẫu) + design hiện tại + revision (ưu tiên).
    KHÔNG đưa toàn bộ bộ câu hỏi."""
    raise NotImplementedError


def bank_stats(bank: dict) -> dict:
    """{count, types, max_score, samples}"""
    raise NotImplementedError
