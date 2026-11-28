"""FIX (T14)"""

from pathlib import Path

from app.core.models import Session, Version
from app.domain.contract import QUESTION_BANK_ID
from app.nodes.fixer import MAX_ERRORS_IN_PROMPT, build_fix_prompt, fix


def _read(v: Version) -> str:
    return Path(v.html_path).read_text(encoding="utf-8")


def _setup(tmp_path: Path, sample_bank: dict, html: str) -> tuple[Session, Version]:
    p = tmp_path / "index.html"
    p.write_text(html, encoding="utf-8")
    session = Session(id="s1", question_bank=sample_bank)
    return session, Version(number=1, html_path=str(p))


async def test_fix_increments_attempts(tmp_path, settings, fake_llm, sample_bank, reference_html) -> None:
    session, v = _setup(tmp_path, sample_bank, reference_html)
    fake_llm.add("fix", f"```html\n{reference_html}\n```")
    await fix(fake_llm, settings, session, v, ["e1"])
    await fix(fake_llm.add("fix", reference_html), settings, session, v, ["e2"])
    assert v.fix_attempts == 2


async def test_fix_overwrites_same_version(tmp_path, settings, fake_llm, sample_bank, reference_html) -> None:
    session, v = _setup(tmp_path, sample_bank, reference_html)
    fixed = reference_html.replace("</body>", "<!--fixed--></body>", 1)
    fake_llm.add("fix", f"```html\n{fixed}\n```")
    await fix(fake_llm, settings, session, v, ["e1"])
    assert "<!--fixed-->" in _read(v)
    assert v.number == 1 and len(session.versions) == 0


async def test_fix_reinjects_bank(tmp_path, settings, fake_llm, sample_bank, reference_html) -> None:
    session, v = _setup(tmp_path, sample_bank, reference_html)
    stripped = "<html><body><h1>x</h1></body></html>"
    fake_llm.add("fix", f"```html\n{stripped}\n```")
    await fix(fake_llm, settings, session, v, ["e1"])
    out = _read(v)
    assert QUESTION_BANK_ID in out
    assert sample_bank["questions"][0]["question"] in out or sample_bank["questions"][0]["id"] in out


def test_build_fix_prompt_caps_errors() -> None:
    p = build_fix_prompt("<html/>", [f"err{i}" for i in range(30)])
    assert f"err{MAX_ERRORS_IN_PROMPT - 1}" in p and f"err{MAX_ERRORS_IN_PROMPT}" not in p
    assert "<html/>" in p and "LỖI CẦN SỬA" in p
