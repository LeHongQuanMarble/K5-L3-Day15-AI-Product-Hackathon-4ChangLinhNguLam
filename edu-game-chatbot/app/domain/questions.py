"""Bộ câu hỏi: schema, validate, nạp file (docs/QUESTION_SCHEMA.md). (T03)"""

from __future__ import annotations

import csv
import json
from pathlib import Path

QUESTION_TYPES = ("mcq", "true_false", "fill_blank")
MIN_QUESTIONS = 3
MAX_QUESTIONS = 50
DEFAULT_POINTS = 10
CSV_HEADER = ("type", "question", "options", "answer", "explanation", "points")

# Mô tả schema đưa vào prompt question_gen / question_edit (viết theo QUESTION_SCHEMA §1–2)
QUESTION_SCHEMA_TEXT = """Định dạng JSON:
{"title": str, "subject": str, "grade": str, "questions": [ ... ]}
Số câu: từ 3 đến 50. Mỗi câu có:
- "id": chuỗi không rỗng, duy nhất (q1, q2, ...)
- "type": "mcq" | "true_false" | "fill_blank"
- "question": chuỗi không rỗng
- "explanation": chuỗi (mặc định "")
- "points": số nguyên > 0 (mặc định 10)
Theo từng loại:
- mcq: "options" gồm 2-6 chuỗi không rỗng, không trùng nhau; "answer" là số nguyên
  (chỉ số bắt đầu từ 0) trong [0, số options), không dùng true/false.
- true_false: "answer" là true hoặc false.
- fill_blank: "answer" là chuỗi không rỗng; "accept" (tuỳ chọn) là list chuỗi đáp án chấp nhận thêm.
Ví dụ:
{"id": "q1", "type": "mcq", "question": "1/2 + 1/4 = ?", "options": ["3/4", "2/6", "1/6", "2/4"],
 "answer": 0, "explanation": "Quy đồng", "points": 10}"""


class BankFileError(ValueError):
    """File bộ câu hỏi không hợp lệ; .errors là list lỗi tiếng Việt."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def _is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_str(v: object) -> bool:
    return isinstance(v, str) and bool(v.strip())


def validate_bank(bank: dict) -> list[str]:
    """Kiểm tra theo QUESTION_SCHEMA §2. Trả về list lỗi tiếng Việt; [] = hợp lệ."""
    if not isinstance(bank, dict):
        return ["Bộ câu hỏi phải là một đối tượng JSON."]
    qs = bank.get("questions")
    if not isinstance(qs, list):
        return ["Thiếu danh sách 'questions'."]
    errors: list[str] = []
    if len(qs) < MIN_QUESTIONS:
        errors.append(f"Cần ít nhất {MIN_QUESTIONS} câu hỏi (hiện có {len(qs)}).")
    elif len(qs) > MAX_QUESTIONS:
        errors.append(f"Tối đa {MAX_QUESTIONS} câu hỏi (hiện có {len(qs)}).")
    seen: set[str] = set()
    for i, q in enumerate(qs, 1):
        errors.extend(validate_question(q, i))
        qid = q.get("id") if isinstance(q, dict) else None
        if _is_str(qid):
            if qid in seen:
                errors.append(f"Câu {i}: id '{qid}' bị trùng.")
            seen.add(qid)
    return errors


def validate_question(q: dict, index: int) -> list[str]:
    """Kiểm tra 1 câu (index tính từ 1, dùng trong thông báo 'Câu <n>: ...')."""
    pre = f"Câu {index}: "
    if not isinstance(q, dict):
        return [pre + "phải là một đối tượng."]
    e: list[str] = []
    if not _is_str(q.get("id")):
        e.append(pre + "thiếu id (chuỗi không rỗng).")
    if not _is_str(q.get("question")):
        e.append(pre + "nội dung câu hỏi không được rỗng.")
    t = q.get("type")
    if t not in QUESTION_TYPES:
        e.append(pre + f"type phải là một trong {', '.join(QUESTION_TYPES)}.")
    elif t == "mcq":
        opts = q.get("options")
        a = q.get("answer")
        if not isinstance(opts, list) or not 2 <= len(opts) <= 6:
            e.append(pre + "mcq cần 2-6 phương án (options).")
        else:
            if not all(_is_str(o) for o in opts):
                e.append(pre + "các phương án phải là chuỗi không rỗng.")
            elif len(set(opts)) != len(opts):
                e.append(pre + "các phương án không được trùng nhau.")
            if not _is_int(a) or not 0 <= a < len(opts):
                e.append(pre + "đáp án mcq phải là số nguyên (không phải true/false) trong khoảng phương án.")
        if not isinstance(opts, list) and not _is_int(a):
            e.append(pre + "đáp án mcq phải là số nguyên.")
    elif t == "true_false":
        if not isinstance(q.get("answer"), bool):
            e.append(pre + "đáp án true_false phải là true hoặc false.")
    else:
        if not _is_str(q.get("answer")):
            e.append(pre + "đáp án fill_blank không được rỗng.")
        acc = q.get("accept")
        if acc is not None and (not isinstance(acc, list) or not all(isinstance(x, str) for x in acc)):
            e.append(pre + "accept phải là list chuỗi.")
    if "points" in q and (not _is_int(q["points"]) or q["points"] <= 0):
        e.append(pre + "points phải là số nguyên > 0.")
    if "explanation" in q and not isinstance(q["explanation"], str):
        e.append(pre + "explanation phải là chuỗi.")
    return e


def normalize_bank(bank: dict) -> dict:
    """Điền mặc định id/points/explanation/title. Không sửa nội dung câu hỏi/đáp án."""
    out = dict(bank)
    if not out.get("title"):
        out["title"] = "Bộ câu hỏi"
    qs = []
    for i, q in enumerate(bank.get("questions") or [], 1):
        if not isinstance(q, dict):
            qs.append(q)
            continue
        nq = dict(q)
        if not nq.get("id"):
            nq["id"] = f"q{i}"
        nq.setdefault("points", DEFAULT_POINTS)
        nq.setdefault("explanation", "")
        qs.append(nq)
    out["questions"] = qs
    return out


def max_score(bank: dict) -> int:
    """Tổng points của mọi câu."""
    return sum(q.get("points", DEFAULT_POINTS) for q in bank.get("questions", []))


def load_bank_file(path: Path) -> dict:
    """Nạp .json/.csv -> bank đã normalize. Đuôi khác hoặc lỗi -> BankFileError."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".json":
        bank = load_bank_json(path)
    elif ext == ".csv":
        bank = load_bank_csv(path)
    else:
        raise BankFileError([f"Định dạng '{ext}' không được hỗ trợ (chỉ .json hoặc .csv)."])
    bank = normalize_bank(bank)
    errors = validate_bank(bank)
    if errors:
        raise BankFileError(errors)
    return bank


