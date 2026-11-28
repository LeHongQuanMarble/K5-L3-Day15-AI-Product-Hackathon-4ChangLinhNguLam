"""Mô hình dữ liệu (ARCHITECTURE §3). (T05)
Phần khai báo trường là cấu trúc cố định — không đổi tên trường khi chưa hỏi."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class State(StrEnum):
    AWAIT_REQUEST = "AWAIT_REQUEST"
    AWAIT_SOURCE = "AWAIT_SOURCE"
    AWAIT_SOURCE_INPUT = "AWAIT_SOURCE_INPUT"
    BUILDING_QUESTIONS = "BUILDING_QUESTIONS"
    AWAIT_QUESTION_APPROVAL = "AWAIT_QUESTION_APPROVAL"
    SUGGESTING_GAMES = "SUGGESTING_GAMES"
    AWAIT_GAMEPLAY = "AWAIT_GAMEPLAY"
    AWAIT_CONTROLS = "AWAIT_CONTROLS"
    AWAIT_VISUAL = "AWAIT_VISUAL"
    READY_TO_DESIGN = "READY_TO_DESIGN"
    PIPELINE_RUNNING = "PIPELINE_RUNNING"
    AWAIT_REVIEW = "AWAIT_REVIEW"
    AWAIT_REVISION_TEXT = "AWAIT_REVISION_TEXT"
    EXPORTING = "EXPORTING"
    DONE = "DONE"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


BUSY_STATES = {
    State.BUILDING_QUESTIONS,
    State.SUGGESTING_GAMES,
    State.READY_TO_DESIGN,
    State.PIPELINE_RUNNING,
    State.EXPORTING,
}
TERMINAL_STATES = {State.DONE, State.REJECTED, State.CANCELLED}


class Source(StrEnum):
    USER = "user"
    DOCUMENT = "document"
    TOPIC = "topic"


def utcnow() -> datetime:
    """Thời điểm hiện tại (UTC, có timezone)."""
    return datetime.now(UTC)


def new_id() -> str:
    """Sinh id ngắn duy nhất (12 ký tự hex)."""
    return uuid.uuid4().hex[:12]


class Button(BaseModel):
    id: str
    label: str


class Message(BaseModel):
    id: str = Field(default_factory=new_id)
    role: Literal["user", "bot", "system"]
    text: str
    buttons: list[Button] = []
    attachments: list[str] = []
    preview_url: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Version(BaseModel):
    number: int
    html_path: str
    design: dict = {}
    test_passed: bool | None = None
    test_errors: list[str] = []
    fix_attempts: int = 0
    screenshots: list[str] = []


class DocumentInfo(BaseModel):
    name: str
    path: str
    chars: int = 0


class Session(BaseModel):
    id: str = Field(default_factory=new_id)
    state: State = State.AWAIT_REQUEST
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    request: str = ""
    subject: str | None = None
    grade: str | None = None
    source: Source | None = None
    topic: str = ""
    num_questions: int = 10

    documents: list[DocumentInfo] = []
    question_bank: dict = {}
    question_feedback: list[str] = []

    # Yêu cầu game của giáo viên (F01): nhãn nút hoặc nguyên văn mô tả tự do
    gameplay: str = ""
    controls: str = ""
    controls_code: str = ""  # mouse | keyboard | motion | voice | custom
    visual: str = ""
    # Gợi ý ý tưởng game (F02): lần gợi ý gần nhất + ý tưởng được chọn đầy đủ
    game_ideas: list[dict] = []
    game_concept: dict = {}

    design: dict = {}
    design_history: list[dict] = []
    revisions: list[str] = []
    versions: list[Version] = []

    messages: list[Message] = []
    events: list[dict] = []
    exported_to: str | None = None
    error: str | None = None

    @property
    def latest_version(self) -> Version | None:
        """Phiên bản mới nhất hoặc None."""
        return self.versions[-1] if self.versions else None
