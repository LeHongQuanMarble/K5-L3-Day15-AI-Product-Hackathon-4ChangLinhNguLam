"""N1. Đọc tài liệu: .pdf .docx .txt .md -> văn bản. (T09)"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED_EXTS = (".pdf", ".docx", ".txt", ".md")
DEFAULT_MAX_BYTES = 10 * 1024 * 1024


class DocumentError(ValueError):
    """Tài liệu không đọc được / sai định dạng / quá lớn."""


@dataclass
class DocResult:
    text: str
    docs: list[dict] = field(default_factory=list)  # [{name, path, chars}]
    warnings: list[str] = field(default_factory=list)


def read_documents(paths: list[Path], max_chars: int, max_bytes: int = DEFAULT_MAX_BYTES) -> DocResult:
    """Đọc lần lượt các file, ghép '### <tên>\\n<nội dung>', cắt tổng còn max_chars.
    Không đọc được chữ nào từ mọi file -> DocumentError."""
    parts: list[str] = []
    docs: list[dict] = []
    warnings: list[str] = []
    for p in paths:
        p = Path(p)
        text = read_file(p, max_bytes).strip()
        if not text:
            if p.suffix.lower() == ".pdf":
                warnings.append(f"{p.name}: không trích được chữ, có thể là file scan")
            else:
                warnings.append(f"{p.name}: file không có nội dung")
            continue
        docs.append({"name": p.name, "path": str(p), "chars": len(text)})
        parts.append(f"### {p.name}\n{text}")
    if not parts:
        raise DocumentError("Không đọc được nội dung nào từ tài liệu đã tải lên")
    full = "\n\n".join(parts)
    if len(full) > max_chars:
        full = full[:max_chars]
        warnings.append(f"Tài liệu quá dài, đã cắt còn {max_chars} ký tự")
    return DocResult(text=full, docs=docs, warnings=warnings)


def read_file(path: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> str:
    """Kiểm đuôi + kích thước rồi gọi reader tương ứng."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTS:
        raise DocumentError(f"{path.name}: định dạng {ext or '(không đuôi)'} không được hỗ trợ")
    if not path.is_file():
        raise DocumentError(f"{path.name}: không tìm thấy file")
    if path.stat().st_size > max_bytes:
        raise DocumentError(f"{path.name}: file quá lớn (tối đa {max_bytes // (1024 * 1024)} MB)")
    try:
        if ext == ".pdf":
            return read_pdf(path)
        if ext == ".docx":
            return read_docx(path)
        return read_text(path)
    except DocumentError:
        raise
    except Exception as e:  # file hỏng
        raise DocumentError(f"{path.name}: không đọc được file ({e})") from e


def read_pdf(path: Path) -> str:
    """pypdf: nối text các trang."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def read_docx(path: Path) -> str:
    """python-docx: đoạn văn + bảng (ô nối bằng ' | ')."""
    from docx import Document

    doc = Document(str(path))
    lines = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            lines.append(" | ".join(c.text.strip() for c in row.cells))
    return "\n".join(lines)


def read_text(path: Path) -> str:
    """utf-8, lỗi thì thử cp1258 rồi latin-1."""
    data = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1258"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")
