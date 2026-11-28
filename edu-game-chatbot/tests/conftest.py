"""Fixture dùng chung + FakeLLM. Test KHÔNG BAO GIỜ gọi LLM thật. (T06)"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

Reply = str | Callable[[str, str], str]  # chuỗi cố định hoặc hàm (system, user) -> str


class FakeLLM:
    """LLM giả: chọn câu trả lời theo tên prompt (dòng đầu '# prompt: <name>' của system)."""

    def __init__(self, script: dict[str, list[Reply]] | None = None) -> None:
        """script: {tên_prompt: [reply lần 1, reply lần 2, ...]}. Ghi mọi lời gọi vào self.calls."""
        raise NotImplementedError

    def add(self, prompt_name: str, *replies: Reply) -> FakeLLM:
        """Nối thêm reply cho prompt; trả self để viết chuỗi."""
        raise NotImplementedError

    async def complete(self, *, system: str, user: str, model: str, json_mode: bool = False) -> str:
        """Lấy reply kế tiếp của prompt tương ứng; hết kịch bản -> AssertionError ghi rõ tên prompt."""
        raise NotImplementedError

    def calls_for(self, prompt_name: str) -> list[dict]:
        """Các lời gọi {system, user, model, json_mode} của 1 prompt."""
        raise NotImplementedError


@pytest.fixture
def settings(tmp_path: Path):
    """Settings trỏ sessions/output/main_inbox vào tmp_path, headless, timeout ngắn."""
    raise NotImplementedError


@pytest.fixture
def store(settings):
    """SessionStore(settings.sessions_dir)."""
    raise NotImplementedError


@pytest.fixture
def bus():
    """EventBus mới."""
    raise NotImplementedError


@pytest.fixture
def fake_llm() -> FakeLLM:
    """FakeLLM rỗng; test tự add kịch bản."""
    raise NotImplementedError


@pytest.fixture
def sample_bank() -> dict:
    """Nạp fixtures/questions_valid.json."""
    raise NotImplementedError


@pytest.fixture
def reference_html() -> str:
    """Nội dung fixtures/reference_game.html (game mẫu đạt 100% contract)."""
    raise NotImplementedError


@pytest.fixture
def happy_llm(fake_llm: FakeLLM, sample_bank: dict, reference_html: str) -> FakeLLM:
    """Kịch bản trọn luồng thành công: intake ok -> question_gen -> design -> codegen(reference)."""
    raise NotImplementedError
