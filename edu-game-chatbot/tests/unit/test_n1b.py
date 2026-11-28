"""N1b bộ câu hỏi (T10)"""

import pytest

# Xoá dòng này khi bắt đầu T10.
pytestmark = pytest.mark.skip(reason="TODO T10")


def test_from_user_file_valid() -> None:
    raise NotImplementedError


def test_from_user_file_invalid() -> None:
    raise NotImplementedError


async def test_generate_topic_ok() -> None:
    raise NotImplementedError


async def test_generate_document_uses_doc_text() -> None:
    raise NotImplementedError


async def test_generate_retry_includes_errors() -> None:
    raise NotImplementedError


async def test_generate_wrong_count_retried() -> None:
    raise NotImplementedError


async def test_generate_fails_after_retries() -> None:
    raise NotImplementedError


async def test_edit_keeps_ids() -> None:
    raise NotImplementedError


async def test_edit_user_source_keeps_untouched() -> None:
    raise NotImplementedError


def test_preview_text() -> None:
    raise NotImplementedError
