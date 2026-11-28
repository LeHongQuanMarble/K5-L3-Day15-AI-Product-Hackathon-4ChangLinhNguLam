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
# Yêu cầu game (F01)
BTN_GP_QUIZ = "gp_quiz"
BTN_GP_RACE = "gp_race"
BTN_GP_TARGET = "gp_target"
BTN_GP_MATCH = "gp_match"
BTN_GP_ADVENTURE = "gp_adventure"
BTN_GP_SUGGEST = "gp_suggest"
BTN_CTL_MOUSE = "ctl_mouse"
BTN_CTL_KEYBOARD = "ctl_keyboard"
BTN_CTL_MOTION = "ctl_motion"
BTN_CTL_VOICE = "ctl_voice"
BTN_VIS_CARTOON = "vis_cartoon"
BTN_VIS_SPACE = "vis_space"
BTN_VIS_NATURE = "vis_nature"
BTN_VIS_MINIMAL = "vis_minimal"
BTN_VIS_RETRO = "vis_retro"
# nút điều khiển -> mã điều khiển (mô tả tự do -> "custom")
CONTROLS_CODES = {
    BTN_CTL_MOUSE: "mouse",
    BTN_CTL_KEYBOARD: "keyboard",
    BTN_CTL_MOTION: "motion",
    BTN_CTL_VOICE: "voice",
}
CONTROLS_CUSTOM = "custom"
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
ASK_GAMEPLAY = (
    "Bộ câu hỏi đã sẵn sàng. Thầy/cô muốn học sinh chơi theo cách nào? "
    "(Chọn một nút hoặc tự mô tả cách chơi.)"
)
ASK_CONTROLS = (
    "Học sinh điều khiển game bằng gì? (Chọn một nút hoặc tự mô tả, ví dụ: dùng phím mũi tên và chuột.)"
)
ASK_VISUAL = (
    "Thầy/cô muốn giao diện game trông thế nào? Chọn một phong cách hoặc tự mô tả "
    "màu sắc, nhân vật, bối cảnh (ví dụ: nền xanh biển, nhân vật cá heo)."
)


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


def gameplay_buttons() -> list[Button]:
    """6 nút cách chơi."""
    return [
        Button(id=BTN_GP_QUIZ, label="Trả lời nhanh (trắc nghiệm)"),
        Button(id=BTN_GP_RACE, label="Đua về đích / vượt chướng ngại"),
        Button(id=BTN_GP_TARGET, label="Chọn mục tiêu / bắn bóng"),
        Button(id=BTN_GP_MATCH, label="Ghép cặp / kéo thả"),
        Button(id=BTN_GP_ADVENTURE, label="Phiêu lưu qua từng màn"),
        Button(id=BTN_GP_SUGGEST, label="Để trợ lý gợi ý"),
    ]


def controls_buttons() -> list[Button]:
    """4 nút cách điều khiển."""
    return [
        Button(id=BTN_CTL_MOUSE, label="Chuột / chạm màn hình"),
        Button(id=BTN_CTL_KEYBOARD, label="Bàn phím"),
        Button(id=BTN_CTL_MOTION, label="Cử động cơ thể (camera)"),
        Button(id=BTN_CTL_VOICE, label="Âm thanh / giọng nói (micro)"),
    ]


def visual_buttons() -> list[Button]:
    """5 nút phong cách giao diện."""
    return [
        Button(id=BTN_VIS_CARTOON, label="Hoạt hình tươi sáng"),
        Button(id=BTN_VIS_SPACE, label="Vũ trụ / khoa học"),
        Button(id=BTN_VIS_NATURE, label="Thiên nhiên"),
        Button(id=BTN_VIS_MINIMAL, label="Tối giản, dễ đọc"),
        Button(id=BTN_VIS_RETRO, label="Pixel cổ điển"),
    ]


def requirements_summary(
    num_questions: int, max_score: int, gameplay: str, controls: str, visual: str
) -> str:
    """Tóm tắt yêu cầu game trước khi bắt đầu tạo."""
    return (
        "Mình đã có đủ thông tin để tạo game:\n"
        f"- Bộ câu hỏi: {num_questions} câu, tổng {max_score} điểm\n"
        f"- Cách chơi: {gameplay}\n"
        f"- Điều khiển: {controls}\n"
        f"- Giao diện: {visual}\n"
        "Mình bắt đầu thiết kế và tạo game ngay đây."
    )


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
