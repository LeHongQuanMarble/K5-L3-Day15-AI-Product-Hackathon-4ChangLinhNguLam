"""LLM client + tiện ích parse output. (T06)"""

from __future__ import annotations

from typing import Protocol

from app.config import Settings


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
        raise NotImplementedError

    async def complete(self, *, system: str, user: str, model: str, json_mode: bool = False) -> str:
        """Chat Completions; retry llm_max_retries lần (2s, 5s) với lỗi mạng/5xx/timeout; 4xx -> LLMError ngay."""
        raise NotImplementedError


def parse_json(text: str) -> dict:
    """Lấy object JSON từ text (chịu ```json```, chữ thừa trước/sau). Lỗi -> LLMFormatError."""
    raise NotImplementedError


def extract_html(text: str) -> str:
    """Lấy tài liệu HTML từ khối ```html``` hoặc <!DOCTYPE ... </html>. Lỗi -> LLMFormatError."""
    raise NotImplementedError
