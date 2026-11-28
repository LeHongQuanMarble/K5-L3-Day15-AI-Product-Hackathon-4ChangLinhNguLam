"""Các bước chạy nền của chatbot (ARCHITECTURE §5). (T18)
Mỗi hàm tự lấy lock phiên khi ghi session và phát progress trước mỗi node."""

from __future__ import annotations

import asyncio
import copy
from typing import TYPE_CHECKING, Any

from app.chatbot import replies
from app.core.models import DocumentInfo, Message, Session, Source, State, Version
from app.domain.questions import BankFileError, validate_bank
from app.nodes import fixer, n1b_questions, n2_design, n3_generate, n5_review, n6_export
from app.nodes.n1_read_docs import DocumentError, read_documents

if TYPE_CHECKING:
    from .engine import ChatEngine

# node -> khoá câu chữ trong replies.progress
_PROGRESS_KEYS = {
    "N1": "questions",
    "N1b": "questions",
    "N2": "design",
    "N3": "codegen",
    "N4": "test",
    "FIX": "test",
    "N6": "export",
}


async def run_build_questions(engine: ChatEngine, session_id: str, feedback: str = "") -> None:
    """N1 (nếu nguồn document) -> N1b. Nguồn user: hiện preview, sang READY_TO_DESIGN và chạy luôn
    run_design_cycle. Nguồn document/topic: hiện preview + nút duyệt -> AWAIT_QUESTION_APPROVAL.
    BankFileError -> báo lỗi, quay lại AWAIT_SOURCE_INPUT."""
    await _mark_step(engine, session_id, "run_build_questions", feedback=feedback)
    work = engine.store.get(session_id)
    try:
        if work.source == Source.USER:
            await emit_progress(engine, work, "N1b")
            files = engine._uploads(work)
            if not files:
                raise BankFileError([replies.ASK_UPLOAD_QUESTIONS])
            work.question_bank = await asyncio.to_thread(n1b_questions.from_user_file, files[0])
            preview = _bot(n1b_questions.preview_text(work.question_bank))
            await _commit(engine, work, "question_bank", messages=[preview], state=State.READY_TO_DESIGN)
            await run_design_cycle(engine, session_id)
            return
        doc_text = ""
        if work.source == Source.DOCUMENT:
            await emit_progress(engine, work, "N1")
            s = engine.settings
            result = await asyncio.to_thread(
                read_documents, engine._uploads(work), s.max_doc_chars, s.max_upload_mb * 1024 * 1024
            )
            doc_text = result.text
            work.documents = [DocumentInfo.model_validate(d) for d in result.docs]
        await emit_progress(engine, work, "N1b")
        work.question_bank = await n1b_questions.generate(
            engine.llm,
            engine.settings,
            source=work.source or Source.TOPIC,
            request=work.request,
            num_questions=work.num_questions,
            doc_text=doc_text,
            topic=work.topic,
            feedback=feedback,
        )
    except BankFileError as exc:
        await _commit(
            engine, work, messages=[_bot(replies.bank_invalid(exc.errors))], state=State.AWAIT_SOURCE_INPUT
        )
        return
    except DocumentError as exc:
        msg = _bot(f"{exc}\n{replies.ASK_UPLOAD_DOCUMENTS}")
        await _commit(engine, work, messages=[msg], state=State.AWAIT_SOURCE_INPUT)
        return
    preview = _bot(
        replies.bank_preview(n1b_questions.preview_text(work.question_bank)),
        replies.question_approval_buttons(),
    )
    await _commit(
        engine, work, "question_bank", "documents", messages=[preview], state=State.AWAIT_QUESTION_APPROVAL
    )


