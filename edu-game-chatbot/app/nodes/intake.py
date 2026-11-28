"""INPUT: cổng 'game học tập?' + phân loại ý định người dùng. (T08)"""

from __future__ import annotations

from pydantic import BaseModel

from app.config import Settings
from app.core.llm import LLMClient, LLMFormatError, parse_json
from app.core.models import Button
from app.core.prompts import load_prompt


class IntakeResult(BaseModel):
    is_educational: bool
    reason: str = ""
    subject: str | None = None
    grade: str | None = None
    suggested_game_type: str | None = None


async def check_educational(llm: LLMClient, settings: Settings, request: str) -> IntakeResult:
    """Gọi prompt 'intake' (json_mode) -> IntakeResult. Sai định dạng -> LLMFormatError."""
    raw = await llm.complete(
        system=load_prompt("intake"), user=request, model=settings.intake_model, json_mode=True
    )
    data = parse_json(raw)
    flag = data.get("is_educational")
    if isinstance(flag, str) and flag.strip().casefold() in ("true", "false"):
        data["is_educational"] = flag.strip().casefold() == "true"
    for k in ("reason", "subject", "grade", "suggested_game_type"):
        if data.get(k) is not None and not isinstance(data[k], str):
            data[k] = str(data[k])
    if data.get("reason") is None:
        data.pop("reason", None)
    try:
        return IntakeResult.model_validate(data)
    except ValueError as e:
        raise LLMFormatError(f"JSON intake sai cấu trúc: {e}") from e


async def classify_intent(llm: LLMClient, settings: Settings, text: str, buttons: list[Button]) -> str | None:
    """Map câu chữ tự do -> button.id. Khớp trực tiếp label/id (không phân biệt hoa thường) thì
    trả ngay, KHÔNG gọi LLM; còn lại gọi prompt 'intent'. Không chắc -> None."""
    direct = match_button(text, buttons)
    if direct is not None:
        return direct
    if not buttons:
        return None
    listing = "\n".join(f"- {b.id}: {b.label}" for b in buttons)
    raw = await llm.complete(
        system=load_prompt("intent", BUTTONS=listing),
        user=text,
        model=settings.intake_model,
        json_mode=True,
    )
    data = parse_json(raw)
    bid = data.get("button_id")
    if isinstance(bid, str) and bid in {b.id for b in buttons}:
        return bid
    return None


def match_button(text: str, buttons: list[Button]) -> str | None:
    """So khớp trực tiếp text với id/label (strip, casefold)."""
    t = text.strip().casefold()
    if not t:
        return None
    for b in buttons:
        if t in (b.id.strip().casefold(), b.label.strip().casefold()):
            return b.id
    return None
