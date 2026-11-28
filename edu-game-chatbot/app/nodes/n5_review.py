"""N5. Giáo viên chơi thử: dựng message có preview + nút. (T15)"""

from __future__ import annotations

from app.core.models import Message, Session, Version

MAX_ERRORS_SHOWN = 8


def preview_url(session_id: str, version_number: int) -> str:
    """'/preview/{id}/v{n}'"""
    raise NotImplementedError


def build_review_message(session: Session, version: Version) -> Message:
    """Pass: nút [approve, revise, cancel]. Fail: [revise, cancel] + tối đa MAX_ERRORS_SHOWN lỗi dễ hiểu."""
    raise NotImplementedError


def humanize_errors(errors: list[str]) -> list[str]:
    """Rút gọn lỗi kỹ thuật thành câu dễ hiểu cho giáo viên."""
    raise NotImplementedError
