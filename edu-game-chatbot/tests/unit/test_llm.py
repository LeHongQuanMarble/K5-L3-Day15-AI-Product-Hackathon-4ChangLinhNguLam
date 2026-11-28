"""LLM utils + FakeLLM (T06)"""

import pytest

# Xoá dòng này khi bắt đầu T06.
pytestmark = pytest.mark.skip(reason="TODO T06")


def test_parse_json_plain() -> None:
    raise NotImplementedError


def test_parse_json_fenced() -> None:
    raise NotImplementedError


def test_parse_json_with_noise() -> None:
    raise NotImplementedError


def test_parse_json_invalid_raises() -> None:
    raise NotImplementedError


def test_extract_html_fenced() -> None:
    raise NotImplementedError


def test_extract_html_raw() -> None:
    raise NotImplementedError


def test_extract_html_missing_raises() -> None:
    raise NotImplementedError


async def test_openai_retry_then_success() -> None:
    raise NotImplementedError


async def test_openai_4xx_no_retry() -> None:
    raise NotImplementedError


async def test_fake_llm_exhausted_raises() -> None:
    raise NotImplementedError
