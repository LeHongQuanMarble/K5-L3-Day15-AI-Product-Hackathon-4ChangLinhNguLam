"""N4 kiểm thử Playwright (T13)"""

import pytest

# Xoá mark skip khi bắt đầu T13.
pytestmark = [pytest.mark.browser, pytest.mark.skip(reason="TODO T13")]


async def test_reference_game_passes() -> None:
    raise NotImplementedError


async def test_broken_no_result_detected() -> None:
    raise NotImplementedError


async def test_broken_score_detected() -> None:
    raise NotImplementedError


async def test_broken_jserror_detected() -> None:
    raise NotImplementedError


async def test_broken_overflow_detected_mobile() -> None:
    raise NotImplementedError


async def test_static_fail_skips_browser() -> None:
    raise NotImplementedError
