"""N4. Kiểm tra tự động: contract tĩnh + Playwright (GAME_CONTRACT §5). (T13)"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import Settings
from app.core.models import Session, Version

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
    raise NotImplementedError


def browser_check(
    html_path: Path, bank: dict, shots_dir: Path, settings: Settings
) -> tuple[list[str], list[str]]:
    """(SYNC) Mở Chromium, chạy check_viewport cho từng VIEWPORTS. Trả (errors, screenshots)."""
    raise NotImplementedError


def check_viewport(
    browser: Any, html_path: Path, bank: dict, shots_dir: Path, width: int, height: int, timeout_ms: int
) -> tuple[list[str], list[str]]:
    """7 bước GAME_CONTRACT §5 trên 1 viewport. Lỗi có tiền tố '[<width>px]'."""
    raise NotImplementedError


def attach_listeners(page: Any, sink: list[str]) -> None:
    """Đăng ký pageerror / console.error / dialog(dismiss) / chặn mạng (chỉ cho file://). Gọi TRƯỚC goto."""
    raise NotImplementedError


def play_through(page: Any, bank: dict, correct: bool, timeout_ms: int) -> None:
    """Trả lời lần lượt mọi câu qua window.__GAME__ (đúng hết hoặc sai hết), chờ status 'finished'."""
    raise NotImplementedError


def wrong_answer(question: dict) -> Any:
    """Đáp án sai chắc chắn: mcq (answer+1)%n; true_false not answer; fill_blank chuỗi vô nghĩa."""
    raise NotImplementedError
