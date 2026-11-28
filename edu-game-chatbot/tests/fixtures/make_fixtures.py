"""Sinh fixture tài liệu mẫu cho N1 (T09). Chạy: python tests/fixtures/make_fixtures.py"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).parent
SAMPLE_TEXT = "TODO: đoạn văn bài học mẫu tiếng Việt (vài trăm chữ)"


def make_txt(path: Path) -> None:
    """Ghi SAMPLE_TEXT ra .txt (utf-8)."""
    raise NotImplementedError


def make_md(path: Path) -> None:
    """Ghi bản markdown có tiêu đề."""
    raise NotImplementedError


def make_docx(path: Path) -> None:
    """python-docx: vài đoạn + 1 bảng 2x2."""
    raise NotImplementedError


def make_pdf(path: Path) -> None:
    """PDF 1 trang có chữ trích được (không thêm thư viện ngoài stack: tự viết PDF tối giản)."""
    raise NotImplementedError


def main() -> None:
    """Sinh cả 4 file vào HERE."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
