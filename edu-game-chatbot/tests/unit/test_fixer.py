"""FIX (T14)"""

import pytest

# Xoá dòng này khi bắt đầu T14.
pytestmark = pytest.mark.skip(reason="TODO T14")


async def test_fix_increments_attempts() -> None:
    raise NotImplementedError


async def test_fix_overwrites_same_version() -> None:
    raise NotImplementedError


async def test_fix_reinjects_bank() -> None:
    raise NotImplementedError
