"""Bộ câu hỏi: validate + nạp file (T03)"""

import copy
import json
from pathlib import Path

import pytest

from app.domain.questions import (
    QUESTION_SCHEMA_TEXT,
    BankFileError,
    load_bank_file,
    max_score,
    normalize_bank,
    validate_bank,
)

FIX = Path(__file__).resolve().parent.parent / "fixtures"
HDR = "type,question,options,answer,explanation,points\n"


def _bank() -> dict:
    return json.loads((FIX / "questions_valid.json").read_text(encoding="utf-8"))


def _errs(mutate) -> list[str]:
    b = _bank()
    mutate(b["questions"])
    return validate_bank(b)


def test_valid_bank_has_no_errors() -> None:
    assert validate_bank(_bank()) == []
    assert "mcq" in QUESTION_SCHEMA_TEXT


def test_too_few_questions() -> None:
    assert _errs(lambda qs: qs.__delitem__(slice(1, None)))


def test_too_many_questions() -> None:
    def m(qs):
        qs.extend(copy.deepcopy(qs[0]) | {"id": f"x{i}"} for i in range(50))

    assert _errs(m)


def test_missing_id() -> None:
    assert _errs(lambda qs: qs[0].pop("id"))


def test_duplicate_id() -> None:
    errs = _errs(lambda qs: qs[1].update(id="q1"))
    assert any("trùng" in e for e in errs)


def test_empty_question() -> None:
    assert _errs(lambda qs: qs[0].update(question="   "))


def test_unknown_type() -> None:
    assert _errs(lambda qs: qs[0].update(type="essay"))


def test_mcq_options_count() -> None:
    assert _errs(lambda qs: qs[0].update(options=["A"], answer=0))
    assert _errs(lambda qs: qs[0].update(options=list("ABCDEFG"), answer=0))


def test_mcq_duplicate_options() -> None:
    assert _errs(lambda qs: qs[0].update(options=["a", "a"], answer=0))


def test_mcq_answer_out_of_range() -> None:
    assert _errs(lambda qs: qs[0].update(answer=9))
    assert _errs(lambda qs: qs[0].update(answer=-1))


def test_mcq_answer_bool_rejected() -> None:
    assert _errs(lambda qs: qs[0].update(answer=True))


def test_true_false_answer_must_be_bool() -> None:
    assert _errs(lambda qs: qs[1].update(answer="đúng"))
    assert _errs(lambda qs: qs[1].update(answer=1))


def test_fill_blank_answer_empty() -> None:
    assert _errs(lambda qs: qs[2].update(answer=" "))
    assert _errs(lambda qs: qs[2].update(accept="x"))


def test_points_must_be_positive_int() -> None:
    for bad in (0, -5, True, 1.5, "10"):
        assert _errs(lambda qs, b=bad: qs[0].update(points=b)), bad


def test_invalid_fixture_reports_all() -> None:
    bank = json.loads((FIX / "questions_invalid.json").read_text(encoding="utf-8"))
    assert len(validate_bank(bank)) >= 4


def test_normalize_fills_defaults() -> None:
    b = normalize_bank({"questions": [{"type": "true_false", "question": "x", "answer": True}]})
    q = b["questions"][0]
    assert (q["id"], q["points"], q["explanation"], b["title"]) == ("q1", 10, "", "Bộ câu hỏi")


def test_normalize_keeps_content() -> None:
    b = _bank()
    assert normalize_bank(b) == b


def test_max_score() -> None:
    assert max_score(_bank()) == sum(q["points"] for q in _bank()["questions"])


def test_load_json_object() -> None:
    assert len(load_bank_file(FIX / "questions_valid.json")["questions"]) >= 3


def test_load_json_list(tmp_path: Path) -> None:
    p = tmp_path / "l.json"
    p.write_text(json.dumps(_bank()["questions"]), encoding="utf-8")
    assert load_bank_file(p)["title"] == "Bộ câu hỏi"


def test_load_csv_letter_answer(tmp_path: Path) -> None:
    b = load_bank_file(FIX / "questions_valid.csv")
    assert b["questions"][0]["answer"] == 0
    assert b["questions"][1]["answer"] is True
    p = tmp_path / "b.csv"
    p.write_text(HDR + "mcq,a,x|y,B,,\nmcq,b,x|y,A,,\nmcq,c,x|y,1,,5\n", encoding="utf-8")
    qs = load_bank_file(p)["questions"]
    assert [q["answer"] for q in qs] == [1, 0, 1]
    assert qs[2]["points"] == 5 and qs[0]["points"] == 10


def test_load_csv_with_bom(tmp_path: Path) -> None:
    p = tmp_path / "bom.csv"
    p.write_bytes(b"\xef\xbb\xbf" + (FIX / "questions_valid.csv").read_bytes())
    assert len(load_bank_file(p)["questions"]) >= 3


def test_load_csv_error_reports_line(tmp_path: Path) -> None:
    p = tmp_path / "e.csv"
    p.write_text(HDR + "mcq,a,x|y,A,,\ntrue_false,b,,maybe,,\nmcq,c,x|y,A,,\n", encoding="utf-8")
    with pytest.raises(BankFileError) as ei:
        load_bank_file(p)
    assert ei.value.errors[0].startswith("Dòng 3:")


def test_load_unsupported_ext(tmp_path: Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("hi")
    with pytest.raises(BankFileError):
        load_bank_file(p)


def test_load_bad_json(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    p.write_text("{bad")
    with pytest.raises(BankFileError):
        load_bank_file(p)
