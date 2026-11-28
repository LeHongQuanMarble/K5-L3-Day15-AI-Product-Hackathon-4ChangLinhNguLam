"""SessionStore (Session Memory) (T05)"""

import pytest

# Xoá dòng này khi bắt đầu T05.
pytestmark = pytest.mark.skip(reason="TODO T05")


def test_create_and_get_roundtrip() -> None:
    raise NotImplementedError


def test_get_missing_raises_keyerror() -> None:
    raise NotImplementedError


def test_save_is_atomic() -> None:
    raise NotImplementedError


def test_updated_at_increases() -> None:
    raise NotImplementedError


def test_safe_path_rejects_traversal() -> None:
    raise NotImplementedError


def test_safe_path_rejects_absolute() -> None:
    raise NotImplementedError


def test_add_message_and_event() -> None:
    raise NotImplementedError


async def test_lock_is_per_session() -> None:
    raise NotImplementedError
