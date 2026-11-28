"""N5. Giáo viên chơi thử: dựng message có preview + nút. (T15)"""

from __future__ import annotations

from app.chatbot import replies
from app.core.models import Message, Session, Version

MAX_ERRORS_SHOWN = 8
MAX_ERROR_LEN = 200


def preview_url(session_id: str, version_number: int) -> str:
    """'/preview/{id}/v{n}'"""
    return f"/preview/{session_id}/v{version_number}"


def build_review_message(session: Session, version: Version) -> Message:
    """Pass: nút [approve, revise, cancel]. Fail: [revise, cancel] + tối đa MAX_ERRORS_SHOWN lỗi dễ hiểu."""
    passed = bool(version.test_passed)
    errors = [] if passed else humanize_errors(version.test_errors)
    return Message(
        role="bot",
        text=replies.review_intro(version.number, passed, errors),
        buttons=replies.review_buttons(passed),
        preview_url=preview_url(session.id, version.number),
    )


def humanize_errors(errors: list[str]) -> list[str]:
    """Rút gọn lỗi kỹ thuật thành câu dễ hiểu cho giáo viên: gọn, bỏ trùng, tối đa MAX_ERRORS_SHOWN."""
    out: list[str] = []
    for e in errors:
        line = " ".join(str(e).split())
        if len(line) > MAX_ERROR_LEN:
            line = line[: MAX_ERROR_LEN - 1] + "…"
        if line and line not in out:
            out.append(line)
        if len(out) >= MAX_ERRORS_SHOWN:
            break
    return out
