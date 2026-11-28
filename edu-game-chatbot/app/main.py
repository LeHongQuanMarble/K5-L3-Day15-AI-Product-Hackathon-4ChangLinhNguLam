"""FastAPI app factory. Chạy: uvicorn app.main:create_app --factory --reload (T19)"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import events, preview, sessions
from app.chatbot.engine import ChatEngine
from app.config import Settings, get_settings
from app.core.events import EventBus
from app.core.llm import LLMClient, OpenAILLM
from app.core.store import SessionStore

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def create_app(settings: Settings | None = None, llm: LLMClient | None = None) -> FastAPI:
    """Tạo app: dựng Settings/Store/EventBus/LLM/ChatEngine, gắn vào app.state,
    include router sessions/events/preview, mount web/ tại '/'.
    Test truyền llm=FakeLLM và settings trỏ tới thư mục tạm."""
    settings = settings or get_settings()
    settings.ensure_dirs()
    store = SessionStore(settings.sessions_dir)
    bus = EventBus()
    llm = llm or OpenAILLM(settings)
    app = FastAPI(title="Edu Game Chatbot")
    app.state.settings = settings
    app.state.store = store
    app.state.bus = bus
    app.state.engine = ChatEngine(store, llm, bus, settings)
    app.include_router(sessions.router)
    app.include_router(events.router)
    app.include_router(preview.router)
    if WEB_DIR.is_dir():
        app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app
