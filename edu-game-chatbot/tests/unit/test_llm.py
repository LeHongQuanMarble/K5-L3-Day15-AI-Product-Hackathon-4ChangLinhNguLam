"""LLM utils + FakeLLM (T06)"""

import httpx
import openai
import pytest

from app.config import Settings
from app.core import llm as llm_mod
from app.core.llm import LLMError, LLMFormatError, OpenAILLM, extract_html, parse_json
from app.core.prompts import PromptVarMissingError, load_prompt, prompt_name_of
from tests.conftest import FakeLLM


@pytest.mark.parametrize(
    "text",
    [
        '{"a": 1}',
        '```json\n{"a": 1}\n```',
        'Đây là kết quả:\n{"a": 1}\nHy vọng hữu ích.',
        '```\n{"a": 1}\n```',
    ],
)
def test_parse_json_wrappers(text: str) -> None:
    assert parse_json(text) == {"a": 1}


def test_parse_json_nested_with_noise() -> None:
    assert parse_json('x {"a": {"b": [1, 2]}} y') == {"a": {"b": [1, 2]}}


def test_parse_json_invalid_raises() -> None:
    with pytest.raises(LLMFormatError):
        parse_json("không có json {oops")


def test_extract_html_fenced() -> None:
    t = "ok\n```html\n<!DOCTYPE html><html><body>x</body></html>\n```\nxong"
    assert extract_html(t) == "<!DOCTYPE html><html><body>x</body></html>"


def test_extract_html_raw() -> None:
    t = "Intro <!doctype html><html></html> outro"
    assert extract_html(t) == "<!doctype html><html></html>"


def test_extract_html_missing_raises() -> None:
    with pytest.raises(LLMFormatError):
        extract_html("chỉ là chữ")


def test_load_prompt_vars_and_missing() -> None:
    with pytest.raises(PromptVarMissingError):
        load_prompt("question_gen")
    out = load_prompt("question_gen", SCHEMA="S", CONTRACT="C", BUTTONS="B")
    assert "{{" not in out


def test_prompt_name_of() -> None:
    assert prompt_name_of("# prompt: design\nxyz") == "design"
    assert prompt_name_of("không có") is None


class _Resp:
    def __init__(self, text: str) -> None:
        msg = type("M", (), {"content": text})
        self.choices = [type("C", (), {"message": msg})]


def _make(monkeypatch, outcomes: list) -> tuple[OpenAILLM, list]:
    async def no_sleep(_s: float) -> None:
        return None

    monkeypatch.setattr(llm_mod.asyncio, "sleep", no_sleep)
    client = OpenAILLM(Settings(_env_file=None, openai_api_key="k"))
    calls: list = []

    async def create(**kw):
        calls.append(kw)
        o = outcomes.pop(0)
        if isinstance(o, Exception):
            raise o
        return o

    monkeypatch.setattr(client._client.chat.completions, "create", create)
    return client, calls


def _status_err(code: int) -> openai.APIStatusError:
    req = httpx.Request("POST", "http://x")
    return openai.APIStatusError("boom", response=httpx.Response(code, request=req), body=None)


async def test_openai_retry_then_success(monkeypatch) -> None:
    err = openai.APIConnectionError(request=httpx.Request("POST", "http://x"))
    client, calls = _make(monkeypatch, [err, _status_err(503), _Resp("hi")])
    assert await client.complete(system="s", user="u", model="m", json_mode=True) == "hi"
    assert len(calls) == 3
    assert calls[0]["response_format"] == {"type": "json_object"}


async def test_openai_4xx_no_retry(monkeypatch) -> None:
    client, calls = _make(monkeypatch, [_status_err(400), _Resp("never")])
    with pytest.raises(LLMError):
        await client.complete(system="s", user="u", model="m")
    assert len(calls) == 1


async def test_openai_gives_up_after_retries(monkeypatch) -> None:
    client, calls = _make(monkeypatch, [_status_err(500)] * 3)
    with pytest.raises(LLMError):
        await client.complete(system="s", user="u", model="m")
    assert len(calls) == 3


async def test_fake_llm_exhausted_raises() -> None:
    f = FakeLLM({"design": ["a", lambda s, u: "b:" + u]})
    sys = "# prompt: design\nx"
    assert await f.complete(system=sys, user="u", model="m") == "a"
    assert await f.complete(system=sys, user="u", model="m") == "b:u"
    with pytest.raises(AssertionError, match="design"):
        await f.complete(system=sys, user="u", model="m")
    assert len(f.calls_for("design")) == 3


def test_empty_base_url_uses_default() -> None:
    """OPENAI_BASE_URL= (rỗng, như .env.example) không được làm hỏng URL gọi API."""
    client = OpenAILLM(Settings(_env_file=None, openai_api_key="k", openai_base_url=""))
    assert client._client.base_url.host == "api.openai.com"
