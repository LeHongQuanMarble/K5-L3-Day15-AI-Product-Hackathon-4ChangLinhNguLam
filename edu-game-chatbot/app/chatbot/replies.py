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

# ---- Câu chữ (SPEC §4) ----
GREETING = "Xin chào! Thầy/cô muốn tạo game học tập về nội dung gì?"
ASK_SOURCE = "Game học tập bắt buộc có bộ câu hỏi. Thầy/cô muốn lấy câu hỏi từ đâu?"
ASK_UPLOAD_QUESTIONS = "Thầy/cô vui lòng tải lên file bộ câu hỏi của mình (.json, .csv hoặc .xlsx)."
ASK_UPLOAD_DOCUMENTS = (
    "Thầy/cô vui lòng tải lên tài liệu (.pdf, .docx, .txt, .md; tối đa 10 MB/file, "
    "5 file) để mình tạo câu hỏi."
)
ASK_TOPIC = "Thầy/cô nhập chủ đề và số câu (mặc định 10):"
ASK_REVISION_TEXT = "Thầy/cô muốn chỉnh sửa điều gì? Hãy mô tả thay đổi mong muốn."
BUSY = "Mình đang xử lý yêu cầu trước đó, thầy/cô vui lòng chờ một chút nhé."
CANCELLED = "Đã huỷ yêu cầu. Thầy/cô có thể bắt đầu game mới bất cứ lúc nào."
NOT_UNDERSTOOD = "Mình chưa hiểu ý thầy/cô. Thầy/cô vui lòng chọn một nút bên dưới hoặc nhập lại yêu cầu."
SESSION_ENDED = "Phiên làm việc đã kết thúc. Thầy/cô hãy bắt đầu một phiên mới nhé."


def source_buttons() -> list[Button]:
    """3 nút nguồn câu hỏi."""
    return [
        Button(id=BTN_SOURCE_USER, label="Tôi có sẵn bộ câu hỏi"),
        Button(id=BTN_SOURCE_DOCUMENT, label="Tạo từ tài liệu của tôi"),
        Button(id=BTN_SOURCE_TOPIC, label="Tạo theo chủ đề"),
    ]


def question_approval_buttons() -> list[Button]:
    """[Đồng ý] [Tạo lại]."""
    return [
        Button(id=BTN_QB_APPROVE, label="Đồng ý"),
        Button(id=BTN_QB_REGENERATE, label="Tạo lại"),
    ]


def review_buttons(test_passed: bool) -> list[Button]:
    """Pass: [approve, revise, cancel]; fail: [revise, cancel]."""
    revise = Button(id=BTN_REVISE, label="Chỉnh sửa")
    cancel = Button(id=BTN_CANCEL, label="Huỷ")
    if test_passed:
        return [Button(id=BTN_APPROVE, label="Hài lòng — xuất file"), revise, cancel]
    return [revise, cancel]


def reject(reason: str) -> str:
    """Câu từ chối yêu cầu không phải game học tập + gợi ý ví dụ."""
    return (
        "Mình chỉ hỗ trợ tạo game học tập. "
        f"Yêu cầu này không có mục tiêu học tập vì {reason}. "
        "Thầy/cô có thể thử: 'Game ôn từ vựng tiếng Anh chủ đề động vật lớp 3'."
    )


def bank_invalid(errors: list[str]) -> str:
    """Báo file câu hỏi lỗi (tối đa 10 lỗi) + mời tải lại."""
    shown = errors[:10]
    lines = "\n".join(f"- {e}" for e in shown)
    more = f"\n(và {len(errors) - 10} lỗi khác)" if len(errors) > 10 else ""
    return (
        "File bộ câu hỏi có lỗi, thầy/cô vui lòng kiểm tra:\n"
        f"{lines}{more}\n"
        "Thầy/cô hãy sửa và tải lại file nhé."
    )


def bank_preview(preview: str) -> str:
    """Giới thiệu bộ câu hỏi để duyệt."""
    return f"Đây là bộ câu hỏi:\n{preview}\nThầy/cô đồng ý hay muốn tạo lại?"


def progress(node: str, detail: str = "") -> str:
    """Thông báo tiến độ, ví dụ 'Kiểm thử… (sửa lỗi 1/2)'."""
    names = {
        "questions": "Đang tạo bộ câu hỏi",
        "design": "Thiết kế game",
        "codegen": "Sinh HTML",
        "test": "Kiểm thử",
        "export": "Xuất file",
    }
    text = f"{names.get(node, node)}…"
    return f"{text} ({detail})" if detail else text


def review_intro(version_number: int, test_passed: bool, errors: list[str]) -> str:
    """Lời mời chơi thử (kèm cảnh báo khi test fail)."""
    text = f"Mời thầy/cô chơi thử phiên bản v{version_number}."
    if not test_passed:
        lines = "\n".join(f"- {e}" for e in errors[:10])
        text += (
            "\nLưu ý: game chưa vượt qua kiểm thử tự động, có thể còn lỗi:\n"
            f"{lines}\nThầy/cô có thể chỉnh sửa để mình sửa tiếp."
        )
    return text


def exported(title: str, version_number: int, warnings: list[str]) -> str:
    """Báo xuất thành công + MAIN đã tiếp nhận (+ cảnh báo webhook nếu có)."""
    text = f'Đã xuất game "{title}" (v{version_number}). MAIN đã tiếp nhận.'
    if warnings:
        text += "\nCảnh báo:\n" + "\n".join(f"- {w}" for w in warnings)
    return text


def failed(error: str) -> str:
    """Báo lỗi thân thiện + mời bấm Thử lại."""
    return f"Rất tiếc, đã có lỗi xảy ra: {error}\nThầy/cô bấm Thử lại để mình làm lại nhé."


def retry_button() -> Button:
    return Button(id=BTN_RETRY, label="Thử lại")


def fix_progress(attempt: int, max_attempts: int) -> str:
    return f"Đang sửa lỗi lần {attempt}/{max_attempts}…"


def document_error(detail: str) -> str:
    return f"Mình chưa đọc được tài liệu: {detail}"


def too_many_revisions(limit: int) -> str:
    """Vượt quá số vòng chỉnh sửa."""
    return f"Đã vượt quá {limit} lần chỉnh sửa cho game này. Thầy/cô hãy xuất file hoặc bắt đầu game mới nhé."
