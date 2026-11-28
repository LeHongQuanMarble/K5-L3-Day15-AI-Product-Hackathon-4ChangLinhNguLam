"""API (T19)"""

import pytest

# Xoá dòng này khi bắt đầu T19.
pytestmark = pytest.mark.skip(reason="TODO T19")


async def test_create_and_get_session() -> None:
    raise NotImplementedError


async def test_post_message_accepted() -> None:
    raise NotImplementedError


async def test_post_message_requires_text_or_action() -> None:
    raise NotImplementedError


async def test_upload_rejects_bad_ext() -> None:
    raise NotImplementedError


async def test_upload_rejects_traversal() -> None:
    raise NotImplementedError


async def test_preview_has_csp() -> None:
    raise NotImplementedError


async def test_export_before_done_409() -> None:
    raise NotImplementedError


async def test_sse_receives_progress() -> None:
    raise NotImplementedError
