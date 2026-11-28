from pathlib import Path

import pytest

from app.nodes.n1_read_docs import DocumentError, read_documents, read_file

FIX = Path(__file__).parent.parent / "fixtures"


def test_txt_md():
    assert "phép cộng" in read_file(FIX / "sample.txt").lower()
    assert "Phép cộng và trừ" in read_file(FIX / "sample.md")


def test_docx_includes_table():
    t = read_file(FIX / "sample.docx")
    assert "Phép cộng là gộp" in t
    assert "7 + 5 | 12" in t


def test_pdf_text():
    assert "Phep cong" in read_file(FIX / "sample.pdf")


def test_all_four_combined():
    r = read_documents([FIX / f"sample.{e}" for e in ("txt", "md", "docx", "pdf")], 100000)
    assert [d["name"] for d in r.docs] == ["sample.txt", "sample.md", "sample.docx", "sample.pdf"]
    assert r.text.startswith("### sample.txt\n")
    assert r.warnings == []


def test_bad_ext(tmp_path):
    f = tmp_path / "a.exe"
    f.write_text("x")
    with pytest.raises(DocumentError):
        read_documents([f], 1000)


def test_too_big(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x" * 100)
    with pytest.raises(DocumentError):
        read_documents([f], 1000, max_bytes=50)


def test_truncate():
    r = read_documents([FIX / "sample.txt"], 50)
    assert len(r.text) == 50
    assert r.warnings


def test_cp1258_fallback(tmp_path):
    f = tmp_path / "v.txt"
    f.write_bytes("Bà Nà".encode("cp1258"))
    assert read_file(f) == "Bà Nà"


def test_empty_pdf_scan_warning(tmp_path):
    from pypdf import PdfWriter

    blank = tmp_path / "scan.pdf"
    w = PdfWriter()
    w.add_blank_page(100, 100)
    with blank.open("wb") as fh:
        w.write(fh)
    r = read_documents([blank, FIX / "sample.txt"], 1000)
    assert any("scan" in x for x in r.warnings)
    with pytest.raises(DocumentError):
        read_documents([blank], 1000)
