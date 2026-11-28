"""N3. Sinh HTML có đồ hoạ (GPT-6 Sol) + nhúng bộ câu hỏi. (T12)"""

from __future__ import annotations

import json

from app.config import Settings
from app.core.llm import LLMClient, extract_html
from app.core.models import Session, Version
from app.core.prompts import load_prompt
from app.core.store import SessionStore
from app.domain.contract import CONTRACT_TEXT, inject_bank


async def generate(llm: LLMClient, settings: Settings, store: SessionStore, session: Session) -> Version:
    """Prompt 'codegen' -> extract_html -> inject_bank(bộ câu hỏi thật)
    -> ghi sessions/<id>/v<n>/index.html -> thêm Version vào session (chưa save)."""
    system = load_prompt("codegen", CONTRACT=CONTRACT_TEXT)
    raw = await llm.complete(system=system, user=build_codegen_prompt(session), model=settings.codegen_model)
    html = inject_bank(extract_html(raw), session.question_bank)
    number = max((v.number for v in session.versions), default=0) + 1
    path = store.version_dir(session.id, number) / "index.html"
    path.write_text(html, encoding="utf-8")
    version = Version(number=number, html_path=str(path), design=dict(session.design))
    session.versions.append(version)
    return version


def build_codegen_prompt(session: Session) -> str:
    """Design JSON + 2 câu mẫu (cấu trúc) + ngữ cảnh phiên + điều khiển giáo viên chọn."""
    samples = session.question_bank.get("questions", [])[:2]
    parts = [
        f"Chủ đề: {session.topic or session.request}",
        f"Môn: {session.subject or ''} - Lớp: {session.grade or ''}",
        "Thiết kế (JSON):\n" + json.dumps(session.design, ensure_ascii=False, indent=2),
        "2 câu mẫu (chỉ để biết cấu trúc, bộ câu hỏi thật sẽ được nhúng sau):\n"
        + json.dumps(samples, ensure_ascii=False, indent=2),
    ]
    if session.controls:
        code = session.controls_code or "custom"
        parts.append(
            f"Điều khiển giáo viên yêu cầu (mã {code}, theo mục ĐIỀU KHIỂN của contract): {session.controls}"
        )
    if session.revisions:
        parts.append("Yêu cầu chỉnh sửa:\n" + "\n".join(f"- {r}" for r in session.revisions))
    return "\n\n".join(parts)
