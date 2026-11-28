"""N6 xuất + MAIN (T16)"""

import pytest

# Xoá dòng này khi bắt đầu T16.
pytestmark = pytest.mark.skip(reason="TODO T16")


def test_slugify_vietnamese() -> None:
    raise NotImplementedError


def test_export_structure() -> None:
    raise NotImplementedError


def test_manifest_fields() -> None:
    raise NotImplementedError


def test_export_blocked_when_tests_failed() -> None:
    raise NotImplementedError


def test_zip_created() -> None:
    raise NotImplementedError


async def test_notify_writes_inbox() -> None:
    raise NotImplementedError


async def test_webhook_failure_is_warning() -> None:
    raise NotImplementedError
