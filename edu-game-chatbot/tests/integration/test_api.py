"""API (T19)"""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from app.api.events import stream_events
from app.main import create_app
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


async def _tester(session, version, settings) -> TestReport:
    return TestReport(passed=True, errors=[])


@pytest.fixture
def app(settings, fake_llm, sample_bank, reference_html):
    fake_llm.add(
        "intake", json.dumps({"is_educational": True, "reason": "ôn tập", "subject": "Toán", "grade": "4"})
    )
    fake_llm.add("question_gen", json.dumps(sample_bank, ensure_ascii=False))
    fake_llm.add("design", json.dumps(DESIGN, ensure_ascii=False))
    fake_llm.add("codegen", f"```html\n{reference_html}\n```")
    a = create_app(settings=settings, llm=fake_llm)
    a.state.engine.tester = _tester
    return a


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def _new(client) -> str:
    r = await client.post("/api/sessions")
    assert r.status_code == 201
    return r.json()["id"]


async def _msg(client, app, sid, **body):
    r = await client.post(f"/api/sessions/{sid}/messages", json=body)
    assert r.status_code == 202
    await app.state.engine.wait_idle(sid)


async def _to_review(client, app, n: int) -> str:
    sid = await _new(client)
    await _msg(client, app, sid, text="Tạo game ôn tập phân số cho lớp 4")
    await _msg(client, app, sid, action="source_topic")
    await _msg(client, app, sid, text=f"Phân số lớp 4, {n} câu")
    await _msg(client, app, sid, action="qb_approve")
    return sid


async def test_create_and_get_session(client) -> None:
    r = await client.post("/api/sessions")
    data = r.json()
    assert r.status_code == 201 and data["state"] == "AWAIT_REQUEST" and data["messages"]
    g = await client.get(f"/api/sessions/{data['id']}")
    assert g.status_code == 200 and g.json()["id"] == data["id"]
    assert (await client.get("/api/sessions/nope")).status_code == 404


async def test_post_message_accepted(client, app) -> None:
    sid = await _new(client)
    r = await client.post(f"/api/sessions/{sid}/messages", json={"text": "Tạo game phân số lớp 4"})
    assert r.status_code == 202 and r.json() == {"accepted": True}
    await app.state.engine.wait_idle(sid)
    assert (await client.post("/api/sessions/nope/messages", json={"text": "x"})).status_code == 404


async def test_post_message_requires_text_or_action(client) -> None:
    sid = await _new(client)
    r = await client.post(f"/api/sessions/{sid}/messages", json={})
    assert r.status_code == 422


async def test_upload_rejects_bad_ext(client) -> None:
    sid = await _new(client)
    r = await client.post(f"/api/sessions/{sid}/files", files={"files": ("a.exe", b"MZ")})
    assert r.status_code == 400


async def test_upload_rejects_traversal(client) -> None:
    sid = await _new(client)
    r = await client.post(f"/api/sessions/{sid}/files", files={"files": ("../evil.txt", b"x")})
    assert r.status_code == 400


async def test_upload_ok_and_too_large(client, app, settings) -> None:
    sid = await _new(client)
    r = await client.post(f"/api/sessions/{sid}/files", files={"files": ("bai.txt", b"noi dung")})
    assert r.status_code == 202
    assert (settings.sessions_dir / sid / "uploads" / "bai.txt").read_bytes() == b"noi dung"
    await app.state.engine.wait_idle(sid)
    settings.max_upload_mb = 0
    r = await client.post(f"/api/sessions/{sid}/files", files={"files": ("b.txt", b"x")})
    assert r.status_code == 400


async def test_preview_has_csp(client, app, sample_bank) -> None:
    sid = await _to_review(client, app, len(sample_bank["questions"]))
    assert app.state.store.get(sid).state == "AWAIT_REVIEW", app.state.store.get(sid).error
    r = await client.get(f"/preview/{sid}/v1")
    assert r.status_code == 200
    assert "default-src 'none'" in r.headers["content-security-policy"]
    assert (await client.get(f"/preview/{sid}/v9")).status_code == 404


async def test_export_before_done_409(client, app, sample_bank) -> None:
    sid = await _to_review(client, app, len(sample_bank["questions"]))
    assert (await client.get(f"/api/sessions/{sid}/export.zip")).status_code == 409
    await _msg(client, app, sid, action="approve")
    r = await client.get(f"/api/sessions/{sid}/export.zip")
    assert r.status_code == 200 and r.content[:2] == b"PK"


async def test_sse_receives_progress(app, client) -> None:
    sid = await _new(client)
    assert (await client.get("/api/sessions/nope/events")).status_code == 404
    req = SimpleNamespace(app=app)
    resp = await stream_events(sid, req)  # type: ignore[arg-type]
    it = resp.body_iterator.__aiter__()
    task = asyncio.create_task(it.__anext__())
    await asyncio.sleep(0.05)
    await app.state.bus.publish(sid, {"type": "progress", "text": "đang làm"})
    ev = await asyncio.wait_for(task, 2)
    assert json.loads(ev["data"])["text"] == "đang làm"
    await it.aclose()
