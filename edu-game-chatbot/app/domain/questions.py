"""Bộ câu hỏi: schema, validate, nạp file (docs/QUESTION_SCHEMA.md). (T03)"""

from __future__ import annotations

from pathlib import Path

QUESTION_TYPES = ("mcq", "true_false", "fill_blank")
MIN_QUESTIONS = 3
MAX_QUESTIONS = 50
DEFAULT_POINTS = 10
CSV_HEADER = ("type", "question", "options", "answer", "explanation", "points")

# Mô tả schema đưa vào prompt question_gen / question_edit (viết theo QUESTION_SCHEMA §1–2)
QUESTION_SCHEMA_TEXT = "TODO"


class BankFileError(ValueError):
    """File bộ câu hỏi không hợp lệ; .errors là list lỗi tiếng Việt."""

    def __init__(self, errors: list[str]) -> None:
        raise NotImplementedError


def validate_bank(bank: dict) -> list[str]:
    """Kiểm tra theo QUESTION_SCHEMA §2. Trả về list lỗi tiếng Việt; [] = hợp lệ."""
    raise NotImplementedError


def validate_question(q: dict, index: int) -> list[str]:
    """Kiểm tra 1 câu (index tính từ 1, dùng trong thông báo 'Câu <n>: ...')."""
    raise NotImplementedError


def normalize_bank(bank: dict) -> dict:
    """Điền mặc định id/points/explanation/title. Không sửa nội dung câu hỏi/đáp án."""
    raise NotImplementedError


def max_score(bank: dict) -> int:
    """Tổng points của mọi câu."""
    raise NotImplementedError


def load_bank_file(path: Path) -> dict:
    """Nạp .json/.csv -> bank đã normalize. Đuôi khác hoặc lỗi -> BankFileError."""
    raise NotImplementedError


def load_bank_json(path: Path) -> dict:
    """Nạp JSON (object hoặc list câu hỏi)."""
    raise NotImplementedError


def load_bank_csv(path: Path) -> dict:
    """Nạp CSV utf-8-sig; lỗi báo 'Dòng <n>: ...' (header là dòng 1)."""
    raise NotImplementedError


def parse_csv_row(row: dict[str, str], line_no: int) -> dict:
    """Chuyển 1 dòng CSV thành câu hỏi (mcq: A–F hoặc chỉ số; true_false: true/false/đúng/sai/1/0)."""
    raise NotImplementedError
