"""Nhập nhanh bộ đề từ Excel (.xlsx), CSV hoặc văn bản → các dòng theo mẫu của AI Lab:  Câu hỏi | Đáp án A | Đáp án B | =B
Chỉ dùng thư viện chuẩn (zipfile + xml). Không ghi gì vào DB: trả về nội dung để giáo viên xem lại rồi mới lưu."""
import base64
import csv
import io
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

from store import Err

MAX_QUESTIONS = 200
MAX_UNZIPPED = 20 * 1024 * 1024
KEYS = "ABCD"
TRUE_WORDS = ("đúng", "dung", "true", "t", "đ")
FALSE_WORDS = ("sai", "false", "f", "s")
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _fold(s):
    s = unicodedata.normalize("NFD", str(s).lower().replace("đ", "d"))
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn").strip()


def _clean(s):
    s = " ".join(str(s if s is not None else "").split())
    return s.replace("|", "/").lstrip("= ").strip()


def _line(q, opts, answer):
    """Ghép một dòng đúng mẫu hoặc ném ValueError với lý do dễ hiểu."""
    q = _clean(q)
    if not q:
        raise ValueError("thiếu nội dung câu hỏi")
    opts = [_clean(o) for o in opts if _clean(o)]
    a = _clean(answer)
    if not a:
        raise ValueError("thiếu đáp án đúng")
    if not opts:
        k = a.lower()
        if k in TRUE_WORDS:
            return q + " | =Đúng"
        if k in FALSE_WORDS:
            return q + " | =Sai"
        raise ValueError("câu không có đáp án A–D thì đáp án phải là Đúng hoặc Sai")
    if len(opts) < 2:
        raise ValueError("cần ít nhất 2 đáp án")
    if len(opts) > 4:
        raise ValueError("tối đa 4 đáp án (A–D)")
    keys = KEYS[:len(opts)]
    m = re.match(r"^(?:đáp án|dap an|đa|da)?\s*[:\-]?\s*([A-Da-d1-4])\s*[\.\)]?$", a, re.I)
    letter = None
    if m:
        letter = m.group(1).upper()
        if letter.isdigit():
            letter = KEYS[int(letter) - 1]
    else:
        for i, o in enumerate(opts):
            if _fold(o) == _fold(a):
                letter = keys[i]
                break
    if letter is None or letter not in keys:
        raise ValueError("đáp án đúng phải là một trong %s (hoặc ghi đúng nội dung đáp án)" % ", ".join(keys))
    return "%s | %s | =%s" % (q, " | ".join(opts), letter)


# ---------- văn bản ----------
OPT = re.compile(r"^\s*(\*)?\s*\(?([A-Da-d])[\.\):]\s*(.+?)\s*(\(\*\)|\*)?\s*$")
ANS = re.compile(r"^\s*(?:đáp án(?: đúng)?|dap an(?: dung)?|đa|answer|key)\s*[:\-]?\s*(.+?)\s*$", re.I)
QNUM = re.compile(r"^\s*(?:câu|cau|question|q)?\s*\d+\s*[\.\):\-]\s*", re.I)


def from_text(text):
    """Trả (các dòng hợp lệ, danh sách lỗi). Hiểu cả dòng có dấu | lẫn dạng soạn thường ngày (1. Câu hỏi / A. … / Đáp án: B)."""
    lines, errors = [], []
    raw = text.splitlines()
    if any("|" in l for l in raw):
        for n, l in enumerate(raw, 1):
            if not l.strip():
                continue
            try:
                parts = [p.strip() for p in l.split("|")]
                if len(parts) < 2 or not parts[-1].startswith("=") or not parts[0]:
                    raise ValueError("viết theo mẫu  Câu hỏi | Đáp án A | Đáp án B | =B")
                a = parts[-1][1:].strip()
                lines.append(_line(parts[0], parts[1:-1], a))
            except ValueError as e:
                errors.append({"line": n, "error": str(e)})
        return lines, errors
    cur = None

    def flush():
        nonlocal cur
        if cur is None:
            return
        try:
            lines.append(_line(" ".join(cur["q"]), [o[1] for o in cur["opts"]], cur["ans"] or ""))
        except ValueError as e:
            errors.append({"line": cur["n"], "error": str(e)})
        cur = None

    for n, l in enumerate(raw, 1):
        if not l.strip():
            continue
        mo, ma = OPT.match(l), ANS.match(l)
        if cur is not None and mo and (cur["q"]):
            letter = mo.group(2).upper()
            cur["opts"].append((letter, mo.group(3)))
            if mo.group(1) or mo.group(4):
                cur["ans"] = letter
        elif cur is not None and ma:
            cur["ans"] = ma.group(1)
        else:
            body = QNUM.sub("", l, count=1)
            if cur is not None and not cur["opts"] and cur["ans"] is None and not QNUM.match(l):
                cur["q"].append(body)  # câu hỏi nhiều dòng
            else:
                flush()
                cur = {"n": n, "q": [body], "opts": [], "ans": None}
    flush()
    return lines, errors


# ---------- bảng (Excel / CSV) ----------
HEAD_Q = ("cau hoi", "question", "noi dung", "cau")
HEAD_A = ("dap an dung", "dap an", "answer", "key", "da")


