"""N4. Kiểm tra tự động: contract tĩnh + Playwright (GAME_CONTRACT §5). (T13)"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import Settings
from app.core.models import Session, Version
from app.domain.contract import static_check
from app.domain.questions import max_score

VIEWPORTS: tuple[tuple[int, int], ...] = ((1280, 800), (375, 740))


@dataclass
class TestReport:
    __test__ = False  # để pytest không coi là test class
    passed: bool
    errors: list[str] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)


async def run_tests(session: Session, version: Version, settings: Settings) -> TestReport:
    """static_check; pass thì chạy browser_check trong asyncio.to_thread.
    Cập nhật version.test_passed / test_errors / screenshots (chưa save)."""
    html_path = Path(version.html_path)
    errors = static_check(await asyncio.to_thread(html_path.read_text, encoding="utf-8"))
    shots: list[str] = []
    if not errors:
        shots_dir = html_path.parent / "screenshots"
        errors, shots = await asyncio.to_thread(
            browser_check, html_path, session.question_bank, shots_dir, settings
        )
    report = TestReport(passed=not errors, errors=errors, screenshots=shots)
    version.test_passed = report.passed
    version.test_errors = list(report.errors)
    version.screenshots = list(report.screenshots)
    return report


def browser_check(
    html_path: Path, bank: dict, shots_dir: Path, settings: Settings
) -> tuple[list[str], list[str]]:
    """(SYNC) Mở Chromium, chạy check_viewport cho từng VIEWPORTS. Trả (errors, screenshots)."""
    from playwright.sync_api import sync_playwright

    shots_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    shots: list[str] = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=settings.headless)
            try:
                for width, height in VIEWPORTS:
                    errs, imgs = check_viewport(
                        browser, html_path, bank, shots_dir, width, height, settings.playwright_timeout_ms
                    )
                    errors += errs
                    shots += imgs
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Không chạy được trình duyệt kiểm thử: {_short(exc)}")
    return errors, shots


class _StepError(Exception):
    """Lỗi của một bước §5 (thông điệp tiếng Việt, chưa có tiền tố viewport)."""


def _short(exc: BaseException) -> str:
    msg = (getattr(exc, "message", None) or str(exc)).strip()
    return msg.splitlines()[0][:200] if msg else type(exc).__name__


def _expect(cond: bool, msg: str) -> None:
    if not cond:
        raise _StepError(msg)


def _tid(testid: str) -> str:
    return f'[data-testid="{testid}"]'


def check_viewport(
    browser: Any, html_path: Path, bank: dict, shots_dir: Path, width: int, height: int, timeout_ms: int
) -> tuple[list[str], list[str]]:
    """7 bước GAME_CONTRACT §5 trên 1 viewport. Lỗi có tiền tố '[<width>px]'."""
    prefix = f"[{width}px]"
    sink: list[str] = []
    errors: list[str] = []
    shots: list[str] = []
    questions = bank.get("questions", [])
    total, max_pts = len(questions), max_score(bank)
    page = browser.new_page(viewport={"width": width, "height": height})
    page.set_default_timeout(timeout_ms)
    step = "mở trang"
    try:
        attach_listeners(page, sink)
        # 1. mở file, chờ ready
        page.goto(html_path.resolve().as_uri())
        try:
            page.wait_for_function(
                "() => window.__GAME__ && window.__GAME__.ready === true", timeout=timeout_ms
            )
        except Exception as exc:  # noqa: BLE001
            raise _StepError("window.__GAME__.ready không thành true trong thời gian chờ") from exc
        # 2. id câu hỏi nhúng
        step = "kiểm tra bộ câu hỏi"
        ids = page.evaluate(
            """() => { const el = document.getElementById("question-bank");
            if (!el) return null;
            try { return (JSON.parse(el.textContent).questions || []).map(q => q.id); }
            catch (e) { return null; } }"""
        )
        _expect(ids is not None, "Không đọc được #question-bank")
        _expect(
            ids == [q.get("id") for q in questions],
            "id câu hỏi trong #question-bank không khớp bộ câu hỏi của phiên",
        )
        # 3. tràn ngang
        step = "kiểm tra bố cục"
        _expect(
            page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 2"),
            "Bố cục bị tràn ngang",
        )
        # 4. bắt đầu
        step = "bắt đầu game"
        page.click(_tid("start-button"))
        state = page.evaluate("() => window.__GAME__.getState()") or {}
        _expect(
            state.get("status") == "playing",
            f"Sau khi bấm start-button, status là {state.get('status')!r}, cần 'playing'",
        )
        _expect(page.is_visible(_tid("question")), "Phần tử question không hiển thị khi đang chơi")
        _expect(
            not page.is_visible(_tid("result-screen")), "result-screen đang hiển thị khi game mới bắt đầu"
        )
        _expect(
            state.get("totalQuestions") == total,
            f"totalQuestions là {state.get('totalQuestions')}, cần {total}",
        )
        _expect(state.get("maxScore") == max_pts, f"maxScore là {state.get('maxScore')}, cần {max_pts}")
        # 5. đúng hết
        step = "trả lời đúng hết"
        play_through(page, bank, True, timeout_ms)
        _wait_result_visible(page, timeout_ms)
        result = page.evaluate("() => window.__GAME__.getResult()") or {}
        _expect(
            result.get("score") == max_pts,
            f"Trả lời đúng hết nhưng getResult().score là {result.get('score')}, cần {max_pts}",
        )
        final = page.inner_text(_tid("final-score"))
        _expect(
            re.search(rf"(?<!\d){max_pts}(?!\d)", final) is not None,
            f"final-score ({final.strip()!r}) không chứa điểm tối đa {max_pts}",
        )
        shots.append(_shot(page, shots_dir / f"{width}_correct.png"))
        # 6. chơi lại, sai hết
        step = "chơi lại và trả lời sai hết"
        page.click(_tid("restart-button"))
        state = page.evaluate("() => window.__GAME__.getState()") or {}
        _expect(
            state.get("status") == "playing",
            f"Sau khi bấm restart-button, status là {state.get('status')!r}, cần 'playing'",
        )
        play_through(page, bank, False, timeout_ms)
        _wait_result_visible(page, timeout_ms)
        result = page.evaluate("() => window.__GAME__.getResult()") or {}
        _expect(result.get("score") == 0, f"Trả lời sai hết nhưng điểm là {result.get('score')}, cần 0")
        wrong = result.get("wrong")
        n_wrong = len(wrong) if isinstance(wrong, list) else None
        _expect(
            n_wrong == total,
            f"Trả lời sai hết nhưng getResult().wrong có {n_wrong} câu, cần {total}",
        )
        shots.append(_shot(page, shots_dir / f"{width}_wrong.png"))
    except _StepError as exc:
        errors.append(f"{prefix} {exc}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{prefix} Lỗi ở bước {step}: {_short(exc)}")
    finally:
        # 7. pageerror / console.error / dialog / request mạng
        errors += [f"{prefix} {msg}" for msg in dict.fromkeys(sink)]
        page.close()
    return errors, shots


def _wait_result_visible(page: Any, timeout_ms: int) -> None:
    try:
        page.wait_for_selector(_tid("result-screen"), state="visible", timeout=timeout_ms)
    except Exception as exc:  # noqa: BLE001
        raise _StepError("result-screen không hiển thị khi game kết thúc") from exc


def _shot(page: Any, path: Path) -> str:
    page.screenshot(path=str(path))
    return str(path)


def attach_listeners(page: Any, sink: list[str]) -> None:
    """Đăng ký pageerror / console.error / dialog(dismiss) / chặn mạng (chỉ cho file://). Gọi TRƯỚC goto."""

    def on_console(msg: Any) -> None:
        if msg.type == "error":
            sink.append(f"console.error: {msg.text[:200]}")

    def on_dialog(dialog: Any) -> None:
        sink.append(f"Game mở hộp thoại {dialog.type}, không được phép")
        dialog.dismiss()

    def on_route(route: Any) -> None:
        url = route.request.url
        if url.startswith("file:"):
            route.continue_()
        else:
            sink.append(f"Request mạng bị chặn: {url[:200]}")
            route.abort()

    page.on("pageerror", lambda err: sink.append(f"Lỗi JavaScript (pageerror): {_short(err)}"))
    page.on("console", on_console)
    page.on("dialog", on_dialog)
    page.route("**/*", on_route)


def play_through(page: Any, bank: dict, correct: bool, timeout_ms: int) -> None:
    """Trả lời lần lượt mọi câu qua window.__GAME__ (đúng hết hoặc sai hết), chờ status 'finished'."""
    questions = bank.get("questions", [])
    for i, q in enumerate(questions):
        try:
            page.wait_for_function(
                "i => { const s = window.__GAME__.getState();"
                " return s.status === 'playing' && s.questionIndex === i; }",
                arg=i,
                timeout=timeout_ms,
            )
        except Exception as exc:  # noqa: BLE001
            raise _StepError(f"Hết thời gian chờ chuyển tới câu {i + 1} (questionIndex={i})") from exc
        if correct:
            page.evaluate("() => window.__GAME__.answer(window.__GAME__.getCorrectAnswer())")
        else:
            page.evaluate("c => window.__GAME__.answer(c)", wrong_answer(q))
    try:
        page.wait_for_function("() => window.__GAME__.getState().status === 'finished'", timeout=timeout_ms)
    except Exception as exc:  # noqa: BLE001
        raise _StepError("Đã trả lời hết câu hỏi nhưng status không chuyển sang 'finished'") from exc


def wrong_answer(question: dict) -> Any:
    """Đáp án sai chắc chắn: mcq (answer+1)%n; true_false not answer; fill_blank chuỗi vô nghĩa."""
    qtype = question.get("type")
    if qtype == "mcq":
        return (question["answer"] + 1) % len(question["options"])
    if qtype == "true_false":
        return not question["answer"]
    return "@@sai@@#9x7"
