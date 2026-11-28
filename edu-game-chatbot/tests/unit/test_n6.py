"""N6 xuất + MAIN (T16)"""

import json
import zipfile

import httpx
import pytest

from app.core.models import Session, Version
from app.nodes import n6_export as n6


@pytest.fixture
def made(settings, tmp_path, sample_bank, reference_html):
    html = tmp_path / "v1.html"
    html.write_text(reference_html, encoding="utf-8")
    shot = tmp_path / "s1.png"
    shot.write_bytes(b"png")
    v = Version(
        number=1,
        html_path=str(html),
        design={"title": "Ôn tập Đại số", "game_type": "quiz"},
        test_passed=True,
        screenshots=[str(shot)],
    )
    s = Session(question_bank=sample_bank, subject="Toán", grade="8", versions=[v])
    return s, v


def test_slugify_vietnamese() -> None:
    assert n6.slugify("Ôn tập Đại số") == "on-tap-dai-so"
    assert n6.slugify("???") == "game"
    assert len(n6.slugify("a" * 100)) <= 50


def test_export_structure(made, settings) -> None:
    s, v = made
    folder = n6.export(s, v, settings)
    assert folder.name == f"on-tap-dai-so_{s.id}"
    for name in ("index.html", "questions.json", "manifest.json", "export.zip"):
        assert (folder / name).is_file()
    assert (folder / "screenshots" / "s1.png").is_file()
    assert s.exported_to == str(folder.resolve())


def test_manifest_fields(made, settings) -> None:
    s, v = made
    m = json.loads((n6.export(s, v, settings) / "manifest.json").read_text(encoding="utf-8"))
    keys = {
        "session_id", "title", "game_type", "subject", "grade", "question_source",
        "num_questions", "max_score", "version", "revisions", "entry", "exported_at",
    }  # fmt: skip
    assert keys <= set(m)
    assert m["entry"] == "index.html"
    assert m["title"] == "Ôn tập Đại số"


def test_export_blocked_when_tests_failed(made, settings) -> None:
    s, v = made
    v.test_passed = None
    with pytest.raises(ValueError):
        n6.export(s, v, settings)


def test_zip_created(made, settings) -> None:
    s, v = made
    folder = n6.export(s, v, settings)
    names = zipfile.ZipFile(folder / "export.zip").namelist()
    assert "index.html" in names
    assert "export.zip" not in names


async def test_notify_writes_inbox(made, settings) -> None:
    s, v = made
    folder = n6.export(s, v, settings)
    assert await n6.notify_main(s, folder, settings) == []
    data = json.loads((settings.main_inbox_dir / f"{s.id}.json").read_text(encoding="utf-8"))
    assert data["folder"] == str(folder.resolve())


async def test_webhook_failure_is_warning(made, settings) -> None:
    s, v = made
    folder = n6.export(s, v, settings)
    settings.main_webhook_url = "http://main.test/hook"
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(500)

    warns = await n6.notify_main(s, folder, settings, transport=httpx.MockTransport(handler))
    assert len(warns) == 1
    assert len(calls) == 3
    assert (settings.main_inbox_dir / f"{s.id}.json").is_file()
