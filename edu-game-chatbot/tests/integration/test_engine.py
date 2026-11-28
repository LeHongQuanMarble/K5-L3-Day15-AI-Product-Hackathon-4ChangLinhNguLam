"""ChatEngine state machine (T18)"""

from __future__ import annotations

import asyncio
import contextlib
import copy
import json

import pytest

from app.chatbot import replies
from app.chatbot.engine import ChatEngine
from app.core.models import State
from app.nodes.n4_test import TestReport

DESIGN = {
    "title": "Phân số vui",
    "game_type": "quiz",
    "mechanics": "chọn đáp án",
    "visual_style": "tươi sáng",
    "scoring": "10 điểm/câu",
    "result_screen": "tổng điểm",
    "question_edit": None,
}


class FakeTester:
    """Tester giả: trả kết quả theo danh sách (hết danh sách -> lặp kết quả cuối)."""

    def __init__(self, results: list[bool] | None = None, gate: asyncio.Event | None = None) -> None:
        self.results = list(results or [True])
        self.calls = 0
        self.gate = gate

    async def __call__(self, session, version, settings) -> TestReport:
        self.calls += 1
        if self.gate is not None:
            await self.gate.wait()
        ok = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        return TestReport(passed=ok, errors=[] if ok else ["Thiếu màn hình kết quả"])


@pytest.fixture
def llm(fake_llm, sample_bank, reference_html):
    fake_llm.add(
        "intake", json.dumps({"is_educational": True, "reason": "ôn tập", "subject": "Toán", "grade": "4"})
    )
    fake_llm.add("question_gen", json.dumps(sample_bank, ensure_ascii=False))
    fake_llm.add("design", json.dumps(DESIGN, ensure_ascii=False))
    fake_llm.add("codegen", f"```html\n{reference_html}\n```")
    return fake_llm


def make_engine(store, llm, bus, settings, tester=None) -> ChatEngine:
    return ChatEngine(store, llm, bus, settings, tester=tester or FakeTester())


async def run(engine: ChatEngine, sid: str, text: str | None = None, action: str | None = None):
    await engine.handle(sid, text=text, action=action)
    await engine.wait_idle(sid)
    return engine.store.get(sid)


async def to_source(engine: ChatEngine, source_btn: str):
    s = await engine.start_session()
    assert s.messages[-1].text == replies.GREETING
    s = await run(engine, s.id, text="Tạo game ôn tập phân số cho lớp 4")
    assert s.state == State.AWAIT_SOURCE
    assert [b.id for b in s.messages[-1].buttons] == [b.id for b in replies.source_buttons()]
    s = await run(engine, s.id, action=source_btn)
    assert s.state == State.AWAIT_SOURCE_INPUT
    return s


async def topic_to_review(engine: ChatEngine, n: int):
    s = await to_source(engine, replies.BTN_SOURCE_TOPIC)
    s = await run(engine, s.id, text=f"Phân số lớp 4, {n} câu")
    assert s.state == State.AWAIT_QUESTION_APPROVAL, s.error
    assert s.topic == "Phân số lớp 4" and s.num_questions == n
    s = await run(engine, s.id, action=replies.BTN_QB_APPROVE)
    return s


def review_ids(s) -> list[str]:
    return [b.id for b in s.messages[-1].buttons]


async def test_flow_topic_to_review(store, llm, bus, settings, sample_bank) -> None:
    engine = make_engine(store, llm, bus, settings)
    s = await topic_to_review(engine, len(sample_bank["questions"]))
    assert s.state == State.AWAIT_REVIEW, s.error
    assert review_ids(s) == [replies.BTN_APPROVE, replies.BTN_REVISE, replies.BTN_CANCEL]
    assert s.messages[-1].preview_url == f"/preview/{s.id}/v1"
    assert s.versions[0].test_passed is True
    assert any(e["node"] == "N4" for e in s.events)
    # xuất
    s = await run(engine, s.id, action=replies.BTN_APPROVE)
    assert s.state == State.DONE, s.error
    assert s.exported_to
    assert (settings.main_inbox_dir / f"{s.id}.json").is_file()
    assert s.messages[-1].attachments == [f"/api/sessions/{s.id}/export.zip"]


