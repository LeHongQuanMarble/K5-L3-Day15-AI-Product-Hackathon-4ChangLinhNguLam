"""MỌI câu chữ tiếng Việt của bot nằm ở đây (SPEC §4). (T17)
Button id là cố định (engine + test dùng) — không đổi. Label/câu chữ: coder viết."""

from __future__ import annotations

from app.core.models import Button

# ---- Button id (cố định) ----
BTN_SOURCE_USER = "source_user"
BTN_SOURCE_DOCUMENT = "source_document"
BTN_SOURCE_TOPIC = "source_topic"
BTN_QB_APPROVE = "qb_approve"
BTN_QB_REGENERATE = "qb_regenerate"
BTN_APPROVE = "approve"
BTN_REVISE = "revise"
BTN_CANCEL = "cancel"
BTN_RETRY = "retry"
ACTION_FILE_UPLOADED = "file_uploaded"

# ---- Câu chữ (TODO: viết theo SPEC §4) ----
GREETING = "TODO"
ASK_SOURCE = "TODO"
ASK_UPLOAD_QUESTIONS = "TODO"
ASK_UPLOAD_DOCUMENTS = "TODO"
ASK_TOPIC = "TODO"
ASK_REVISION_TEXT = "TODO"
BUSY = "TODO"
CANCELLED = "TODO"
NOT_UNDERSTOOD = "TODO"
SESSION_ENDED = "TODO"


def source_buttons() -> list[Button]:
    """3 nút nguồn câu hỏi."""
    raise NotImplementedError


def question_approval_buttons() -> list[Button]:
    """[Đồng ý] [Tạo lại]."""
    raise NotImplementedError


def review_buttons(test_passed: bool) -> list[Button]:
    """Pass: [approve, revise, cancel]; fail: [revise, cancel]."""
    raise NotImplementedError


def reject(reason: str) -> str:
    """Câu từ chối yêu cầu không phải game học tập + gợi ý ví dụ."""
    raise NotImplementedError


def bank_invalid(errors: list[str]) -> str:
    """Báo file câu hỏi lỗi (tối đa 10 lỗi) + mời tải lại."""
    raise NotImplementedError


def bank_preview(preview: str) -> str:
    """Giới thiệu bộ câu hỏi để duyệt."""
    raise NotImplementedError


def progress(node: str, detail: str = "") -> str:
    """Thông báo tiến độ, ví dụ 'Kiểm thử… (sửa lỗi 1/2)'."""
    raise NotImplementedError


def review_intro(version_number: int, test_passed: bool, errors: list[str]) -> str:
    """Lời mời chơi thử (kèm cảnh báo khi test fail)."""
    raise NotImplementedError


def exported(title: str, version_number: int, warnings: list[str]) -> str:
    """Báo xuất thành công + MAIN đã tiếp nhận (+ cảnh báo webhook nếu có)."""
    raise NotImplementedError


def failed(error: str) -> str:
    """Báo lỗi thân thiện + mời bấm Thử lại."""
    raise NotImplementedError


def too_many_revisions(limit: int) -> str:
    """Vượt quá số vòng chỉnh sửa."""
    raise NotImplementedError
