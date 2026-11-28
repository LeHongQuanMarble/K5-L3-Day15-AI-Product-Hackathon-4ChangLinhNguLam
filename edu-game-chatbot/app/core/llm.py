"""LLM client + tiện ích parse output. (T06)"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Protocol

import openai
from openai import AsyncOpenAI

from app.config import Settings

RETRY_DELAYS = (2.0, 5.0)


class LLMError(Exception):
    """Lỗi gọi LLM sau khi đã retry."""


class LLMFormatError(LLMError):
    """LLM trả về sai định dạng (không parse được JSON/HTML)."""


class LLMClient(Protocol):
    async def complete(self, *, system: str, user: str, model: str, json_mode: bool = False) -> str:
        """Gửi 1 lượt system+user, trả về text của model."""
        ...


class OpenAILLM:
    def __init__(self, settings: Settings) -> None:
        """Tạo AsyncOpenAI (api_key, base_url, timeout từ settings). Chỉ đọc key tại đây."""
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=settings.llm_timeout_s,
            max_retries=0,
        )
        self._max_retries = settings.llm_max_retries

    async def complete(self, *, system: str, user: str, model: str, json_mode: bool = False) -> str:
        """Chat Completions; retry llm_max_retries lần (2s, 5s) với lỗi mạng/5xx/timeout; 4xx -> LLMError ngay."""
        kwargs: dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        attempt = 0
        while True:
            try:
                resp = await self._client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content or ""
            except openai.APIConnectionError as e:  # gồm cả timeout
                err: Exception = e
            except openai.APIStatusError as e:
                if e.status_code < 500:
                    raise LLMError(f"LLM lỗi {e.status_code}: {e}") from e
                err = e
            if attempt >= self._max_retries:
                raise LLMError(f"LLM lỗi sau {attempt + 1} lần thử: {err}") from err
            await asyncio.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])
            attempt += 1


_FENCE_RE = re.compile(r"```[a-zA-Z]*\s*\n?(.*?)```", re.DOTALL)


def parse_json(text: str) -> dict:
    """Lấy object JSON từ text (chịu ```json```, chữ thừa trước/sau). Lỗi -> LLMFormatError."""
    candidates = [text.strip()] + [m.strip() for m in _FENCE_RE.findall(text)]
    dec = json.JSONDecoder()
    for c in candidates:
        try:
            v = json.loads(c)
            if isinstance(v, dict):
                return v
        except ValueError:
            pass
        for m in re.finditer(r"\{", c):
            try:
                v, _ = dec.raw_decode(c[m.start() :])
            except ValueError:
                continue
            if isinstance(v, dict):
                return v
    raise LLMFormatError("Không tìm thấy JSON object hợp lệ trong câu trả lời của LLM")


def extract_html(text: str) -> str:
    """Lấy tài liệu HTML từ khối ```html``` hoặc <!DOCTYPE ... </html>. Lỗi -> LLMFormatError."""
    m = re.search(r"```html\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    body = m.group(1) if m else text
    start = re.search(r"<!DOCTYPE", body, re.IGNORECASE)
    end = body.lower().rfind("</html>")
    if start and end > start.start():
        return body[start.start() : end + len("</html>")].strip()
    if m and "<html" in body.lower():
        return body.strip()
    raise LLMFormatError("Không tìm thấy tài liệu HTML trong câu trả lời của LLM")
