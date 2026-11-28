import json
from pathlib import Path

import pytest

from app.domain.contract import (
    REQUIRED_TESTIDS,
    find_forbidden_calls,
    inject_bank,
    static_check,
)

BANK = {
    "title": "T",
    "questions": [
        {"id": "q1", "type": "mcq", "question": "a </script><b> ?", "options": ["x", "y"], "answer": 0}
    ],
}


@pytest.fixture
def ref() -> str:
    return (Path(__file__).parents[1] / "fixtures" / "reference_game.html").read_text(encoding="utf-8")


def test_reference_ok(ref):
    assert static_check(ref) == []


@pytest.mark.parametrize(
    ("old", "new", "code"),
    [
        ("<!DOCTYPE html>", "", "C2"),
        ('<html lang="vi">', "<html>", "C2"),
        ('name="viewport"', 'name="vp"', "C2"),
        ('id="game-root"', 'id="x"', "C3"),
        ("<svg ", "<p ", "C3"),
        ('id="question-bank"', 'id="qb"', "C4"),
        ("<style>", '<link rel="stylesheet" href="https://cdn.x/a.css"><style>', "C1"),
        ("<style>", '<script src="//cdn.x/a.js"></script><style>', "C1"),
        ("(function(){", "(function(){alert(1);", "C5"),
        ("(function(){", "(function(){fetch('/x');", "C5"),
        ("(function(){", "(function(){new XMLHttpRequest();", "C5"),
        ("(function(){", "(function(){new WebSocket('x');", "C5"),
        ("window.__GAME__=api;", "", "__GAME__"),
    ],
)
def test_violations(ref, old, new, code):
    assert old in ref
    errs = static_check(ref.replace(old, new, 1))
    assert errs
    assert any(code in e for e in errs)


def test_c6_size(ref):
    assert any("C6" in e for e in static_check(ref + "x" * 2_000_001))


@pytest.mark.parametrize("tid", REQUIRED_TESTIDS)
def test_missing_testid(ref, tid):
    errs = static_check(ref.replace(f'data-testid="{tid}"', 'data-x="1"'))
    assert any(tid in e for e in errs)


def test_forbidden_no_false_positive():
    assert find_forbidden_calls("obj.alert(1); myalert(2); $alert(3); x.fetch(1)") == []
    assert find_forbidden_calls("alert(1); confirm (2); prompt('x')") == ["alert", "confirm", "prompt"]


def test_inject_replaces_one(ref):
    out = inject_bank(ref, BANK)
    assert out.count('id="question-bank"') == 1
    assert "<\\/script>" in out
    body = out.split('id="question-bank">')[1].split("</script>")[0]
    assert json.loads(body.replace("<\\/", "</")) == BANK
    assert static_check(out) == []


def test_inject_inserts_when_missing(ref):
    out = inject_bank(ref.replace('id="question-bank"', 'id="qb"'), BANK)
    assert 'id="question-bank"' in out
    assert out.index('id="question-bank"') < out.index("<style>")


def test_contract_text_has_controls_rules():
    from app.domain.contract import CONTRACT_TEXT

    for needle in ("ĐIỀU KHIỂN", "getUserMedia", "webkitSpeechRecognition", "vi-VN", "console.warn", "chuột"):
        assert needle in CONTRACT_TEXT, needle
