"""N1 đọc tài liệu (T09)"""

import pytest

# Xoá dòng này khi bắt đầu T09.
pytestmark = pytest.mark.skip(reason="TODO T09")


def test_read_txt() -> None:
    raise NotImplementedError


def test_read_md() -> None:
    raise NotImplementedError


def test_read_docx_with_table() -> None:
    raise NotImplementedError


def test_read_pdf() -> None:
    raise NotImplementedError


def test_unsupported_ext() -> None:
    raise NotImplementedError


def test_file_too_large() -> None:
    raise NotImplementedError


def test_truncate_max_chars() -> None:
    raise NotImplementedError


def test_all_empty_raises() -> None:
    raise NotImplementedError
