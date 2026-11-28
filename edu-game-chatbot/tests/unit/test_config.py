"""Config (T02)"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings, get_settings


@pytest.fixture(autouse=True)
def clean_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Đứng trong tmp_path (không đọc .env thật), xoá biến env cấu hình, reset cache."""
    monkeypatch.chdir(tmp_path)
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_defaults(tmp_path: Path) -> None:
    s = Settings(_env_file=None)
    assert s.openai_api_key is None
    assert s.openai_base_url is None
    assert s.design_model == "gpt-6-sol"
    assert s.codegen_model == "gpt-6-sol"
    assert s.fix_model == "gpt-6-sol"
    assert s.question_model == "gpt-6-sol"
    assert s.intake_model == "gpt-6-sol"
    assert s.llm_timeout_s == 120
    assert s.llm_max_retries == 2
    assert s.max_revision_rounds == 10
    assert s.default_num_questions == 10
    assert s.max_doc_chars == 60_000
    assert s.max_upload_mb == 10
    assert s.max_files_per_session == 5
    assert s.playwright_timeout_ms == 10_000
    assert s.headless is True
    assert s.sessions_dir == Path("sessions")
    assert s.output_dir == Path("output")
    assert s.main_inbox_dir == Path("main_inbox")
    assert s.main_webhook_url is None

    s = get_settings()
    assert s.sessions_dir == Path("sessions")
    assert (tmp_path / "sessions").is_dir()
    assert (tmp_path / "output").is_dir()
    assert (tmp_path / "main_inbox").is_dir()


def test_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MAX_FIX_ATTEMPTS", "5")
    monkeypatch.setenv("HEADLESS", "0")
    monkeypatch.setenv("LLM_TIMEOUT_S", "30")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("SESSIONS_DIR", str(tmp_path / "custom_sessions"))
    get_settings.cache_clear()

    s = get_settings()
    assert s.max_fix_attempts == 5
    assert s.headless is False
    assert s.llm_timeout_s == 30
    assert s.openai_api_key == "test-key"
    assert s.sessions_dir == tmp_path / "custom_sessions"
    assert (tmp_path / "custom_sessions").is_dir()


def test_max_fix_attempts_default_is_2() -> None:
    assert Settings(_env_file=None).max_fix_attempts == 2
    assert get_settings().max_fix_attempts == 2


def test_dirs_created(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    monkeypatch.setenv("OUTPUT_DIR", str(nested / "out"))
    monkeypatch.setenv("MAIN_INBOX_DIR", str(nested / "inbox"))
    get_settings.cache_clear()

    get_settings()
    assert (nested / "out").is_dir()
    assert (nested / "inbox").is_dir()
    assert (tmp_path / "sessions").is_dir()