async def test_flow_document_to_review(store, llm, bus, settings, sample_bank) -> None:
    settings.default_num_questions = len(sample_bank["questions"])
    engine = make_engine(store, llm, bus, settings)
    s = await to_source(engine, replies.BTN_SOURCE_DOCUMENT)
    # chưa có file -> nhắc tải lên, giữ state
    s = await run(engine, s.id, text="xin chào")
    assert s.state == State.AWAIT_SOURCE_INPUT
    assert s.messages[-1].text == replies.ASK_UPLOAD_DOCUMENTS
    store.safe_path(s.id, "bai.txt").write_text("Phân số là ... " * 20, encoding="utf-8")
    s = await run(engine, s.id, action=replies.ACTION_FILE_UPLOADED)
    assert s.state == State.AWAIT_QUESTION_APPROVAL, s.error
    assert s.documents and s.documents[0].name == "bai.txt"
    assert "Phân số là" in llm.calls_for("question_gen")[0]["user"]
    s = await run(engine, s.id, action=replies.BTN_QB_APPROVE)
    assert s.state == State.AWAIT_REVIEW, s.error


async def test_flow_user_file_to_review(store, fake_llm, llm, bus, settings, sample_bank) -> None:
    engine = make_engine(store, llm, bus, settings)
    s = await to_source(engine, replies.BTN_SOURCE_USER)
    store.safe_path(s.id, "qb.json").write_text(json.dumps(sample_bank, ensure_ascii=False), encoding="utf-8")
    s = await run(engine, s.id, action=replies.ACTION_FILE_UPLOADED)
    # nguồn user: không bắt duyệt, chạy thẳng tới review
    assert s.state == State.AWAIT_REVIEW, s.error
    assert s.question_bank == sample_bank
    assert not llm.calls_for("question_gen")
    assert review_ids(s)[0] == replies.BTN_APPROVE


async def test_happy_llm_fixture_reaches_review(store, happy_llm, bus, settings, sample_bank) -> None:
    engine = make_engine(store, happy_llm, bus, settings)
    s = await topic_to_review(engine, len(sample_bank["questions"]))
    assert s.state == State.AWAIT_REVIEW, s.error


async def test_llm_error_on_user_text_fails_cleanly(store, fake_llm, bus, settings) -> None:
    """Lỗi LLM khi xử lý tin nhắn (vd. mất kết nối) -> FAILED + nút retry, không văng TypeError."""
    from app.core.llm import LLMError

    def boom(system: str, user: str) -> str:
        raise LLMError("Connection error.")

    fake_llm.add("intake", boom)
    engine = make_engine(store, fake_llm, bus, settings)
    s = await engine.start_session()
    s = await run(engine, s.id, text="Tạo game ôn tập phân số lớp 4")
    assert s.state == State.FAILED and "Connection error" in s.error
    assert review_ids(s) == [replies.BTN_RETRY]
    assert s.events[-1]["input_text"] == "Tạo game ôn tập phân số lớp 4"


async def test_reject_non_educational(store, fake_llm, bus, settings) -> None:
    fake_llm.add("intake", json.dumps({"is_educational": False, "reason": "đây là game bắn súng giải trí"}))
    engine = make_engine(store, fake_llm, bus, settings)
    s = await engine.start_session()
    s = await run(engine, s.id, text="Làm game bắn súng")
    assert s.state == State.REJECTED
    assert s.messages[-1].text == replies.reject("đây là game bắn súng giải trí")
    assert [c["prompt"] for c in fake_llm.calls] == ["intake"]
    s = await run(engine, s.id, text="thử lại")
    assert s.state == State.REJECTED
    assert s.messages[-1].text == replies.SESSION_ENDED


async def test_invalid_user_file_stays_in_source_input(store, llm, bus, settings) -> None:
    engine = make_engine(store, llm, bus, settings)
    s = await to_source(engine, replies.BTN_SOURCE_USER)
    store.safe_path(s.id, "qb.json").write_text(json.dumps({"questions": []}), encoding="utf-8")
    s = await run(engine, s.id, action=replies.ACTION_FILE_UPLOADED)
    assert s.state == State.AWAIT_SOURCE_INPUT
    assert s.messages[-1].text.startswith("File bộ câu hỏi có lỗi")
    assert not s.question_bank
    assert not llm.calls_for("design")


