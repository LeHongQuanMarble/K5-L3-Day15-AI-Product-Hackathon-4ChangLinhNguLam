"""INPUT: cổng game học tập (T08)"""

import pytest

# Xoá dòng này khi bắt đầu T08.
pytestmark = pytest.mark.skip(reason="TODO T08")


async def test_educational_accepted() -> None:
    raise NotImplementedError


async def test_non_educational_rejected() -> None:
    raise NotImplementedError


async def test_bad_json_raises() -> None:
    raise NotImplementedError


async def test_intent_direct_match_skips_llm() -> None:
    raise NotImplementedError


async def test_intent_via_llm() -> None:
    raise NotImplementedError


async def test_intent_unknown_returns_none() -> None:
    raise NotImplementedError
