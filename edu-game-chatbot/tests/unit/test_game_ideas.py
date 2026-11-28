"""Gợi ý ý tưởng game (F02)"""

import json

import pytest

from app.chatbot import replies
from app.core.llm import LLMFormatError
from app.core.models import Session
from app.nodes.game_ideas import IDEA_KEYS, build_ideas_prompt, suggest_ideas, validate_ideas
from tests.conftest import ideas_reply, make_ideas


@pytest.fixture
def session(sample_bank):
    return Session(
        request="game ôn phân số lớp 4", subject="Toán", grade="4", topic="Phân số", question_bank=sample_bank
    )


async def test_suggest_ok(fake_llm, settings, session) -> None:
    fake_llm.add("game_ideas", ideas_reply())
    ideas = await suggest_ideas(fake_llm, settings, session)
    assert [i["title"] for i in ideas] == ["Ý tưởng 1", "Ý tưởng 2", "Ý tưởng 3"]
    assert all(set(IDEA_KEYS) <= set(i) for i in ideas)
    call = fake_llm.calls[0]
    assert call["json_mode"] is True and call["model"] == settings.design_model


async def test_prompt_has_samples_not_full_bank(fake_llm, settings, session, sample_bank) -> None:
    fake_llm.add("game_ideas", ideas_reply())
    await suggest_ideas(fake_llm, settings, session, avoid=["Cũ A", "Cũ B"])
    user = fake_llm.calls[0]["user"]
    qs = sample_bank["questions"]
    assert len(qs) > 3
    for q in qs[:3]:
        assert json.dumps(q["question"], ensure_ascii=False)[1:-1] in user
    for q in qs[3:]:
        assert f'"id": "{q["id"]}"' not in user
        assert json.dumps(q["question"], ensure_ascii=False)[1:-1] not in user
    for needle in ("game ôn phân số lớp 4", "Toán", "Phân số", "Cũ A", "Cũ B", '"max_score"'):
        assert needle in user


@pytest.mark.parametrize("missing", IDEA_KEYS)
def test_missing_key_raises(missing: str) -> None:
    data = make_ideas()
    del data["ideas"][1][missing]
    with pytest.raises(LLMFormatError):
        validate_ideas(data)


@pytest.mark.parametrize(
    "data", [{}, {"ideas": "x"}, {"ideas": make_ideas()["ideas"][:2]}, {"ideas": [1, 2, 3]}]
)
def test_bad_shape_raises(data: dict) -> None:
    with pytest.raises(LLMFormatError):
        validate_ideas(data)


async def test_not_json_raises(fake_llm, settings, session) -> None:
    fake_llm.add("game_ideas", "không phải JSON")
    with pytest.raises(LLMFormatError):
        await suggest_ideas(fake_llm, settings, session)


def test_normalize_controls_and_interactions() -> None:
    data = make_ideas()
    data["ideas"][0]["recommended_controls"] = "Keyboard, laser"
    data["ideas"][0]["interactions"] = "kéo thả; né bom nước"
    data["ideas"][1]["recommended_controls"] = ["laser"]
    ideas = validate_ideas(data)
    assert ideas[0]["recommended_controls"] == ["keyboard"]
    assert ideas[0]["interactions"] == ["kéo thả", "né bom nước"]
    assert ideas[1]["recommended_controls"] == ["mouse"]


def test_build_prompt_without_avoid(session) -> None:
    assert "KHÔNG lặp lại" not in build_ideas_prompt(session, [])


def test_idea_replies() -> None:
    ideas = make_ideas()["ideas"]
    ideas[2]["title"] = "Một cái tên rất rất dài vượt quá bốn mươi ký tự cho nút"
    buttons = replies.idea_buttons(ideas)
    assert [b.id for b in buttons] == ["idea_1", "idea_2", "idea_3", "ideas_more", "gp_suggest"]
    assert buttons[0].label == "💡 Ý tưởng 1"
    assert all(len(b.label) <= 40 for b in buttons)
    text = replies.ideas_message(ideas)
    assert "**Ý tưởng 1**" in text and "Tương tác: di chuyển nhân vật, né chướng ngại" in text
    assert "Tiến triển:" in text
    ctl = replies.controls_buttons(["motion"])
    assert ctl[0].id == "ctl_motion" and ctl[0].label.endswith("(gợi ý)")
    assert [b.id for b in replies.controls_buttons()] == [
        "ctl_mouse",
        "ctl_keyboard",
        "ctl_motion",
        "ctl_voice",
    ]