async def test_regenerate_questions_with_feedback(store, llm, bus, settings, sample_bank) -> None:
    n = len(sample_bank["questions"])
    llm.add("question_gen", json.dumps(sample_bank, ensure_ascii=False))
    engine = make_engine(store, llm, bus, settings)
    s = await to_source(engine, replies.BTN_SOURCE_TOPIC)
    s = await run(engine, s.id, text=f"Phân số, {n} câu")
    assert s.state == State.AWAIT_QUESTION_APPROVAL
    s = await run(engine, s.id, text="Câu hỏi dễ hơn", action=replies.BTN_QB_REGENERATE)
    assert s.state == State.AWAIT_QUESTION_APPROVAL, s.error
    calls = llm.calls_for("question_gen")
    assert len(calls) == 2 and "Câu hỏi dễ hơn" in calls[1]["user"]
    assert s.question_feedback == ["Câu hỏi dễ hơn"]
    assert not llm.calls_for("design")
    # gõ chữ không rõ ý -> hướng dẫn, giữ state
    llm.add("intent", json.dumps({"button_id": None}))
    s = await run(engine, s.id, text="hmm")
    assert s.state == State.AWAIT_QUESTION_APPROVAL
    assert s.messages[-1].text == replies.NOT_UNDERSTOOD


async def test_fix_called_at_most_twice(store, llm, reference_html, bus, settings, sample_bank) -> None:
    llm.add("fix", *[f"```html\n{reference_html}\n```"] * 5)
    tester = FakeTester([False, False, False, True])
    engine = make_engine(store, llm, bus, settings, tester)
    s = await topic_to_review(engine, len(sample_bank["questions"]))
    assert s.state == State.AWAIT_REVIEW, s.error
    assert len(llm.calls_for("fix")) == settings.max_fix_attempts == 2
    assert tester.calls == 3
    assert s.versions[-1].fix_attempts == 2 and s.versions[-1].test_passed is False


async def test_failed_tests_no_approve_button(store, llm, reference_html, bus, settings, sample_bank) -> None:
    llm.add("fix", *[f"```html\n{reference_html}\n```"] * 2)
    engine = make_engine(store, llm, bus, settings, FakeTester([False]))
    s = await topic_to_review(engine, len(sample_bank["questions"]))
    assert review_ids(s) == [replies.BTN_REVISE, replies.BTN_CANCEL]
    # bấm approve vẫn bị từ chối, không xuất
    s = await run(engine, s.id, action=replies.BTN_APPROVE)
    assert s.state == State.AWAIT_REVIEW
    assert s.exported_to is None
    assert s.messages[-1].text == replies.NOT_UNDERSTOOD
    s = await run(engine, s.id, action=replies.BTN_CANCEL)
    assert s.state == State.CANCELLED


async def test_revision_goes_back_to_n2(store, llm, reference_html, bus, settings, sample_bank) -> None:
    llm.add("design", json.dumps({**DESIGN, "visual_style": "xanh dương"}, ensure_ascii=False))
    llm.add("codegen", f"```html\n{reference_html}\n```")
    engine = make_engine(store, llm, bus, settings)
    s = await topic_to_review(engine, len(sample_bank["questions"]))
    s = await run(engine, s.id, action=replies.BTN_REVISE)
    assert s.state == State.AWAIT_REVISION_TEXT
    s = await run(engine, s.id, text="Đổi màu nền sang xanh dương")
    assert s.state == State.AWAIT_REVIEW, s.error
    assert s.revisions == ["Đổi màu nền sang xanh dương"]
    assert "Đổi màu nền sang xanh dương" in llm.calls_for("design")[1]["user"]
    assert [v.number for v in s.versions] == [1, 2]
    assert s.design["visual_style"] == "xanh dương" and len(s.design_history) == 1
    assert s.messages[-1].preview_url == f"/preview/{s.id}/v2"


