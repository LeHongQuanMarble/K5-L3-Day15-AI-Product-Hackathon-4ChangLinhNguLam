"""N2. Phân tích & thiết kế game (GPT-6 Sol), đọc/ghi Session Memory. (T11)"""

from __future__ import annotations

import json

from app.config import Settings
from app.core.llm import LLMClient, LLMFormatError, parse_json
from app.core.models import Session
from app.core.prompts import load_prompt
from app.domain.questions import max_score

REQUIRED_KEYS = ("title", "game_type", "mechanics", "visual_style", "scoring", "result_screen")
SAMPLE_QUESTIONS = 3


async def design(llm: LLMClient, settings: Settings, session: Session, revision: str | None = None) -> dict:
    """Prompt 'design' (json_mode) -> dict; thiếu REQUIRED_KEYS -> LLMFormatError.
    Đẩy session.design cũ vào design_history, gán design mới (chưa save)."""
    raw = await llm.complete(
        system=load_prompt("design"),
        user=build_design_prompt(session, revision),
        model=settings.design_model,
        json_mode=True,
    )
    result = parse_json(raw)
    missing = [k for k in REQUIRED_KEYS if k not in result]
    if missing:
        raise LLMFormatError(f"Thiết kế thiếu trường bắt buộc: {', '.join(missing)}")
    if session.design:
        session.design_history.append(session.design)
    session.design = result
    return result


def build_design_prompt(session: Session, revision: str | None) -> str:
    """Ngữ cảnh phiên + thống kê bộ câu hỏi (số câu, loại, maxScore, 3 câu mẫu) + design hiện tại + revision (ưu tiên).
    KHÔNG đưa toàn bộ bộ câu hỏi."""
    dump = lambda o: json.dumps(o, ensure_ascii=False)  # noqa: E731
    parts = [
        "## Ngữ cảnh phiên",
        f"Yêu cầu: {session.request}",
        f"Chủ đề: {session.topic}",
        f"Môn: {session.subject or ''}",
        f"Lớp: {session.grade or ''}",
    ]
    if session.revisions:
        parts.append("Các lần chỉnh sửa trước:")
        parts += [f"- {r}" for r in session.revisions]
    parts += ["", "## Thống kê bộ câu hỏi", dump(bank_stats(session.question_bank))]
    if session.design:
        parts += ["", "## Thiết kế hiện tại", dump(session.design)]
    if revision:
        parts += ["", "## YÊU CẦU CHỈNH SỬA (ƯU TIÊN CAO NHẤT)", revision]
    return "\n".join(parts)


def bank_stats(bank: dict) -> dict:
    """{count, types, max_score, samples}"""
    qs = bank.get("questions", [])
    types: dict[str, int] = {}
    for q in qs:
        types[q.get("type", "")] = types.get(q.get("type", ""), 0) + 1
    return {
        "count": len(qs),
        "types": types,
        "max_score": max_score(bank),
        "samples": qs[:SAMPLE_QUESTIONS],
    }
