"""N1b. Bộ câu hỏi: nạp từ người dùng / AI tạo từ tài liệu / AI tạo theo chủ đề / sửa. (T10)"""

from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.core.llm import LLMClient
from app.core.models import Source

MAX_GEN_RETRIES = 2


class QuestionGenError(RuntimeError):
    """AI không tạo được bộ câu hỏi hợp lệ sau MAX_GEN_RETRIES lần sửa."""


def from_user_file(path: Path) -> dict:
    """load_bank_file + validate_bank; lỗi -> BankFileError (giữ nguyên nội dung giáo viên)."""
    raise NotImplementedError


async def generate(
    llm: LLMClient,
    settings: Settings,
    *,
    source: Source,
    request: str,
    num_questions: int,
    doc_text: str = "",
    topic: str = "",
    feedback: str = "",
) -> dict:
    """Prompt 'question_gen'. Bank sai / sai số câu -> gửi lại kèm lỗi, tối đa MAX_GEN_RETRIES; rồi QuestionGenError.
    source=DOCUMENT: chỉ dùng doc_text. source=TOPIC: dùng topic."""
    raise NotImplementedError


def build_gen_prompt(
    *,
    source: Source,
    request: str,
    num_questions: int,
    doc_text: str,
    topic: str,
    feedback: str,
    previous_errors: list[str],
) -> str:
    """Tạo nội dung user message cho question_gen."""
    raise NotImplementedError


async def edit(llm: LLMClient, settings: Settings, bank: dict, instruction: str, source: Source) -> dict:
    """Prompt 'question_edit' -> bank mới hợp lệ. source=USER: các câu không bị nhắc tới phải giữ nguyên (so theo id)."""
    raise NotImplementedError


def preview_text(bank: dict, limit: int = 5) -> str:
    """Tóm tắt: '<title> — N câu, tổng X điểm' + limit câu đầu."""
    raise NotImplementedError