async def test_revision_with_question_edit(store, llm, reference_html, bus, settings, sample_bank) -> None:
    edited = copy.deepcopy(sample_bank)
    edited["questions"][0]["question"] = "Câu hỏi đã sửa về so sánh phân số?"
    llm.add(
        "design",
        json.dumps({**DESIGN, "question_edit": "Sửa câu 1 thành so sánh phân số"}, ensure_ascii=False),
    )
    llm.add("question_edit", json.dumps(edited, ensure_ascii=False))
    llm.add("codegen", f"```html\n{reference_html}\n```")
    engine = make_engine(store, llm, bus, settings)
    s = await topic_to_review(engine, len(sample_bank["questions"]))
    s = await run(engine, s.id, action=replies.BTN_REVISE)
    s = await run(engine, s.id, text="Sửa câu 1 thành so sánh phân số")
    assert s.state == State.AWAIT_REVIEW, s.error
    assert s.question_bank["questions"][0]["question"] == "Câu hỏi đã sửa về so sánh phân số?"
    html = (store.version_dir(s.id, 2) / "index.html").read_text(encoding="utf-8")
    assert "Câu hỏi đã sửa về so sánh phân số?" in html


async def test_too_many_revisions_failed(store, llm, reference_html, bus, settings, sample_bank) -> None:
    settings.max_revision_rounds = 1
    llm.add("design", json.dumps(DESIGN, ensure_ascii=False))
    llm.add("codegen", f"```html\n{reference_html}\n```")
    engine = make_engine(store, llm, bus, settings)
    s = await topic_to_review(engine, len(sample_bank["questions"]))
    s = await run(engine, s.id, action=replies.BTN_REVISE)
    s = await run(engine, s.id, text="Lần 1")
    assert s.state == State.AWAIT_REVIEW
    s = await run(engine, s.id, action=replies.BTN_REVISE)
    s = await run(engine, s.id, text="Lần 2")
    assert s.state == State.FAILED
    assert s.messages[-1].text == replies.too_many_revisions(1)
    assert len(llm.calls_for("design")) == 2


async def test_busy_message_while_running(store, llm, bus, settings, sample_bank) -> None:
    gate = asyncio.Event()
    engine = make_engine(store, llm, bus, settings, FakeTester([True], gate=gate))
    s = await to_source(engine, replies.BTN_SOURCE_TOPIC)
    s = await run(engine, s.id, text=f"Phân số, {len(sample_bank['questions'])} câu")
    await engine.handle(s.id, action=replies.BTN_QB_APPROVE)
    for _ in range(200):
        if engine.tester.calls:
            break
        await asyncio.sleep(0.01)
    await engine.handle(s.id, text="xong chưa?")
    s = store.get(s.id)
    assert s.state == State.PIPELINE_RUNNING
    assert s.messages[-1].text == replies.BUSY
    gate.set()
    await engine.wait_idle(s.id)
    assert store.get(s.id).state == State.AWAIT_REVIEW


async def test_exception_failed_then_retry(
    store, fake_llm, sample_bank, reference_html, bus, settings
) -> None:
    fake_llm.add("intake", json.dumps({"is_educational": True}))
    fake_llm.add("question_gen", json.dumps(sample_bank, ensure_ascii=False))
    engine = make_engine(store, fake_llm, bus, settings)
    s = await to_source(engine, replies.BTN_SOURCE_TOPIC)
    s = await run(engine, s.id, text=f"Phân số, {len(sample_bank['questions'])} câu")
    s = await run(engine, s.id, action=replies.BTN_QB_APPROVE)  # design chưa có kịch bản -> lỗi
    assert s.state == State.FAILED and s.error
    assert review_ids(s) == [replies.BTN_RETRY]
    fake_llm.add("design", json.dumps(DESIGN, ensure_ascii=False))
    fake_llm.add("codegen", f"```html\n{reference_html}\n```")
    s = await run(engine, s.id, action=replies.BTN_RETRY)
    assert s.state == State.AWAIT_REVIEW, s.error


async def test_event_bus_publish_subscribe(bus) -> None:
    got: list[dict] = []

    async def reader() -> None:
        async with contextlib.aclosing(bus.subscribe("s1")) as events:
            async for ev in events:
                got.append(ev)
                if len(got) == 2:
                    break

    task = asyncio.create_task(reader())
    for _ in range(100):
        if bus.subscriber_count("s1"):
            break
        await asyncio.sleep(0)
    await bus.publish("s1", {"type": "state", "state": "X"})
    await bus.publish("s2", {"type": "state", "state": "other"})
    await bus.publish("s1", {"type": "progress", "node": "N2", "text": "t"})
    await asyncio.wait_for(task, 1)
    assert [e["type"] for e in got] == ["state", "progress"]
    assert bus.subscriber_count("s1") == 0
