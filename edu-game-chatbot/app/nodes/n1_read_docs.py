"""N1. Đọc tài liệu: .pdf .docx .txt .md -> văn bản. (T09)"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED_EXTS = (".pdf", ".docx", ".txt", ".md")


class DocumentError(ValueError):
    """Tài liệu không đọc được / sai định dạng / quá lớn."""


@dataclass
class DocResult:
    text: str
    docs: list[dict] = field(default_factory=list)  # [{name, path, chars}]
    warnings: list[str] = field(default_factory=list)


def read_documents(paths: list[Path], max_chars: int, max_bytes: int) -> DocResult:
    """Đọc lần lượt các file, ghép '### <tên>\\n<nội dung>', cắt tổng còn max_chars.
    Không đọc được chữ nào từ mọi file -> DocumentError."""
    raise NotImplementedError


def read_file(path: Path, max_bytes: int) -> str:
    """Kiểm đuôi + kích thước rồi gọi reader tương ứng."""
    raise NotImplementedError


def read_pdf(path: Path) -> str:
    """pypdf: nối text các trang."""
    raise NotImplementedError


def read_docx(path: Path) -> str:
    """python-docx: đoạn văn + bảng (ô nối bằng ' | ')."""
    raise NotImplementedError


def read_text(path: Path) -> str:
    """utf-8, lỗi thì thử cp1258 rồi latin-1."""
    raise NotImplementedError