async def run_design_cycle(engine: ChatEngine, session_id: str, revision: str | None = None) -> None:
    """N2 -> (question_edit? -> n1b.edit) -> N3 -> N4 -> while fail and fix_attempts < MAX: FIX -> N4
    -> N5 review message -> AWAIT_REVIEW."""
    await _mark_step(engine, session_id, "run_design_cycle", revision=revision)
    work = engine.store.get(session_id)
    errors = validate_bank(work.question_bank)
    if errors:
        raise ValueError("; ".join(errors))
    if work.state != State.PIPELINE_RUNNING:
        await _commit(engine, work, state=State.PIPELINE_RUNNING)
    llm, settings = engine.llm, engine.settings

    await emit_progress(engine, work, "N2")
    design = await n2_design.design(llm, settings, work, revision)
    await _commit(engine, work, "design", "design_history")

    edit = design.get("question_edit")
    if isinstance(edit, str) and edit.strip():
        await emit_progress(engine, work, "N1b")
        work.question_bank = await n1b_questions.edit(
            llm, settings, work.question_bank, edit.strip(), work.source or Source.TOPIC
        )
        await _commit(engine, work, "question_bank")

    await emit_progress(engine, work, "N3")
    version = await n3_generate.generate(llm, settings, engine.store, work)
    await _commit(engine, work, "versions")

    await emit_progress(engine, work, "N4")
    await _test(engine, work, version)
    limit = settings.max_fix_attempts
    while not version.test_passed and version.fix_attempts < limit:
        await emit_progress(engine, work, "FIX", f"{version.fix_attempts + 1}/{limit}")
        await fixer.fix(llm, settings, work, version, list(version.test_errors))
        await _commit(engine, work, "versions")
        await emit_progress(engine, work, "N4", f"{version.fix_attempts}/{limit}")
        await _test(engine, work, version)

    review = n5_review.build_review_message(work, version)
    await _commit(engine, work, messages=[review], state=State.AWAIT_REVIEW)


async def run_export(engine: ChatEngine, session_id: str) -> None:
    """N6 export -> notify_main -> message exported (+ link zip) -> DONE."""
    await _mark_step(engine, session_id, "run_export")
    work = engine.store.get(session_id)
    # n6_export.export tự từ chối phiên bản chưa pass N4 (ValueError).
    version = work.latest_version or Version(number=0, html_path="")
    await emit_progress(engine, work, "N6")
    folder = await asyncio.to_thread(n6_export.export, work, version, engine.settings)
    await _commit(engine, work, "exported_to")
    warnings = await n6_export.notify_main(work, folder, engine.settings)
    title = n6_export.build_manifest(work, version)["title"]
    msg = Message(
        role="bot",
        text=replies.exported(title, version.number, warnings),
        attachments=[f"/api/sessions/{session_id}/export.zip"],
    )
    await _commit(engine, work, messages=[msg], state=State.DONE)


async def emit_progress(engine: ChatEngine, session: Session, node: str, detail: str = "") -> None:
    """Ghi event vào session + publish {'type':'progress','node','text'}."""
    text = replies.progress(_PROGRESS_KEYS.get(node, node), detail)
    async with engine.store.lock(session.id):
        live = engine.store.get(session.id)
        engine.store.add_event(live, node, text)
        engine.store.save(live)
    await engine.bus.publish(session.id, {"type": "progress", "node": node, "text": text})


# ---------- private ----------
def _bot(text: str, buttons: list | None = None) -> Message:
    return Message(role="bot", text=text, buttons=buttons or [])


async def _test(engine: ChatEngine, work: Session, version: Version) -> None:
    """Chạy tester (inject được), ghi kết quả vào version rồi commit."""
    report = await engine.tester(work, version, engine.settings)
    version.test_passed = bool(report.passed)
    version.test_errors = list(report.errors)
    version.screenshots = list(report.screenshots)
    await _commit(engine, work, "versions")


async def _mark_step(engine: ChatEngine, session_id: str, step: str, **kwargs: Any) -> None:
    """Ghi bước đang chạy để _on_retry chạy lại đúng bước khi lỗi."""
    async with engine.store.lock(session_id):
        live = engine.store.get(session_id)
        engine.store.add_event(live, "step", step, kwargs=kwargs)
        engine.store.save(live)


async def _commit(
    engine: ChatEngine,
    work: Session,
    *fields: str,
    messages: list[Message] | None = None,
    state: State | None = None,
) -> None:
    """Chép các trường từ bản làm việc sang phiên thật trong lock; thêm message, đổi state."""
    async with engine.store.lock(work.id):
        live = engine.store.get(work.id)
        for name in fields:
            setattr(live, name, copy.deepcopy(getattr(work, name)))
        engine.store.save(live)
        for m in messages or []:
            await engine._reply(live, m)
        if state is not None:
            await engine._transition(live, state)
        work.state = live.state
