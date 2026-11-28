"""N2 thiết kế (T11)"""

import json

import pytest

from app.core.llm import LLMFormatError
from app.core.models import Session
from app.nodes.n2_design import REQUIRED_KEYS, bank_stats, build_design_prompt, design

GOOD = {k: "x" for k in REQUIRED_KEYS}


@pytest.fixture
def session(sample_bank):
    return Session(request="game phân số", topic="Phân số", question_bank=sample_bank)


async def test_design_ok(fake_llm, settings, session) -> None:
    fake_llm.add("design", json.dumps(GOOD))
    out = await design(fake_llm, settings, session)
    assert out == GOOD and session.design == GOOD
    assert fake_llm.calls[0]["json_mode"] is True


async def test_missing_keys_raises(fake_llm, settings, session) -> None:
    fake_llm.add("design", json.dumps({"title": "t"}))
    with pytest.raises(LLMFormatError):
        await design(fake_llm, settings, session)


async def test_revision_in_prompt(fake_llm, settings, session) -> None:
    fake_llm.add("design", json.dumps(GOOD))
    await design(fake_llm, settings, session, "đổi nền màu xanh")
    assert "đổi nền màu xanh" in fake_llm.calls[0]["user"]


async def test_old_design_to_history(fake_llm, settings, session) -> None:
    session.design = {"title": "cũ"}
    fake_llm.add("design", json.dumps(GOOD))
    await design(fake_llm, settings, session)
    assert session.design_history == [{"title": "cũ"}]
    assert session.design == GOOD


async def test_prompt_excludes_full_bank(session, sample_bank) -> None:
    s = bank_stats(sample_bank)
    assert s["count"] == len(sample_bank["questions"])
    assert len(s["samples"]) <= 3
    prompt = build_design_prompt(session, None)
    last = sample_bank["questions"][-1]["question"]
    if len(sample_bank["questions"]) > 3:
        assert last not in prompt


async def test_teacher_requirements_in_prompt(fake_llm, settings, session) -> None:
    session.gameplay = "Đua về đích / vượt chướng ngại"
    session.controls, session.controls_code = "Bàn phím", "keyboard"
    session.visual = "nền xanh biển, nhân vật cá heo"
    fake_llm.add("design", json.dumps(GOOD | {"controls": "x"}))
    out = await design(fake_llm, settings, session, "đổi nền màu xanh")
    user = fake_llm.calls[0]["user"]
    for value in (session.gameplay, "Bàn phím", "keyboard", session.visual):
        assert value in user
    assert user.index("YÊU CẦU BẮT BUỘC CỦA GIÁO VIÊN") < user.index("YÊU CẦU CHỈNH SỬA")
    assert out["controls"] == "x"  # LLM đã trả controls thì giữ nguyên


async def test_controls_filled_from_session(fake_llm, settings, session) -> None:
    session.controls = "Âm thanh / giọng nói (micro)"
    fake_llm.add("design", json.dumps(GOOD | {"controls": ""}))
    out = await design(fake_llm, settings, session)
    assert out["controls"] == session.controls


def test_prompt_without_requirements(session) -> None:
    assert "GIÁO VIÊN" not in build_design_prompt(session, None)


async def test_game_concept_in_prompt_and_defaults(fake_llm, settings, session) -> None:
    session.game_concept = {
        "title": "Pizza phân số",
        "question_integration": "đáp án là các lát pizza",
        "progression": "3 mạng, combo",
    }
    fake_llm.add("design", json.dumps(GOOD))
    out = await design(fake_llm, settings, session)
    user = fake_llm.calls[0]["user"]
    assert "Pizza phân số" in user and "Ý TƯỞNG GAME GIÁO VIÊN ĐÃ CHỌN" in user
    assert out["question_integration"] == "đáp án là các lát pizza"
    assert out["progression"] == "3 mạng, combo"
    system = fake_llm.calls[0]["system"]
    assert "ÍT NHẤT 2 lớp tương tác" in system and "explanation" in system


def test_no_concept_section_when_empty(session) -> None:
    assert "Ý TƯỞNG GAME" not in build_design_prompt(session, None)