def load_bank_json(path: Path) -> dict:
    """Nạp JSON (object hoặc list câu hỏi)."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError) as exc:
        raise BankFileError([f"Không đọc được file: {exc}"]) from exc
    except json.JSONDecodeError as exc:
        raise BankFileError([f"JSON không hợp lệ (dòng {exc.lineno}): {exc.msg}"]) from exc
    if isinstance(data, list):
        data = {"questions": data}
    if not isinstance(data, dict):
        raise BankFileError(["JSON phải là object hoặc list câu hỏi."])
    return data


def load_bank_csv(path: Path) -> dict:
    """Nạp CSV utf-8-sig; lỗi báo 'Dòng <n>: ...' (header là dòng 1)."""
    questions: list[dict] = []
    errors: list[str] = []
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            missing = [h for h in CSV_HEADER if h not in (reader.fieldnames or [])]
            if missing:
                raise BankFileError([f"Dòng 1: thiếu cột {', '.join(missing)}."])
            for row in reader:
                try:
                    questions.append(parse_csv_row(row, reader.line_num))
                except ValueError as exc:
                    errors.append(str(exc))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise BankFileError([f"Không đọc được file CSV: {exc}"]) from exc
    if errors:
        raise BankFileError(errors)
    return {"questions": questions}


_TRUE = {"true", "đúng", "1"}
_FALSE = {"false", "sai", "0"}


def parse_csv_row(row: dict[str, str], line_no: int) -> dict:
    """Chuyển 1 dòng CSV thành câu hỏi (mcq: A–F hoặc chỉ số; true_false: true/false/đúng/sai/1/0)."""
    pre = f"Dòng {line_no}: "

    def g(k: str) -> str:
        return (row.get(k) or "").strip()

    t = g("type").lower()
    if t not in QUESTION_TYPES:
        raise ValueError(pre + f"type '{t}' không hợp lệ.")
    if not g("question"):
        raise ValueError(pre + "nội dung câu hỏi không được rỗng.")
    q: dict = {"type": t, "question": g("question"), "explanation": g("explanation")}
    if g("points"):
        try:
            q["points"] = int(g("points"))
        except ValueError:
            raise ValueError(pre + "points phải là số nguyên.") from None
    ans = g("answer")
    if t == "mcq":
        q["options"] = [o.strip() for o in g("options").split("|")] if g("options") else []
        if len(ans) == 1 and ans.upper() in "ABCDEF":
            q["answer"] = "ABCDEF".index(ans.upper())
        else:
            try:
                q["answer"] = int(ans)
            except ValueError:
                raise ValueError(pre + "đáp án mcq phải là chữ cái A-F hoặc chỉ số.") from None
        if not 2 <= len(q["options"]) <= 6 or not 0 <= q["answer"] < len(q["options"]):
            raise ValueError(pre + "mcq cần 2-6 phương án và đáp án nằm trong khoảng đó.")
    elif t == "true_false":
        low = ans.lower()
        if low in _TRUE:
            q["answer"] = True
        elif low in _FALSE:
            q["answer"] = False
        else:
            raise ValueError(pre + "đáp án true_false phải là true/false/đúng/sai/1/0.")
    else:
        if not ans:
            raise ValueError(pre + "đáp án fill_blank không được rỗng.")
        q["answer"] = ans
    return q
