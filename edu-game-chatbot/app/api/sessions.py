"""REST API phiên chat (ARCHITECTURE §4). (T19)"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.chatbot import replies
from app.chatbot.engine import ChatEngine
from app.core.models import Session, State

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

ALLOWED_UPLOAD_EXTS = (".pdf", ".docx", ".txt", ".md", ".json", ".csv")


class MessageIn(BaseModel):
    text: str | None = None
    action: str | None = None


class SessionOut(BaseModel):
    id: str
    state: str
    messages: list[dict]


def _load(request: Request, session_id: str) -> Session:
    store = request.app.state.store
    if not store.exists(session_id):
        raise HTTPException(404, "Không tìm thấy phiên")
    return store.get(session_id)


def get_engine(request: Request) -> ChatEngine:
    """Lấy ChatEngine từ request.app.state.engine."""
    return request.app.state.engine


def to_session_out(session: Session) -> SessionOut:
    """Chuyển Session -> SessionOut (messages ở dạng model_dump(mode='json'))."""
    return SessionOut(
        id=session.id,
        state=session.state.value,
        messages=[m.model_dump(mode="json") for m in session.messages],
    )


@router.post("", status_code=201)
async def create_session(request: Request) -> SessionOut:
    """Tạo phiên + lời chào."""
    session = await get_engine(request).start_session()
    return to_session_out(session)


@router.get("/{session_id}")
async def get_session(session_id: str, request: Request) -> SessionOut:
    """404 nếu không có phiên."""
    return to_session_out(_load(request, session_id))


@router.post("/{session_id}/messages", status_code=202)
async def post_message(session_id: str, body: MessageIn, request: Request) -> dict:
    """Cần text hoặc action (thiếu cả hai -> 422). Gọi engine.handle. Trả {'accepted': True}."""
    if not body.text and not body.action:
        raise HTTPException(422, "Cần text hoặc action")
    _load(request, session_id)
    await get_engine(request).handle(session_id, text=body.text, action=body.action)
    return {"accepted": True}


@router.post("/{session_id}/files", status_code=202)
async def upload_files(session_id: str, files: list[UploadFile], request: Request) -> dict:
    """Kiểm đuôi (ALLOWED_UPLOAD_EXTS), kích thước, số file; lưu qua store.safe_path;
    gọi engine.handle(action='file_uploaded'). Sai -> 400."""
    session = _load(request, session_id)
    settings = request.app.state.settings
    store = request.app.state.store
    if not files:
        raise HTTPException(400, "Chưa chọn file")
    existing = len(list(store.safe_path(session_id, "x").parent.iterdir()))
    if existing + len(files) > settings.max_files_per_session:
        raise HTTPException(400, f"Tối đa {settings.max_files_per_session} file")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    staged: list[tuple[Path, bytes]] = []
    for f in files:
        name = f.filename or ""
        if Path(name).suffix.lower() not in ALLOWED_UPLOAD_EXTS:
            raise HTTPException(400, f"Định dạng không được hỗ trợ: {name}")
        try:
            path = store.safe_path(session_id, name)
        except ValueError:
            raise HTTPException(400, f"Tên file không hợp lệ: {name}") from None
        data = await f.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise HTTPException(400, f"File quá lớn (tối đa {settings.max_upload_mb}MB): {name}")
        staged.append((path, data))
    for path, data in staged:
        path.write_bytes(data)
    await get_engine(request).handle(session.id, action=replies.ACTION_FILE_UPLOADED)
    return {"accepted": True, "files": [p.name for p, _ in staged]}


@router.get("/{session_id}/export.zip")
async def download_export(session_id: str, request: Request) -> FileResponse:
    """Chỉ khi state DONE (khác -> 409)."""
    session = _load(request, session_id)
    if session.state != State.DONE or not session.exported_to:
        raise HTTPException(409, "Game chưa được xuất")
    zip_path = Path(session.exported_to) / "export.zip"
    if not zip_path.is_file():
        raise HTTPException(404, "Không tìm thấy file export")
    return FileResponse(zip_path, media_type="application/zip", filename=f"{session_id}.zip")
