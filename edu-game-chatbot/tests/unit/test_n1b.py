import copy
import json

import pytest

from app.core.models import Source
from app.domain.questions import BankFileError
from app.nodes import n1b_questions as n1b


def _gen(llm, settings, n=3):
    return n1b.generate(llm, settings, source=Source.TOPIC, request="r", num_questions=n, topic="phân số")


async def test_valid_first_try(fake_llm, settings, sample_bank):
    n = len(sample_bank["questions"])
    fake_llm.add("question_gen", json.dumps(sample_bank))
    bank = await _gen(fake_llm, settings, n)
    assert len(bank["questions"]) == n
    assert len(fake_llm.calls_for("question_gen")) == 1


async def test_retry_includes_errors(fake_llm, settings, sample_bank):
    n = len(sample_bank["questions"])
    bad = copy.deepcopy(sample_bank)
    bad["questions"][0]["answer"] = 9
    fake_llm.add("question_gen", json.dumps(bad), json.dumps(sample_bank))
    await _gen(fake_llm, settings, n)
    calls = fake_llm.calls_for("question_gen")
    assert len(calls) == 2
    assert "Câu 1" in calls[1]["user"]


async def test_wrong_count_three_failures(fake_llm, settings, sample_bank):
    fake_llm.add("question_gen", *[json.dumps(sample_bank)] * 3)
    with pytest.raises(n1b.QuestionGenError):
        await _gen(fake_llm, settings, len(sample_bank["questions"]) + 1)
    assert len(fake_llm.calls_for("question_gen")) == 3


async def test_non_json_raises(fake_llm, settings):
    fake_llm.add("question_gen", "xin lỗi", "xin lỗi", "xin lỗi")
    with pytest.raises(n1b.QuestionGenError):
        await _gen(fake_llm, settings)


async def test_edit_keeps_unmentioned(fake_llm, settings, sample_bank):
    new = copy.deepcopy(sample_bank)
    new["questions"][0]["question"] = "đã sửa"
    new["questions"][1]["question"] = "AI tự ý sửa"
    fake_llm.add("question_edit", json.dumps(new))
    out = await n1b.edit(fake_llm, settings, sample_bank, "sửa q1", Source.USER)
    assert out["questions"][0]["question"] == "đã sửa"
    assert out["questions"][1] == sample_bank["questions"][1]
    assert [q["id"] for q in out["questions"]] == [q["id"] for q in sample_bank["questions"]]


async def test_edit_ai_source(fake_llm, settings, sample_bank):
    fake_llm.add("question_edit", json.dumps(sample_bank))
    out = await n1b.edit(fake_llm, settings, sample_bank, "đổi", Source.TOPIC)
    assert out["questions"] == sample_bank["questions"]


def test_from_user_file(tmp_path, sample_bank):
    p = tmp_path / "b.json"
    p.write_text(json.dumps(sample_bank), encoding="utf-8")
    assert n1b.from_user_file(p)["questions"]
    p.write_text("{bad", encoding="utf-8")
    with pytest.raises(BankFileError):
        n1b.from_user_file(p)


def test_preview(sample_bank):
    t = n1b.preview_text(sample_bank, limit=2)
    assert sample_bank["title"] in t and "điểm" in t
    assert len(t.splitlines()) <= 4
