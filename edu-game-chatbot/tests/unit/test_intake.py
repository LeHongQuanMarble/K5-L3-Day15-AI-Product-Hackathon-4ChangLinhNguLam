"""INPUT: cổng game học tập (T08)"""

import json

import pytest

from app.core.llm import LLMFormatError
from app.core.models import Button
from app.nodes.intake import check_educational, classify_intent, match_button

BTNS = [Button(id="approve", label="Duyệt"), Button(id="revise", label="Chỉnh sửa")]


async def test_educational_accepted(fake_llm, settings) -> None:
    fake_llm.add("intake", json.dumps({"is_educational": True, "subject": "Toán", "grade": "5"}))
    r = await check_educational(fake_llm, settings, "game ghép phân số")
    assert r.is_educational and r.subject == "Toán"
    assert fake_llm.calls[0]["user"] == "game ghép phân số"
    assert fake_llm.calls[0]["json_mode"] is True


async def test_non_educational_rejected(fake_llm, settings) -> None:
    fake_llm.add("intake", '{"is_educational": false, "reason": "cờ bạc"}')
    r = await check_educational(fake_llm, settings, "game casino")
    assert not r.is_educational and r.reason == "cờ bạc"


async def test_bad_json_raises(fake_llm, settings) -> None:
    fake_llm.add("intake", "không phải json", '{"reason": "thiếu cờ"}')
    with pytest.raises(LLMFormatError):
        await check_educational(fake_llm, settings, "x")
    with pytest.raises(LLMFormatError):
        await check_educational(fake_llm, settings, "x")


async def test_intent_direct_match_no_llm(fake_llm, settings) -> None:
    assert await classify_intent(fake_llm, settings, "  DUYỆT ", BTNS) == "approve"
    assert await classify_intent(fake_llm, settings, "Revise", BTNS) == "revise"
    assert fake_llm.calls == []
    assert match_button("zzz", BTNS) is None


async def test_intent_llm(fake_llm, settings) -> None:
    fake_llm.add("intent", '{"button_id": "revise"}', '{"button_id": "bogus"}', '{"button_id": null}')
    assert await classify_intent(fake_llm, settings, "sửa giúp mình", BTNS) == "revise"
    assert "revise: Chỉnh sửa" in fake_llm.calls[0]["system"]
    assert fake_llm.calls[0]["user"] == "sửa giúp mình"
    assert await classify_intent(fake_llm, settings, "abc", BTNS) is None
    assert await classify_intent(fake_llm, settings, "abc", BTNS) is None