def from_rows(rows):
    rows = [[("" if c is None else str(c)).strip() for c in r] for r in rows]
    start = 0
    qi, oi, ai = 0, None, None
    if rows:
        f = [_fold(c) for c in rows[0]]
        if any(c in HEAD_Q or c.startswith(HEAD_Q) for c in f) or any(c.startswith(("dap an", "answer")) for c in f):
            start = 1
            qi = next((i for i, c in enumerate(f) if c.startswith(HEAD_Q)), 0)
            opts = {}
            for i, c in enumerate(f):
                m = re.match(r"^(?:dap an|phuong an|lua chon|option)?\s*([a-d])$", c)
                if m:
                    opts[m.group(1).upper()] = i
            if opts:
                oi = [opts[k] for k in KEYS if k in opts]
            ai = next((i for i, c in enumerate(f) if (c in HEAD_A or c.startswith(("dap an dung", "answer", "key"))) and i not in (oi or [])), None)
    lines, errors = [], []
    for n, r in enumerate(rows[start:], start + 1):
        if not any(r):
            continue
        try:
            if oi is not None and ai is not None:
                q, opts, ans = r[qi] if qi < len(r) else "", [r[i] if i < len(r) else "" for i in oi], r[ai] if ai < len(r) else ""
            else:
                cells = list(r)
                if len(cells) > 2 and re.fullmatch(r"\d+[\.\)]?", cells[0]):
                    cells = cells[1:]  # cột STT
                while cells and not cells[-1]:
                    cells.pop()
                if len(cells) < 2:
                    raise ValueError("thiếu đáp án đúng ở cột cuối")
                q, opts, ans = cells[0], cells[1:-1], cells[-1]
            lines.append(_line(q, opts, ans))
        except ValueError as e:
            errors.append({"line": n, "error": str(e)})
    return lines, errors


def _col(ref):
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def xlsx_rows(data):
    if not data[:2] == b"PK":
        raise Err(400, "import", "Đây không phải tệp .xlsx. Hãy lưu lại từ Excel dưới dạng .xlsx hoặc .csv.")
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise Err(400, "import", "Không đọc được tệp Excel (tệp hỏng hoặc có mật khẩu).")
    if sum(i.file_size for i in z.infolist()) > MAX_UNZIPPED:
        raise Err(413, "import", "Tệp Excel quá lớn.")

    def load(name):
        b = z.read(name)
        if b"<!DOCTYPE" in b or b"<!ENTITY" in b:
            raise Err(400, "import", "Tệp Excel có cấu trúc không hợp lệ.")
        return ET.fromstring(b)
    names = z.namelist()
    sheets = sorted((n for n in names if re.match(r"^xl/worksheets/sheet\d+\.xml$", n)), key=lambda n: int(re.findall(r"\d+", n)[-1]))
    if not sheets:
        raise Err(400, "import", "Không tìm thấy trang tính trong tệp Excel.")
    shared = []
    if "xl/sharedStrings.xml" in names:
        for si in load("xl/sharedStrings.xml").findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    rows = []
    for row in load(sheets[0]).iter("{%s}row" % NS["m"]):
        cells = {}
        for c in row.findall("m:c", NS):
            t = c.get("t")
            if t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
            else:
                v = c.find("m:v", NS)
                val = v.text if v is not None and v.text is not None else ""
                if t == "s" and val.isdigit() and int(val) < len(shared):
                    val = shared[int(val)]
                elif t is None and val.endswith(".0"):
                    val = val[:-2]
            if val != "":
                cells[_col(c.get("r") or "A1")] = val
        rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
    return rows


def csv_rows(text):
    sample = text[:4000]
    delim = max(",;\t", key=sample.count)
    return list(csv.reader(io.StringIO(text), delimiter=delim))


def decode(b):
    for enc in ("utf-8-sig", "utf-16", "cp1258", "cp1252"):
        try:
            return b.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise Err(400, "import", "Không đọc được bảng mã của tệp. Hãy lưu lại dưới dạng UTF-8.")


def run(d):
    """d: {"filename": str, "data": base64} hoặc {"text": str}. Trả {"content","count","errors"}."""
    if isinstance(d.get("data"), str):
        try:
            b = base64.b64decode(d["data"], validate=False)
        except ValueError:
            raise Err(400, "import", "Tệp tải lên không hợp lệ.")
        name = str(d.get("filename") or "").lower()
        if name.endswith((".xlsx", ".xlsm")) or b[:2] == b"PK":
            lines, errors = from_rows(xlsx_rows(b))
        elif name.endswith(".xls"):
            raise Err(400, "import", "Chưa đọc được .xls cũ. Trong Excel chọn Lưu thành → .xlsx hoặc .csv.")
        elif name.endswith((".csv", ".tsv")):
            lines, errors = from_rows(csv_rows(decode(b)))
        else:
            lines, errors = from_text(decode(b))
    elif isinstance(d.get("text"), str):
        lines, errors = from_text(d["text"])
    else:
        raise Err(400, "import", "Chọn tệp hoặc dán văn bản để nhập.")
    if len(lines) > MAX_QUESTIONS:
        errors.append({"line": 0, "error": "Chỉ lấy %d câu đầu (giới hạn của một bộ đề)." % MAX_QUESTIONS})
        lines = lines[:MAX_QUESTIONS]
    return {"content": "\n".join(lines), "count": len(lines), "errors": errors[:50], "error_count": len(errors)}
