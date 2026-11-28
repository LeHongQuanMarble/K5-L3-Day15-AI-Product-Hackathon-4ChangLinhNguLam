"""FastAPI app factory. Chạy: uvicorn app.main:create_app --factory --reload (T19)"""

from __future__ import annotations

from fastapi import FastAPI

from app.config import Settings
from app.core.llm import LLMClient


def create_app(settings: Settings | None = None, llm: LLMClient | None = None) -> FastAPI:
    """Tạo app: dựng Settings/Store/EventBus/LLM/ChatEngine, gắn vào app.state,
    include router sessions/events/preview, mount web/ tại '/'.
    Test truyền llm=FakeLLM và settings trỏ tới thư mục tạm."""
    raise NotImplementedError
