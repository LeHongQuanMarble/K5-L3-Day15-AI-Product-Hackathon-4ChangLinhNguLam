"""E2E giao diện chat (FakeLLM + Playwright) (T21)"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

import pytest
import uvicorn
from playwright.sync_api import Browser, Page, expect, sync_playwright

from app.main import create_app
from app.nodes.n4_test import TestReport
from tests.conftest import FakeLLM

pytestmark = pytest.mark.browser

TIMEOUT_MS = 15_000
expect.set_options(timeout=TIMEOUT_MS)
INTAKE = {"is_educational": True, "reason": "ôn tập", "subject": "Toán", "grade": "4"}


def _design(title: str) -> str:
    d = {
        "title": title,
        "game_type": "quiz",
        "mechanics": "chọn đáp án",
        "visual_style": "tươi sáng",
        "scoring": "10 điểm/câu",
        "result_screen": "tổng điểm",
        "question_edit": None,
    }
    return json.dumps(d, ensure_ascii=False)


async def _tester(session, version, settings) -> TestReport:
    """Tester giả: N4 thật đã có test riêng (tests/integration/test_n4.py)."""
    return TestReport(passed=True, errors=[])


@pytest.fixture
def scripted_llm(sample_bank: dict, reference_html: str) -> FakeLLM:
    """Kịch bản có 1 vòng chỉnh sửa: design/codegen trả 2 lần (v1, v2)."""
    llm = FakeLLM()
    llm.add("intake", json.dumps(INTAKE, ensure_ascii=False))
    llm.add("question_gen", json.dumps(sample_bank, ensure_ascii=False))
    llm.add("design", _design("Phân số vui"), _design("Phân số vui (bản 2)"))
    v2 = reference_html.replace("<title>Quiz mẫu</title>", "<title>Quiz mẫu v2</title>")
    llm.add("codegen", f"```html\n{reference_html}\n```", f"```html\n{v2}\n```")
    return llm


@pytest.fixture
def live_server(settings, scripted_llm) -> Iterator[str]:
    """Chạy uvicorn trong thread trên cổng ngẫu nhiên; trả base URL."""
    app = create_app(settings=settings, llm=scripted_llm)
    app.state.engine.tester = _tester
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning", loop="asyncio")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline or not thread.is_alive():
            raise RuntimeError("uvicorn không khởi động được")
        time.sleep(0.05)
    port = server.servers[0].sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    server.force_exit = True  # SSE giữ kết nối mở
    thread.join(timeout=10)


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


@pytest.fixture
def page(browser: Browser) -> Iterator[Page]:
    ctx = browser.new_context()
    pg = ctx.new_page()
    pg.set_default_timeout(TIMEOUT_MS)
    pg.on("dialog", lambda d: d.dismiss())
    yield pg
    ctx.close()


def _session_id(page: Page) -> str:
    return parse_qs(urlparse(page.url).query)["session"][0]


def _send(page: Page, text: str) -> None:
    expect(page.get_by_test_id("text-input")).to_be_enabled()
    page.get_by_test_id("text-input").fill(text)
    page.get_by_test_id("send-btn").click()


def _open_and_choose_topic(page: Page, base: str) -> None:
    page.goto(base + "/")
    expect(page.get_by_test_id("msg-bot").first).to_be_visible()
    page.wait_for_url("**?session=*")
    _send(page, "Tôi muốn game ôn phân số cho lớp 4")
    page.get_by_test_id("btn-source_topic").click()
    _send(page, "Phân số, 5 câu")
    page.get_by_test_id("btn-qb_approve").click()


def test_full_flow_topic_with_revision(live_server: str, page: Page, settings, scripted_llm) -> None:
    _open_and_choose_topic(page, live_server)
    sid = _session_id(page)

    frame = page.locator("#preview-frame")
    expect(page.get_by_test_id("preview")).to_be_visible()
    expect(frame).to_have_attribute("src", f"/preview/{sid}/v1")
    expect(page.frame_locator("#preview-frame").get_by_test_id("start-button")).to_be_visible()

    page.get_by_test_id("btn-revise").last.click()
    _send(page, "Đổi màu nền sang xanh lá")
    expect(frame).to_have_attribute("src", f"/preview/{sid}/v2")
    expect(page.frame_locator("#preview-frame").get_by_test_id("start-button")).to_be_visible()

    page.get_by_test_id("btn-approve").last.click()
    link = page.get_by_test_id("download-zip")
    expect(link).to_be_visible()
    expect(link).to_have_attribute("href", f"/api/sessions/{sid}/export.zip")
    resp = page.request.get(live_server + link.get_attribute("href"))
    assert resp.status == 200 and resp.body()[:2] == b"PK"

    assert (settings.main_inbox_dir / f"{sid}.json").is_file()
    assert len(scripted_llm.calls_for("design")) == 2
    assert len(scripted_llm.calls_for("codegen")) == 2
    assert "Đổi màu nền sang xanh lá" in scripted_llm.calls_for("design")[1]["user"]
    expect(page.get_by_test_id("text-input")).to_be_disabled()


def test_mobile_layout(browser: Browser, live_server: str) -> None:
    ctx = browser.new_context(viewport={"width": 375, "height": 667}, is_mobile=True, has_touch=True)
    try:
        pg = ctx.new_page()
        pg.set_default_timeout(TIMEOUT_MS)
        pg.goto(live_server + "/")
        expect(pg.get_by_test_id("msg-bot").first).to_be_visible()
        _send(pg, "Tôi muốn game ôn phân số cho lớp 4")
        expect(pg.get_by_test_id("btn-source_topic")).to_be_visible()

        no_hscroll = "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
        assert pg.evaluate(no_hscroll)
        for tid in ("text-input", "send-btn", "btn-source_topic"):
            box = pg.get_by_test_id(tid).bounding_box()
            assert box is not None
            assert box["x"] >= 0 and box["x"] + box["width"] <= 375, tid
        composer = pg.get_by_test_id("composer").bounding_box()
        assert composer is not None and composer["y"] + composer["height"] <= 667
    finally:
        ctx.close()


def test_resume_session_from_url(live_server: str, browser: Browser, page: Page) -> None:
    page.goto(live_server + "/")
    expect(page.get_by_test_id("msg-bot").first).to_be_visible()
    page.wait_for_url("**?session=*")
    sid = _session_id(page)
    _send(page, "Tôi muốn game ôn phân số cho lớp 4")
    expect(page.get_by_test_id("btn-source_topic")).to_be_visible()

    # Trình duyệt khác (không có localStorage) mở đúng URL phiên.
    ctx = browser.new_context()
    try:
        other = ctx.new_page()
        other.set_default_timeout(TIMEOUT_MS)
        other.goto(f"{live_server}/?session={sid}")
        expect(other.get_by_test_id("msg-user")).to_have_count(1)
        expect(other.get_by_test_id("msg-user")).to_contain_text("phân số cho lớp 4")
        expect(other.get_by_test_id("btn-source_topic")).to_be_visible()
        assert _session_id(other) == sid
        bots = other.get_by_test_id("msg-bot").count()
        other.get_by_test_id("btn-source_topic").click()
        expect(other.get_by_test_id("msg-bot")).to_have_count(bots + 1)
        expect(other.get_by_test_id("text-input")).to_be_enabled()
    finally:
        ctx.close()

    # Cùng trình duyệt, mở '/' không tham số -> nhớ phiên qua localStorage.
    page.goto(live_server + "/")
    page.wait_for_url(f"**?session={sid}")
    expect(page.get_by_test_id("msg-bot")).to_have_count(bots + 1)
    expect(page.get_by_test_id("msg-user")).to_have_count(1)
    expect(page.get_by_test_id("btn-source_topic")).to_be_visible()
