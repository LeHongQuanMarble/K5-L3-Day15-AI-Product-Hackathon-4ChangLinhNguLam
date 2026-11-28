"""Fixture dùng chung + FakeLLM. Test KHÔNG BAO GIỜ gọi LLM thật. (T06)"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

Reply = str | Callable[[str, str], str]  # chuỗi cố định hoặc hàm (system, user) -> str


class FakeLLM:
    """LLM giả: chọn câu trả lời theo tên prompt (dòng đầu '# prompt: <name>' của system)."""

    def __init__(self, script: dict[str, list[Reply]] | None = None) -> None:
        """script: {tên_prompt: [reply lần 1, reply lần 2, ...]}. Ghi mọi lời gọi vào self.calls."""
        self.script: dict[str, list[Reply]] = {k: list(v) for k, v in (script or {}).items()}
        self.calls: list[dict] = []

    def add(self, prompt_name: str, *replies: Reply) -> FakeLLM:
        """Nối thêm reply cho prompt; trả self để viết chuỗi."""
        self.script.setdefault(prompt_name, []).extend(replies)
        return self

    async def complete(self, *, system: str, user: str, model: str, json_mode: bool = False) -> str:
        """Lấy reply kế tiếp của prompt tương ứng; hết kịch bản -> AssertionError ghi rõ tên prompt."""
        from app.core.prompts import prompt_name_of

        name = prompt_name_of(system)
        self.calls.append(
            {"prompt": name, "system": system, "user": user, "model": model, "json_mode": json_mode}
        )
        queue = self.script.get(name or "")
        if not queue:
            raise AssertionError(f"FakeLLM hết kịch bản cho prompt '{name}'")
        reply = queue.pop(0)
        return reply(system, user) if callable(reply) else reply

    def calls_for(self, prompt_name: str) -> list[dict]:
        """Các lời gọi {system, user, model, json_mode} của 1 prompt."""
        return [c for c in self.calls if c["prompt"] == prompt_name]


@pytest.fixture
def settings(tmp_path: Path):
    """Settings trỏ sessions/output/main_inbox vào tmp_path, headless, timeout ngắn."""
    from app.config import Settings

    s = Settings(
        _env_file=None,
        openai_api_key="test-key",
        sessions_dir=tmp_path / "sessions",
        output_dir=tmp_path / "output",
        main_inbox_dir=tmp_path / "main_inbox",
        headless=True,
        playwright_timeout_ms=5_000,
        llm_timeout_s=5,
    )
    s.ensure_dirs()  # lazy: chỉ lỗi khi fixture được dùng và T02 chưa xong
    return s


@pytest.fixture
def store(settings):
    """SessionStore(settings.sessions_dir)."""
    from app.core.store import SessionStore

    return SessionStore(settings.sessions_dir)


@pytest.fixture
def bus():
    """EventBus mới."""
    from app.core.events import EventBus

    return EventBus()


@pytest.fixture
def fake_llm() -> FakeLLM:
    """FakeLLM rỗng; test tự add kịch bản."""
    return FakeLLM()


@pytest.fixture
def sample_bank() -> dict:
    """Nạp fixtures/questions_valid.json."""
    return json.loads((FIXTURES / "questions_valid.json").read_text(encoding="utf-8"))


@pytest.fixture
def reference_html() -> str:
    """Nội dung fixtures/reference_game.html (game mẫu đạt 100% contract)."""
    return (FIXTURES / "reference_game.html").read_text(encoding="utf-8")


@pytest.fixture
def happy_llm(fake_llm: FakeLLM, sample_bank: dict, reference_html: str) -> FakeLLM:
    """Kịch bản trọn luồng thành công: intake ok -> question_gen -> design -> codegen(reference)."""
    intake = {"is_educational": True, "reason": "ôn tập", "subject": "Toán", "grade": "4"}
    fake_llm.add("intake", json.dumps(intake, ensure_ascii=False))
    fake_llm.add("question_gen", json.dumps(sample_bank, ensure_ascii=False))
    fake_llm.add(
        "design",
        json.dumps(
            {
                "title": sample_bank.get("title", "Game"),
                "game_type": "quiz",
                "mechanics": "chọn đáp án",
                "visual_style": "tươi sáng",
                "scoring": "10 điểm/câu",
                "result_screen": "tổng điểm",
            },
            ensure_ascii=False,
        ),
    )
    fake_llm.add("codegen", f"```html\n{reference_html}\n```")
    return fake_llm
