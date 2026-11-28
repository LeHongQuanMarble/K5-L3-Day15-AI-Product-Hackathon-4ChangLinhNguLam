"""Sinh fixture tài liệu mẫu cho N1 (T09). Chạy: python tests/fixtures/make_fixtures.py"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).parent
SAMPLE_TEXT = (
    "Bài học: Phép cộng và phép trừ trong phạm vi 20. "
    "Phép cộng là gộp hai nhóm đồ vật lại với nhau. "
    "Ví dụ: 7 + 5 = 12. Phép trừ là bớt đi một số đồ vật. Ví dụ: 15 - 8 = 7."
)
PDF_LINE = "Bai hoc: Phep cong va phep tru trong pham vi 20. 7 + 5 = 12."


def make_txt(path: Path) -> None:
    """Ghi SAMPLE_TEXT ra .txt (utf-8)."""
    path.write_text(SAMPLE_TEXT, encoding="utf-8")


def make_md(path: Path) -> None:
    """Ghi bản markdown có tiêu đề."""
    path.write_text(f"# Phép cộng và trừ\n\n{SAMPLE_TEXT}\n", encoding="utf-8")


def make_docx(path: Path) -> None:
    """python-docx: vài đoạn + 1 bảng 2x2."""
    from docx import Document

    doc = Document()
    doc.add_heading("Phép cộng và trừ", level=1)
    doc.add_paragraph(SAMPLE_TEXT)
    table = doc.add_table(rows=2, cols=2)
    for r, row in enumerate((("Phép tính", "Kết quả"), ("7 + 5", "12"))):
        for c, val in enumerate(row):
            table.cell(r, c).text = val
    doc.save(str(path))


def make_pdf(path: Path) -> None:
    """PDF 1 trang có chữ trích được (không thêm thư viện ngoài stack: tự viết PDF tối giản)."""
    stream = f"BT /F1 12 Tf 50 750 Td ({PDF_LINE}) Tj ET".encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objs) + 1,
        xref,
    )
    path.write_bytes(bytes(out))


def main() -> None:
    """Sinh cả 4 file vào HERE."""
    make_txt(HERE / "sample.txt")
    make_md(HERE / "sample.md")
    make_docx(HERE / "sample.docx")
    make_pdf(HERE / "sample.pdf")


if __name__ == "__main__":
    main()
