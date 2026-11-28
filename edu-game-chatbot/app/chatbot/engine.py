"""ChatEngine: state machine hội thoại (SPEC §3). (T18)
Dispatch bằng bảng {State: handler}; handler xử lý input và gọi _transition/_reply."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable, Coroutine
from pathlib import Path
from typing import Any

from app.chatbot import pipeline, replies
from app.config import Settings
from app.core.events import EventBus
from app.core.llm import LLMClient
from app.core.models import BUSY_STATES, TERMINAL_STATES, Button, Message, Session, Source, State, Version
from app.core.store import SessionStore
from app.nodes import intake
from app.nodes.n1_read_docs import SUPPORTED_EXTS
from app.nodes.n4_test import TestReport, run_tests

Tester = Callable[[Session, Version, Settings], Awaitable[TestReport]]
Handler = Callable[[Session, str | None, str | None], Awaitable[None]]

_NUM_RE = re.compile(r"(\d+)\s*câu", re.IGNORECASE)
_MAX_NUM_QUESTIONS = 50
_STEP_STATES = {
    "run_build_questions": State.BUILDING_QUESTIONS,
    "run_design_cycle": State.PIPELINE_RUNNING,
    "run_export": State.EXPORTING,
}


def _bot(text: str, buttons: list[Button] | None = None) -> Message:
    return Message(role="bot", text=text, buttons=buttons or [])


def _last_event(s: Session, node: str) -> dict | None:
    return next((e for e in reversed(s.events) if e.get("node") == node), None)


class ChatEngine:
    def __init__(
        self,
        store: SessionStore,
        llm: LLMClient,
        bus: EventBus,
        settings: Settings,
        tester: Tester | None = None,
    ) -> None:
        """tester mặc định = n4_test.run_tests (test inject tester giả). Dựng self._handlers."""
        self.store = store
        self.llm = llm
        self.bus = bus
        self.settings = settings
        self.tester: Tester = tester or run_tests
        self._tasks: set[asyncio.Task[None]] = set()
        self._session_tasks: dict[str, set[asyncio.Task[None]]] = {}
        self._handlers: dict[State, Handler] = {
            State.AWAIT_REQUEST: self._on_await_request,
            State.AWAIT_SOURCE: self._on_await_source,
            State.AWAIT_SOURCE_INPUT: self._on_await_source_input,
            State.AWAIT_QUESTION_APPROVAL: self._on_await_question_approval,
            State.AWAIT_REVIEW: self._on_await_review,
            State.AWAIT_REVISION_TEXT: self._on_await_revision_text,
        }

    # ---------- public ----------
    async def start_session(self) -> Session:
        """Tạo phiên mới + message GREETING, state AWAIT_REQUEST."""
        s = self.store.create()
        async with self.store.lock(s.id):
            s.state = State.AWAIT_REQUEST
            await self._reply(s, _bot(replies.GREETING))
        return s

    async def handle(self, session_id: str, text: str | None = None, action: str | None = None) -> None:
        """Ghi message người dùng (nếu có text), lấy lock phiên, dispatch theo state.
        State bận -> BUSY; state kết thúc -> SESSION_ENDED; FAILED + action retry -> _on_retry."""
        async with self.store.lock(session_id):
            s = self.store.get(session_id)
            if text:
                self.store.add_message(s, Message(role="user", text=text))
                self.store.save(s)
            if s.state in BUSY_STATES:
                await self._reply(s, _bot(replies.BUSY))
            elif s.state in TERMINAL_STATES:
                await self._reply(s, _bot(replies.SESSION_ENDED))
            elif s.state == State.FAILED:
                await self._on_failed_input(s, text, action)
            else:
                await self._dispatch(s, s.state, text, action)

    async def wait_idle(self, session_id: str) -> None:
        """Chờ mọi background task của phiên xong (phục vụ test)."""
        while tasks := self._session_tasks.get(session_id):
            await asyncio.gather(*list(tasks), return_exceptions=True)

    # ---------- handlers theo state ----------
    async def _on_await_request(self, s: Session, text: str | None, action: str | None) -> None:
        """check_educational: không -> REJECTED; có -> lưu subject/grade, hỏi nguồn -> AWAIT_SOURCE."""
        if not text or not text.strip():
            await self._reply(s, _bot(replies.GREETING))
            return
        result = await intake.check_educational(self.llm, self.settings, text)
        s.request = text.strip()
        if not result.is_educational:
            await self._reply(s, _bot(replies.reject(result.reason)))
            await self._transition(s, State.REJECTED)
            return
        s.subject, s.grade = result.subject, result.grade
        s.num_questions = self.settings.default_num_questions
        await self._reply(s, _bot(replies.ASK_SOURCE, replies.source_buttons()))
        await self._transition(s, State.AWAIT_SOURCE)

    async def _on_await_source(self, s: Session, text: str | None, action: str | None) -> None:
        """Nhận nút nguồn (hoặc classify_intent) -> AWAIT_SOURCE_INPUT với câu hỏi phù hợp."""
        buttons = replies.source_buttons()
        choices = {
            replies.BTN_SOURCE_USER: (Source.USER, replies.ASK_UPLOAD_QUESTIONS),
            replies.BTN_SOURCE_DOCUMENT: (Source.DOCUMENT, replies.ASK_UPLOAD_DOCUMENTS),
            replies.BTN_SOURCE_TOPIC: (Source.TOPIC, replies.ASK_TOPIC),
        }
        bid = await self._resolve(text, action, buttons)
        if bid not in choices:
            await self._reply(s, _bot(replies.NOT_UNDERSTOOD, buttons))
            return
        s.source, ask = choices[bid]
        await self._reply(s, _bot(ask))
        await self._transition(s, State.AWAIT_SOURCE_INPUT)

    async def _on_await_source_input(self, s: Session, text: str | None, action: str | None) -> None:
        """user/document: chờ action file_uploaded; topic: text là chủ đề (+ số câu nếu có).
        Đủ dữ liệu -> BUILDING_QUESTIONS + chạy pipeline.run_build_questions nền."""
        if s.source == Source.TOPIC:
            topic, num = self._parse_topic(text or "")
            if not topic:
                await self._reply(s, _bot(replies.ASK_TOPIC))
                return
            s.topic = topic
            if num:
                s.num_questions = num
        else:
            ask = replies.ASK_UPLOAD_QUESTIONS if s.source == Source.USER else replies.ASK_UPLOAD_DOCUMENTS
            if action != replies.ACTION_FILE_UPLOADED or not self._uploads(s):
                await self._reply(s, _bot(ask))
                return
        await self._launch(s, "run_build_questions")

    async def _on_await_question_approval(self, s: Session, text: str | None, action: str | None) -> None:
        """qb_approve -> READY_TO_DESIGN + chạy pipeline.run_design_cycle; qb_regenerate -> hỏi góp ý / tạo lại."""
        buttons = replies.question_approval_buttons()
        bid = await self._resolve(text, action, buttons)
        if bid == replies.BTN_QB_APPROVE:
            await self._transition(s, State.READY_TO_DESIGN)
            self._run_background(s.id, pipeline.run_design_cycle(self, s.id))
        elif bid == replies.BTN_QB_REGENERATE:
            feedback = self._free_text(text, buttons)
            if feedback:
                s.question_feedback.append(feedback)
            await self._launch(s, "run_build_questions", feedback=feedback)
        else:
            await self._reply(s, _bot(replies.NOT_UNDERSTOOD, buttons))

    async def _on_await_review(self, s: Session, text: str | None, action: str | None) -> None:
        """approve (chỉ khi test pass) -> EXPORTING + run_export; revise -> AWAIT_REVISION_TEXT; cancel -> CANCELLED."""
        version = s.latest_version
        passed = bool(version and version.test_passed is True)
        buttons = replies.review_buttons(passed)
        bid = await self._resolve(text, action, buttons)
        if bid == replies.BTN_APPROVE and passed:
            await self._launch(s, "run_export")
        elif bid == replies.BTN_REVISE:
            revision = self._free_text(text, buttons)
            if revision:
                await self._on_await_revision_text(s, revision, None)
                return
            await self._reply(s, _bot(replies.ASK_REVISION_TEXT))
            await self._transition(s, State.AWAIT_REVISION_TEXT)
        elif bid == replies.BTN_CANCEL:
            await self._reply(s, _bot(replies.CANCELLED))
            await self._transition(s, State.CANCELLED)
        else:
            await self._reply(s, _bot(replies.NOT_UNDERSTOOD, buttons))

    async def _on_await_revision_text(self, s: Session, text: str | None, action: str | None) -> None:
        """Lưu revision; vượt MAX_REVISION_ROUNDS -> FAILED; còn lại -> PIPELINE_RUNNING + run_design_cycle(revision)."""
        if not text or not text.strip():
            await self._reply(s, _bot(replies.ASK_REVISION_TEXT))
            return
        limit = self.settings.max_revision_rounds
        if len(s.revisions) >= limit:
            msg = replies.too_many_revisions(limit)
            s.error = msg
            self.store.add_event(s, "error", msg)
            await self._reply(s, _bot(msg))
            await self._transition(s, State.FAILED)
            return
        revision = text.strip()
        s.revisions.append(revision)
        await self._launch(s, "run_design_cycle", revision=revision)

    async def _on_retry(self, s: Session) -> None:
        """Từ FAILED: chạy lại bước đã lỗi gần nhất (ghi trong s.events)."""
        err = _last_event(s, "error")
        step = (err or {}).get("step")
        if not step:
            await self._reply(s, _bot(replies.SESSION_ENDED))
            return
        s.error = None
        if step == "handle":
            prev = State(err["state"])
            await self._transition(s, prev)
            await self._dispatch(s, prev, err.get("text"), err.get("action"))
        else:
            await self._launch(s, step, **(err.get("kwargs") or {}))

    # ---------- tiện ích ----------
    async def _transition(self, s: Session, new_state: State) -> None:
        """Đổi state, save, publish event {'type':'state'}."""
        s.state = new_state
        self.store.save(s)
        await self.bus.publish(s.id, {"type": "state", "state": new_state.value})

    async def _reply(self, s: Session, message: Message) -> None:
        """Thêm message bot, save, publish event {'type':'message'}."""
        self.store.add_message(s, message)
        self.store.save(s)
        await self.bus.publish(s.id, {"type": "message", "message": message.model_dump(mode="json")})

    def _run_background(self, session_id: str, coro: Coroutine[Any, Any, None]) -> asyncio.Task[None]:
        """create_task + giữ reference trong set (tránh GC) + bắt exception -> FAILED."""
        task = asyncio.create_task(self._guard(session_id, coro))
        per_session = self._session_tasks.setdefault(session_id, set())
        self._tasks.add(task)
        per_session.add(task)

        def _done(t: asyncio.Task[None]) -> None:
            self._tasks.discard(t)
            per_session.discard(t)
            if not per_session and self._session_tasks.get(session_id) is per_session:
                self._session_tasks.pop(session_id, None)

        task.add_done_callback(_done)
        return task

    # ---------- private ----------
    async def _guard(self, session_id: str, coro: Coroutine[Any, Any, None]) -> None:
        try:
            await coro
        except Exception as exc:  # noqa: BLE001 - mọi lỗi nền -> FAILED
            async with self.store.lock(session_id):
                s = self.store.get(session_id)
                step = _last_event(s, "step") or {}
                await self._fail(s, exc, step=step.get("text"), kwargs=step.get("kwargs") or {})

    async def _fail(self, s: Session, exc: BaseException, **info: Any) -> None:
        """Ghi lỗi (đã giữ lock), gửi message kèm nút retry, state FAILED."""
        error = str(exc) or type(exc).__name__
        s.error = error
        self.store.add_event(s, "error", error, **info)
        await self._reply(s, _bot(replies.failed(error), [replies.retry_button()]))
        await self._transition(s, State.FAILED)

    async def _dispatch(self, s: Session, state: State, text: str | None, action: str | None) -> None:
        handler = self._handlers.get(state)
        if handler is None:
            await self._reply(s, _bot(replies.NOT_UNDERSTOOD))
            return
        try:
            await handler(s, text, action)
        except Exception as exc:  # noqa: BLE001
            await self._fail(s, exc, step="handle", state=state.value, text=text, action=action)

    async def _on_failed_input(self, s: Session, text: str | None, action: str | None) -> None:
        retry = replies.retry_button()
        if action is None and text:
            action = intake.match_button(text, [retry])
        err = _last_event(s, "error") or {}
        if not err.get("step"):
            await self._reply(s, _bot(replies.SESSION_ENDED))
        elif action == replies.BTN_RETRY:
            await self._on_retry(s)
        else:
            await self._reply(s, _bot(replies.NOT_UNDERSTOOD, [retry]))

    async def _launch(self, s: Session, step: str, **kwargs: Any) -> None:
        """Chuyển sang state bận của bước rồi chạy pipeline.<step> nền."""
        await self._transition(s, _STEP_STATES[step])
        fn = getattr(pipeline, step)
        self._run_background(s.id, fn(self, s.id, **kwargs))

    async def _resolve(self, text: str | None, action: str | None, buttons: list[Button]) -> str | None:
        ids = {b.id for b in buttons}
        if action:
            return action if action in ids else None
        if text and text.strip():
            return await intake.classify_intent(self.llm, self.settings, text, buttons)
        return None

    @staticmethod
    def _free_text(text: str | None, buttons: list[Button]) -> str:
        """Phần chữ tự do đi kèm lựa chọn (rỗng nếu chỉ là nhãn nút)."""
        if not text or not text.strip() or intake.match_button(text, buttons):
            return ""
        return text.strip()

    def _parse_topic(self, text: str) -> tuple[str, int | None]:
        m = _NUM_RE.search(text)
        num = None
        if m:
            num = max(1, min(int(m.group(1)), _MAX_NUM_QUESTIONS))
            text = text[: m.start()] + text[m.end() :]
        return text.strip(" \t\n,.;:-"), num

    def _uploads(self, s: Session) -> list[Path]:
        """File đã upload (mới nhất trước); nguồn document chỉ lấy đuôi đọc được."""
        folder = self.store.session_dir(s.id) / "uploads"
        if not folder.is_dir():
            return []
        files = [p for p in folder.iterdir() if p.is_file()]
        if s.source == Source.DOCUMENT:
            files = [p for p in files if p.suffix.lower() in SUPPORTED_EXTS]
        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
