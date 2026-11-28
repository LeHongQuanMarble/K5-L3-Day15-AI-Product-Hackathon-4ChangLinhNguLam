"""SessionStore = Session Memory trong sơ đồ. Lưu sessions/<id>/memory.json. (T05)"""

from __future__ import annotations

import asyncio
from pathlib import Path

from .models import Message, Session


class SessionStore:
    def __init__(self, root: Path) -> None:
        """root: thư mục chứa mọi phiên (settings.sessions_dir)."""
        raise NotImplementedError

    def create(self) -> Session:
        """Tạo phiên mới, tạo thư mục, lưu lần đầu, trả về Session."""
        raise NotImplementedError

    def get(self, session_id: str) -> Session:
        """Nạp phiên từ memory.json. Không tồn tại -> KeyError."""
        raise NotImplementedError

    def save(self, session: Session) -> None:
        """Cập nhật updated_at, ghi nguyên tử (.tmp rồi os.replace)."""
        raise NotImplementedError

    def exists(self, session_id: str) -> bool:
        """Phiên có tồn tại không."""
        raise NotImplementedError

    def lock(self, session_id: str) -> asyncio.Lock:
        """Lock riêng cho từng phiên (tạo nếu chưa có)."""
        raise NotImplementedError

    def session_dir(self, session_id: str) -> Path:
        """Thư mục của phiên (tạo nếu chưa có)."""
        raise NotImplementedError

    def version_dir(self, session_id: str, number: int) -> Path:
        """sessions/<id>/v<number>/ (tạo nếu chưa có)."""
        raise NotImplementedError

    def safe_path(self, session_id: str, filename: str, subdir: str = "uploads") -> Path:
        """Đường dẫn an toàn trong thư mục phiên. Có '..', đường dẫn tuyệt đối, ký tự lạ -> ValueError."""
        raise NotImplementedError

    def add_message(self, session: Session, message: Message) -> Message:
        """Thêm message vào session (chưa save)."""
        raise NotImplementedError

    def add_event(self, session: Session, node: str, text: str, **data: object) -> None:
        """Ghi một sự kiện nhật ký {at, node, text, ...} vào session (chưa save)."""
        raise NotImplementedError
