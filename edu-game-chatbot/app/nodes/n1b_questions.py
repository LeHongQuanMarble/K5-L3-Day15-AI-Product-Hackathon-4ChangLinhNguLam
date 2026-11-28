"""N1b. Bộ câu hỏi: nạp từ người dùng / AI tạo từ tài liệu / AI tạo theo chủ đề / sửa. (T10)"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

from app.config import Settings
from app.core.llm import LLMClient, LLMFormatError, parse_json
from app.core.models import Source
from app.core.prompts import load_prompt
from app.domain.questions import (
    QUESTION_SCHEMA_TEXT,
    BankFileError,
    load_bank_file,
    max_score,
    normalize_bank,
    validate_bank,
)

MAX_GEN_RETRIES = 2


class QuestionGenError(RuntimeError):
    """AI không tạo được bộ câu hỏi hợp lệ sau MAX_GEN_RETRIES lần sửa."""


def from_user_file(path: Path) -> dict:
    """load_bank_file + validate_bank; lỗi -> BankFileError (giữ nguyên nội dung giáo viên)."""
    bank = load_bank_file(Path(path))
    errors = validate_bank(bank)
    if errors:
        raise BankFileError(errors)
    return bank


def _check(bank: dict, n: int | None) -> list[str]:
    errors = validate_bank(bank)
    if not errors and n is not None and len(bank["questions"]) != n:
        errors.append(f"Cần đúng {n} câu hỏi (hiện có {len(bank['questions'])}).")
    return errors


async def _ask(
    llm: LLMClient,
    settings: Settings,
    name: str,
    n: int | None,
    build: Callable[[list[str]], str],
) -> dict:
    system = load_prompt(name, SCHEMA=QUESTION_SCHEMA_TEXT)
    errors: list[str] = []
    for _ in range(MAX_GEN_RETRIES + 1):
        raw = await llm.complete(
            system=system, user=build(errors), model=settings.question_model, json_mode=True
        )
        try:
            bank = normalize_bank(parse_json(raw))
            errors = _check(bank, n)
        except LLMFormatError as exc:
            errors = [str(exc)]
            continue
        if not errors:
            return bank
    raise QuestionGenError("; ".join(errors))


async def generate(
    llm: LLMClient,
    settings: Settings,
    *,
    source: Source,
    request: str,
    num_questions: int,
    doc_text: str = "",
    topic: str = "",
    feedback: str = "",
) -> dict:
    """Prompt 'question_gen'. Bank sai / sai số câu -> gửi lại kèm lỗi, tối đa MAX_GEN_RETRIES; rồi QuestionGenError.
    source=DOCUMENT: chỉ dùng doc_text. source=TOPIC: dùng topic."""

    def build(errors: list[str]) -> str:
        return build_gen_prompt(
            source=source,
            request=request,
            num_questions=num_questions,
            doc_text=doc_text,
            topic=topic,
            feedback=feedback,
            previous_errors=errors,
        )

    return await _ask(llm, settings, "question_gen", num_questions, build)


def build_gen_prompt(
    *,
    source: Source,
    request: str,
    num_questions: int,
    doc_text: str,
    topic: str,
    feedback: str,
    previous_errors: list[str],
) -> str:
    """Tạo nội dung user message cho question_gen."""
    parts = [f"Yêu cầu: {request}", f"Số câu: {num_questions}"]
    if source == Source.DOCUMENT:
        parts.append(f"Tài liệu (chỉ dùng nội dung này):\n{doc_text}")
    else:
        parts.append(f"Chủ đề: {topic}")
    if feedback:
        parts.append(f"Phản hồi của giáo viên: {feedback}")
    if previous_errors:
        parts.append("Lần trước bộ câu hỏi bị lỗi, hãy sửa:\n" + "\n".join(f"- {e}" for e in previous_errors))
    return "\n\n".join(parts)


def _mentioned(instruction: str, bank: dict) -> set[str]:
    out: set[str] = set()
    for i, q in enumerate(bank["questions"], 1):
        qid = str(q.get("id"))
        by_id = re.search(rf"(?<!\w){re.escape(qid)}(?!\w)", instruction, re.I)
        by_pos = re.search(rf"(?i)\bcâu\s*(?:số\s*)?{i}\b", instruction)
        if by_id or by_pos:
            out.add(qid)
    return out


def _keep_unmentioned(old: dict, new: dict, mentioned: set[str]) -> dict:
    """Câu cũ không được nhắc tới: khôi phục nguyên văn (kể cả khi AI xoá/sửa)."""
    old_by = {q["id"]: q for q in old["questions"]}
    locked = {i for i in old_by if i not in mentioned}
    res: list[dict] = []
    seen: set[str] = set()
    for q in new["questions"]:
        qid = q.get("id")
        if qid in locked:
            res.append(old_by[qid])
            seen.add(qid)
        else:
            res.append(q)
    res.extend(q for i, q in old_by.items() if i in locked and i not in seen)
    return {**new, "questions": res}


async def edit(llm: LLMClient, settings: Settings, bank: dict, instruction: str, source: Source) -> dict:
    """Prompt 'question_edit' -> bank mới hợp lệ. source=USER: các câu không bị nhắc tới phải giữ nguyên (so theo id)."""
    mentioned = _mentioned(instruction, bank)

    def build(errors: list[str]) -> str:
        msg = f"Bộ câu hỏi hiện tại:\n{json.dumps(bank, ensure_ascii=False)}\n\nYêu cầu sửa: {instruction}"
        if errors:
            msg += "\n\nLần trước bị lỗi, hãy sửa:\n" + "\n".join(f"- {e}" for e in errors)
        return msg

    new = await _ask(llm, settings, "question_edit", None, build)
    if source == Source.USER:
        new = _keep_unmentioned(bank, new, mentioned)
        errors = validate_bank(new)
        if errors:
            raise QuestionGenError("; ".join(errors))
    return new


def preview_text(bank: dict, limit: int = 5) -> str:
    """Tóm tắt: '<title> — N câu, tổng X điểm' + limit câu đầu."""
    qs = bank.get("questions", [])
    lines = [f"{bank.get('title') or 'Bộ câu hỏi'} — {len(qs)} câu, tổng {max_score(bank)} điểm"]
    for i, q in enumerate(qs[:limit], 1):
        lines.append(f"{i}. {q.get('question', '')}")
    if len(qs) > limit:
        lines.append(f"... và {len(qs) - limit} câu nữa")
    return "\n".join(lines)
