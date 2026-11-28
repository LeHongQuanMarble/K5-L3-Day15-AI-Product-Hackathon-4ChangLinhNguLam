from app.core.models import Session, Version
from app.nodes.n5_review import build_review_message, humanize_errors, preview_url


def _ids(m):
    return [b.id for b in m.buttons]


def test_pass_buttons():
    s = Session()
    m = build_review_message(s, Version(number=2, html_path="x", test_passed=True))
    assert _ids(m) == ["approve", "revise", "cancel"]
    assert m.preview_url == preview_url(s.id, 2) == f"/preview/{s.id}/v2"


def test_fail_buttons_and_max_errors():
    errs = [f"[375px] loi {i}" for i in range(12)]
    v = Version(number=1, html_path="x", test_passed=False, test_errors=errs)
    m = build_review_message(Session(), v)
    assert _ids(m) == ["revise", "cancel"]
    assert "loi 7" in m.text and "loi 8" not in m.text


def test_humanize_dedupe_and_trim():
    out = humanize_errors(["a  b", "a b", "x" * 500])
    assert out[0] == "a b" and len(out) == 2 and len(out[1]) <= 200
