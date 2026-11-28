"""N4 kiểm thử Playwright (T13)"""

import shutil
from pathlib import Path

import pytest

from app.core.models import Session, Version
from app.nodes import n4_test
from app.nodes.n4_test import run_tests, wrong_answer

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _make(tmp_path: Path, bank: dict, name: str) -> tuple[Session, Version]:
    vdir = tmp_path / "v1"
    vdir.mkdir()
    path = vdir / "index.html"
    shutil.copy(FIXTURES / name, path)
    return Session(question_bank=bank), Version(number=1, html_path=str(path))


def _is_file(p: str) -> bool:
    return Path(p).is_file()


def _strip_testid(path: Path, testid: str) -> None:
    html = path.read_text(encoding="utf-8").replace(f'data-testid="{testid}"', "")
    path.write_text(html, encoding="utf-8")


def test_wrong_answer() -> None:
    assert wrong_answer({"type": "mcq", "options": ["a", "b", "c"], "answer": 2}) == 0
    assert wrong_answer({"type": "true_false", "answer": True}) is False
    assert wrong_answer({"type": "fill_blank", "answer": "1/2"}) != "1/2"


@pytest.mark.browser
async def test_reference_game_passes(tmp_path, settings, sample_bank) -> None:
    session, version = _make(tmp_path, sample_bank, "reference_game.html")
    report = await run_tests(session, version, settings)
    assert report.passed, report.errors
    assert report.errors == []
    assert len(report.screenshots) == 4
    assert all(map(_is_file, report.screenshots))
    assert version.test_passed is True and version.screenshots == report.screenshots


@pytest.mark.browser
async def test_broken_no_result_detected(tmp_path, settings, sample_bank) -> None:
    session, version = _make(tmp_path, sample_bank, "broken_no_result.html")
    report = await run_tests(session, version, settings)
    assert not report.passed
    assert any("result-screen" in e for e in report.errors), report.errors
    assert version.test_passed is False and version.test_errors == report.errors


@pytest.mark.browser
async def test_broken_score_detected(tmp_path, settings, sample_bank) -> None:
    session, version = _make(tmp_path, sample_bank, "broken_score.html")
    report = await run_tests(session, version, settings)
    assert not report.passed
    assert any("đúng hết" in e and "score" in e for e in report.errors), report.errors


@pytest.mark.browser
async def test_broken_jserror_detected(tmp_path, settings, sample_bank) -> None:
    session, version = _make(tmp_path, sample_bank, "broken_jserror.html")
    report = await run_tests(session, version, settings)
    assert not report.passed
    assert any("pageerror" in e for e in report.errors), report.errors


@pytest.mark.browser
async def test_broken_overflow_detected_mobile(tmp_path, settings, sample_bank) -> None:
    session, version = _make(tmp_path, sample_bank, "broken_overflow.html")
    report = await run_tests(session, version, settings)
    assert not report.passed
    assert any(e.startswith("[375px]") and "tràn" in e for e in report.errors), report.errors
    assert not any(e.startswith("[1280px]") for e in report.errors), report.errors


@pytest.mark.browser
async def test_static_fail_skips_browser(tmp_path, settings, sample_bank, monkeypatch) -> None:
    session, version = _make(tmp_path, sample_bank, "reference_game.html")
    _strip_testid(Path(version.html_path), "restart-button")

    def boom(*args, **kwargs):
        raise AssertionError("browser_check không được chạy khi static fail")

    monkeypatch.setattr(n4_test, "browser_check", boom)
    report = await run_tests(session, version, settings)
    assert not report.passed
    assert any("restart-button" in e for e in report.errors)
    assert report.screenshots == [] and version.test_passed is False
