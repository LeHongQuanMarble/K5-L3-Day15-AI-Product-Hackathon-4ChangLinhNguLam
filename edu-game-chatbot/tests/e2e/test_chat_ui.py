"""E2E giao diện chat (FakeLLM + Playwright) (T21)"""

import pytest

# Xoá mark skip khi bắt đầu T21.
pytestmark = [pytest.mark.browser, pytest.mark.skip(reason="TODO T21")]


def test_full_flow_topic_with_revision() -> None:
    raise NotImplementedError


def test_mobile_layout() -> None:
    raise NotImplementedError


def test_resume_session_from_url() -> None:
    raise NotImplementedError
