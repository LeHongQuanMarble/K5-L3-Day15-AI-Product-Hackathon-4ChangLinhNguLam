"""INPUT: cổng 'game học tập?' + phân loại ý định người dùng. (T08)"""

from __future__ import annotations

from pydantic import BaseModel

from app.config import Settings
from app.core.llm import LLMClient
from app.core.models import Button


class IntakeResult(BaseModel):
    is_educational: bool
    reason: str = ""
    subject: str | None = None
    grade: str | None = None
    suggested_game_type: str | None = None


async def check_educational(llm: LLMClient, settings: Settings, request: str) -> IntakeResult:
    """Gọi prompt 'intake' (json_mode) -> IntakeResult. Sai định dạng -> LLMFormatError."""
    raise NotImplementedError


async def classify_intent(llm: LLMClient, settings: Settings, text: str, buttons: list[Button]) -> str | None:
    """Map câu chữ tự do -> button.id. Khớp trực tiếp label/id (không phân biệt hoa thường) thì
    trả ngay, KHÔNG gọi LLM; còn lại gọi prompt 'intent'. Không chắc -> None."""
    raise NotImplementedError


def match_button(text: str, buttons: list[Button]) -> str | None:
    """So khớp trực tiếp text với id/label (strip, casefold)."""
    raise NotImplementedError
