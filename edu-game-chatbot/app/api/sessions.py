"""REST API phiên chat (ARCHITECTURE §4). (T19)"""

from __future__ import annotations

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.chatbot.engine import ChatEngine
from app.core.models import Session

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

ALLOWED_UPLOAD_EXTS = (".pdf", ".docx", ".txt", ".md", ".json", ".csv")


class MessageIn(BaseModel):
    text: str | None = None
    action: str | None = None


class SessionOut(BaseModel):
    id: str
    state: str
    messages: list[dict]


def get_engine(request: Request) -> ChatEngine:
    """Lấy ChatEngine từ request.app.state.engine."""
    raise NotImplementedError


def to_session_out(session: Session) -> SessionOut:
    """Chuyển Session -> SessionOut (messages ở dạng model_dump(mode='json'))."""
    raise NotImplementedError


@router.post("", status_code=201)
async def create_session(request: Request) -> SessionOut:
    """Tạo phiên + lời chào."""
    raise NotImplementedError


@router.get("/{session_id}")
async def get_session(session_id: str, request: Request) -> SessionOut:
    """404 nếu không có phiên."""
    raise NotImplementedError


@router.post("/{session_id}/messages", status_code=202)
async def post_message(session_id: str, body: MessageIn, request: Request) -> dict:
    """Cần text hoặc action (thiếu cả hai -> 422). Gọi engine.handle. Trả {'accepted': True}."""
    raise NotImplementedError


@router.post("/{session_id}/files", status_code=202)
async def upload_files(session_id: str, files: list[UploadFile], request: Request) -> dict:
    """Kiểm đuôi (ALLOWED_UPLOAD_EXTS), kích thước, số file; lưu qua store.safe_path;
    gọi engine.handle(action='file_uploaded'). Sai -> 400."""
    raise NotImplementedError


@router.get("/{session_id}/export.zip")
async def download_export(session_id: str, request: Request) -> FileResponse:
    """Chỉ khi state DONE (khác -> 409)."""
    raise NotImplementedError
