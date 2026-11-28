"""SessionStore = Session Memory trong sơ đồ. Lưu sessions/<id>/memory.json. (T05)"""

from __future__ import annotations

import asyncio
import os
import re
from datetime import timedelta
from pathlib import Path

from .models import Message, Session, utcnow

_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_NAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\- ]*$")


class SessionStore:
    def __init__(self, root: Path) -> None:
        """root: thư mục chứa mọi phiên (settings.sessions_dir)."""
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, asyncio.Lock] = {}

    def _check_id(self, session_id: str) -> None:
        if not isinstance(session_id, str) or not _ID_RE.match(session_id):
            raise ValueError(f"session id không hợp lệ: {session_id!r}")

    def create(self) -> Session:
        """Tạo phiên mới, tạo thư mục, lưu lần đầu, trả về Session."""
        session = Session()
        self.session_dir(session.id)
        self.save(session)
        return session

    def get(self, session_id: str) -> Session:
        """Nạp phiên từ memory.json. Không tồn tại -> KeyError."""
        try:
            self._check_id(session_id)
        except ValueError:
            raise KeyError(session_id) from None
        path = self.root / session_id / "memory.json"
        if not path.is_file():
            raise KeyError(session_id)
        return Session.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, session: Session) -> None:
        """Cập nhật updated_at, ghi nguyên tử (.tmp rồi os.replace)."""
        now = utcnow()
        if now <= session.updated_at:
            now = session.updated_at + timedelta(microseconds=1)
        session.updated_at = now
        path = self.session_dir(session.id) / "memory.json"
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(session.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp, path)

    def exists(self, session_id: str) -> bool:
        """Phiên có tồn tại không."""
        try:
            self._check_id(session_id)
        except ValueError:
            return False
        return (self.root / session_id / "memory.json").is_file()

    def lock(self, session_id: str) -> asyncio.Lock:
        """Lock riêng cho từng phiên (tạo nếu chưa có)."""
        return self._locks.setdefault(session_id, asyncio.Lock())

    def session_dir(self, session_id: str) -> Path:
        """Thư mục của phiên (tạo nếu chưa có)."""
        self._check_id(session_id)
        d = self.root / session_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def version_dir(self, session_id: str, number: int) -> Path:
        """sessions/<id>/v<number>/ (tạo nếu chưa có)."""
        d = self.session_dir(session_id) / f"v{int(number)}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def safe_path(self, session_id: str, filename: str, subdir: str = "uploads") -> Path:
        """Đường dẫn an toàn trong thư mục phiên. Có '..', đường dẫn tuyệt đối, ký tự lạ -> ValueError."""
        if not filename or not _NAME_RE.match(filename) or ".." in filename:
            raise ValueError(f"tên file không hợp lệ: {filename!r}")
        if subdir and not _ID_RE.match(subdir):
            raise ValueError(f"subdir không hợp lệ: {subdir!r}")
        base = self.session_dir(session_id)
        if subdir:
            base = base / subdir
            base.mkdir(parents=True, exist_ok=True)
        base = base.resolve()
        path = (base / filename).resolve()
        if not path.is_relative_to(base):
            raise ValueError(f"đường dẫn thoát khỏi thư mục phiên: {filename!r}")
        return path

    def add_message(self, session: Session, message: Message) -> Message:
        """Thêm message vào session (chưa save)."""
        session.messages.append(message)
        return message

    def add_event(self, session: Session, node: str, text: str, **data: object) -> None:
        """Ghi một sự kiện nhật ký {at, node, text, ...} vào session (chưa save)."""
        session.events.append({"at": utcnow().isoformat(), "node": node, "text": text, **data})
