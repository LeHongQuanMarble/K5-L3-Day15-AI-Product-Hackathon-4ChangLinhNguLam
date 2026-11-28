"""Gợi ý 3 ý tưởng game có chiều sâu tương tác (F02)."""

from __future__ import annotations

import json
import re

from app.config import Settings
from app.core.llm import LLMClient, LLMFormatError, parse_json
from app.core.models import Session
from app.core.prompts import load_prompt
from app.nodes.n2_design import bank_stats

IDEA_KEYS = (
    "title",
    "pitch",
    "core_loop",
    "question_integration",
    "interactions",
    "progression",
    "recommended_controls",
)
NUM_IDEAS = 3
CONTROL_CODES = ("mouse", "keyboard", "motion", "voice")


async def suggest_ideas(
    llm: LLMClient, settings: Settings, session: Session, avoid: list[str] | None = None
) -> list[dict]:
    """Prompt 'game_ideas' (json_mode) -> đúng 3 ý tưởng đủ IDEA_KEYS; sai định dạng -> LLMFormatError.
    avoid: các title đã gợi ý trước đó (không lặp lại)."""
    raw = await llm.complete(
        system=load_prompt("game_ideas"),
        user=build_ideas_prompt(session, avoid or []),
        model=settings.design_model,
        json_mode=True,
    )
    return validate_ideas(parse_json(raw))


def validate_ideas(data: dict) -> list[dict]:
    """Kiểm tra {"ideas":[...]} có >= 3 ý tưởng đủ khoá; chuẩn hoá interactions/recommended_controls."""
    ideas = data.get("ideas")
    if not isinstance(ideas, list) or len(ideas) < NUM_IDEAS:
        raise LLMFormatError(f"Gợi ý ý tưởng phải có {NUM_IDEAS} ý tưởng")
    result: list[dict] = []
    for i, idea in enumerate(ideas[:NUM_IDEAS], 1):
        if not isinstance(idea, dict):
            raise LLMFormatError(f"Ý tưởng {i} không phải object")
        missing = [k for k in IDEA_KEYS if idea.get(k) in (None, "", [])]
        if missing:
            raise LLMFormatError(f"Ý tưởng {i} thiếu trường: {', '.join(missing)}")
        item = dict(idea)
        item["title"] = str(item["title"]).strip()
        item["interactions"] = _as_list(item["interactions"])
        item["recommended_controls"] = [
            c for c in (x.lower() for x in _as_list(item["recommended_controls"])) if c in CONTROL_CODES
        ] or ["mouse"]
        result.append(item)
    return result


def build_ideas_prompt(session: Session, avoid: list[str]) -> str:
    """Yêu cầu gốc, môn, lớp, chủ đề, thống kê bộ câu hỏi (≤ 3 câu mẫu) + title cần tránh.
    KHÔNG đưa toàn bộ bộ câu hỏi."""
    parts = [
        "## Ngữ cảnh",
        f"Yêu cầu gốc: {session.request}",
        f"Môn: {session.subject or ''}",
        f"Lớp: {session.grade or ''}",
        f"Chủ đề: {session.topic}",
        "",
        "## Thống kê bộ câu hỏi (kèm tối đa 3 câu mẫu)",
        json.dumps(bank_stats(session.question_bank), ensure_ascii=False),
    ]
    if avoid:
        parts += ["", "## Ý tưởng ĐÃ gợi ý (KHÔNG lặp lại, hãy nghĩ hướng khác hẳn)"]
        parts += [f"- {t}" for t in avoid]
    return "\n".join(parts)


def _as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [p.strip() for p in re.split(r"[,;\n]", str(value)) if p.strip()]
