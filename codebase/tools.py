"""Công cụ của bài toán — NHÓM VIẾT. Điền ở guide bước 2.2 (thiết kế) và 3.2 (code).

Mỗi công cụ là một hàm Python có @tool. Docstring ghi đúng 4 ý như sơ đồ ở spec.md §4:
    tên · input · output · có tác động ra ngoài không (gửi tin, sửa dữ liệu, chấm điểm…)
Khung tự ghi mỗi lần gọi công cụ vào trace (tên, input, output rút gọn, thời gian, lỗi).

Lát cắt của nhóm: giáo viên mô tả game → AI viết một file trình chơi HTML → người duyệt. Luật kiểm của AI Lab (hợp đồng
khối jl-camera + quét cờ cảnh báo) nằm ở ailab/contract.py; công cụ dưới đây gọi lại đúng luật đó, không chép lại.
Công cụ có tác động ra ngoài: KHÔNG tự làm. Ở đây không có công cụ nào lưu, gửi hay chấm điểm: lưu game là việc của
người dùng bấm Chấp nhận trong AI Lab (ailab/server.py), rồi Admin duyệt.
"""
import os
import sys

from tracing import tool, TOOLS  # noqa: F401  (TOOLS: danh sách công cụ đã đăng ký, dùng khi viết vòng lặp agent)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ailab"))
import composer  # noqa: E402  (ailab/composer.py — T12)
import contract  # noqa: E402  (ailab/contract.py)
import store  # noqa: E402  (ailab/store.py)
from chatbot import exams as chatbot_exams  # noqa: E402  (ailab/chatbot/exams.py)


@tool
def check_game(html: str) -> dict:
    """check_game — kiểm một file trình chơi HTML do AI viết.
    Input: html (str), toàn bộ file. Output: {"ok": bool, "error": str hoặc None, "name": str, "flags": [{"code","label","reason","line","excerpt"}]}.
    ok=False khi vi phạm hợp đồng (thiếu hoặc sai khối jl-camera, quá 2 MB…); flags là câu hỏi cho người duyệt, không phải lời từ chối.
    Không tác động ra ngoài: chỉ đọc, không lưu gì."""
    manifest, err = contract.parse(html or "")
    if err:
        return {"ok": False, "error": err[1], "name": "", "flags": []}
    return {"ok": True, "error": None, "name": manifest["name"], "flags": contract.scan(html)}


def _db_missing_error():
    """Trả thông báo lỗi nếu SQLite DB chưa tồn tại (tránh tạo file DB rỗng khi đọc)."""
    if not os.path.exists(store.DB_PATH):
        return "Catalog chưa khởi tạo. Chạy `bash scripts/staging.sh all` trước khi dùng tools."
    return None


@tool
def list_players(kind: str = None, questions: str = None, name_contains: str = None, limit: int = 50) -> dict:
    """list_players — tra cứu Player có sẵn trong Catalog để ưu tiên nhánh REUSE.
    Input: kind (str|None) lọc theo kinds trong manifest (vd 'hands'), questions (str|None) lọc 'exam'/'texts',
           name_contains (str|None), limit (int, 1–100).
    Output: {"ok": bool, "players": [{"id","name","kinds","inputs","questions","content","status"}], "error": str|None}.
    Không tác động ra ngoài: chỉ đọc Catalog; không lưu, không sửa, không xuất bản."""
    db_err = _db_missing_error()
    if db_err:
        return {"ok": False, "players": [], "error": db_err}
    try:
        snap = composer.catalog_snapshot()
    except composer.ComposerError as exc:
        return {"ok": False, "players": [], "error": str(exc)}
    try:
        cap = max(1, min(100, int(limit)))
    except (TypeError, ValueError):
        cap = 50
    out = []
    for p in snap["players"]:
        if kind and kind not in (p.get("kinds") or []):
            continue
        if questions:
            actual = p.get("questions") or (p.get("content") or {}).get("kind")
            if actual != questions:
                continue
        if name_contains and name_contains.strip().lower() not in (p["name"] or "").lower():
            continue
        out.append({k: p.get(k) for k in ("id", "name", "kinds", "inputs", "questions", "content", "status")})
        if len(out) >= cap:
            break
    return {"ok": True, "players": out, "error": None}


@tool
def get_player(player_id: int) -> dict:
    """get_player — lấy HTML gốc và manifest của một Player theo ID thật trong Catalog.
    Input: player_id (int), ID có trong Catalog; không đoán ID.
    Output: {"ok": bool, "player": {"id","name","manifest","html"} hoặc None, "error": str|None}.
    Không tác động ra ngoài: chỉ đọc; trả HTML để tái dùng nguyên vẹn, không ghi đè file gốc."""
    db_err = _db_missing_error()
    if db_err:
        return {"ok": False, "player": None, "error": db_err}
    try:
        row = composer._load("players", player_id)  # nội bộ composer: đọc SQLite, không ghi
    except composer.ComposerError as exc:
        return {"ok": False, "player": None, "error": str(exc)}
    man = composer._json_value(row.get("manifest")) or {}
    return {"ok": True, "player": {"id": row["id"], "name": row["name"], "manifest": man,
                                   "html": row["html"]}, "error": None}


@tool
def list_models(kind: str = None, limit: int = 50) -> dict:
    """list_models — tra cứu Model AI có sẵn trong Catalog (kèm kinds/outputs thật).
    Input: kind (str|None) lọc theo 'hands'/'image'/'pose'/'audio', limit (int, 1–100).
    Output: {"ok": bool, "models": [{"id","name","kind","outputs","url"}], "error": str|None}.
    Không tác động ra ngoài: chỉ đọc Catalog; không nạp model, không lưu, không xuất bản."""
    db_err = _db_missing_error()
    if db_err:
        return {"ok": False, "models": [], "error": db_err}
    try:
        snap = composer.catalog_snapshot()
    except composer.ComposerError as exc:
        return {"ok": False, "models": [], "error": str(exc)}
    try:
        cap = max(1, min(100, int(limit)))
    except (TypeError, ValueError):
        cap = 50
    out = []
    for m in snap["models"]:
        if kind and m.get("kind") != kind:
            continue
        out.append({k: m.get(k) for k in ("id", "name", "kind", "outputs", "url")})
        if len(out) >= cap:
            break
    return {"ok": True, "models": out, "error": None}


@tool
def validate_compatibility(player_id: int = None, model_id: int = None, exam_id: int = None,
                           mapping: dict = None, plan: dict = None) -> dict:
    """validate_compatibility — kiểm tổ hợp Model + Player + Question Set bằng Rules.
    Input: player_id/model_id/exam_id (int|None, ID thật trong Catalog; None = chuột hoặc không có đề),
           mapping (dict|None) ánh xạ ô của player sang lớp của model, plan (dict|None) để kiểm mouse_always_enabled.
    Output: {"ok": bool, "reasons": [str], "player": str, "model": str, "exam": str}.
    Không tác động ra ngoài: chỉ đọc Catalog và kiểm Rules; không lưu, không chấm điểm, không xuất bản."""
    raw = plan.get("application_plan") if isinstance(plan, dict) and isinstance(plan.get("application_plan"), dict) else plan
    raw = raw if isinstance(raw, dict) else {}
    if player_id is None:
        player_id = (raw.get("player") or {}).get("player_id") if isinstance(raw.get("player"), dict) else None
    if model_id is None:
        model_id = (raw.get("model") or {}).get("model_id") if isinstance(raw.get("model"), dict) else None
    if exam_id is None:
        exam_id = (raw.get("exam") or {}).get("exam_id") if isinstance(raw.get("exam"), dict) else None
    db_err = _db_missing_error()
    if db_err:
        return {"ok": False, "reasons": [db_err], "player": "", "model": "", "exam": ""}
    try:
        p = composer._load("players", player_id) if player_id not in (None, "") else None
        m = composer._load("models", model_id) if model_id not in (None, "") else None
        e = composer._load("exams", exam_id) if exam_id not in (None, "") else None
    except composer.ComposerError as exc:
        return {"ok": False, "reasons": [str(exc)], "player": "", "model": "", "exam": ""}
    return composer.validate_compatibility(p, m, e, mapping=mapping, plan=plan)


@tool
def compose_application(plan: dict) -> dict:
    """compose_application — lắp ApplicationPlan hợp lệ thành ứng dụng BẢN NHÁP (DRAFT).
    Input: plan (dict hoặc chuỗi JSON theo Contract của T06; có thể bọc trong 'application_plan').
    Output: {"ok": bool, "errors": [str], "app": dict|None, "status": "draft"};
            app gồm Model + Player + Question Set, requires_human_approval=True, catalog_written=False.
    Không tác động ra ngoài: KHÔNG ghi Catalog, KHÔNG lưu DB, KHÔNG tự đặt APPROVED hay xuất bản."""
    db_err = _db_missing_error()
    if db_err:
        return {"ok": False, "errors": [db_err], "app": None, "status": "draft"}
    return composer.compose_app(plan)


@tool
def list_exams(name_contains: str = None, limit: int = 50) -> dict:
    """list_exams — tra cứu danh sách bộ đề (Question Set) có sẵn trong Catalog kèm số câu thật.
    Input: name_contains (str|None) lọc theo tên bộ đề, limit (int, 1–100).
    Output: {"ok": bool, "exams": [{"id","name","description","count"}], "error": str|None}.
    Không tác động ra ngoài: chỉ đọc Catalog; không lưu, không sửa, không xuất bản."""
    db_err = _db_missing_error()
    if db_err:
        return {"ok": False, "exams": [], "error": db_err}
    try:
        snap = composer.catalog_snapshot()
    except composer.ComposerError as exc:
        return {"ok": False, "exams": [], "error": str(exc)}
    try:
        cap = max(1, min(100, int(limit)))
    except (TypeError, ValueError):
        cap = 50
    out = []
    for e in snap["exams"]:
        if name_contains and name_contains.strip().lower() not in (e["name"] or "").lower():
            continue
        out.append({k: e.get(k) for k in ("id", "name", "description", "count")})
        if len(out) >= cap:
            break
    return {"ok": True, "exams": out, "error": None}


@tool
def get_exam(exam_id: int) -> dict:
    """get_exam — lấy nội dung đầy đủ và số câu thật của một bộ đề theo ID trong Catalog.
    Input: exam_id (int), ID có thật trong Catalog; không đoán ID.
    Output: {"ok": bool, "exam": {"id","name","description","count","content"} hoặc None, "error": str|None}.
    Không tác động ra ngoài: chỉ đọc Catalog; không sửa, không xuất bản."""
    db_err = _db_missing_error()
    if db_err:
        return {"ok": False, "exam": None, "error": db_err}
    try:
        row = composer._load("exams", exam_id)
    except composer.ComposerError as exc:
        return {"ok": False, "exam": None, "error": str(exc)}
    content = row.get("content") or ""
    try:
        count = len(store.parse_questions(content))
    except store.Err:
        count = 0
    return {"ok": True, "exam": {"id": row["id"], "name": row["name"], "description": row.get("description", ""),
                                 "count": count, "content": content}, "error": None}


@tool
def validate_exam(content: str, player_id: int = None, expected_count: int = None, manifest: dict = None) -> dict:
    """validate_exam — kiểm tra cú pháp bộ câu hỏi (Question Set) theo luật ailab/store.py parse_questions().
    Input: content (str) nội dung bộ đề, player_id (int|None) hoặc manifest (dict|None) kiểm tương thích với Player, expected_count (int|None).
    Output: {"ok": bool, "count": int, "errors": [str], "warnings": [{"code","message","field"}]}.
    Không tác động ra ngoài: chỉ kiểm tra Rules; luôn trả cảnh báo yêu cầu giáo viên kiểm duyệt kiến thức."""
    warnings = [{
        "code": "knowledge_review_required",
        "message": "Bộ câu hỏi do AI soạn/kiểm tra cú pháp chưa được xác minh kiến thức. Giáo viên bắt buộc kiểm duyệt câu hỏi và đáp án trước khi dùng trên lớp.",
        "field": "exam.content",
    }]
    if not isinstance(content, str) or not content.strip():
        return {"ok": False, "count": 0, "errors": ["Nội dung bộ đề không được rỗng."], "warnings": warnings}
    errors = []
    parsed = []
    try:
        store.clean_exam({"name": "Kiểm tra bộ đề", "content": content})
        parsed = store.parse_questions(content)
    except store.Err as exc:
        errors.append(exc.msg)
        return {"ok": False, "count": 0, "errors": errors, "warnings": warnings}
    except (ValueError, TypeError) as exc:
        errors.append("Lỗi định dạng bộ đề: %s" % exc)
        return {"ok": False, "count": 0, "errors": errors, "warnings": warnings}

    resolved_manifest = manifest if isinstance(manifest, dict) else None
    if resolved_manifest is None and player_id is not None:
        db_err = _db_missing_error()
        if db_err:
            errors.append(db_err)
        else:
            try:
                prow = composer._load("players", player_id)
                resolved_manifest = composer._json_value(prow.get("manifest"))
            except composer.ComposerError as exc:
                errors.append(str(exc))

    questions = [{
        "type": q["type"],
        "text": q["text"],
        "choices": [{"key": c["key"], "text": c["text"]} for c in q["choices"]],
        "answer": q["answer"],
        "explanation": "Structural check",
        "sourceRefs": [],
        "aiGenerated": True,
    } for q in parsed]

    structural = chatbot_exams.validate_exam_questions(
        {"name": "Kiểm tra bộ đề", "questions": questions},
        manifest=resolved_manifest,
        question_count=expected_count,
    )
    for item in structural:
        idx = item.get("questionIndex")
        prefix = "Câu %d: " % (idx + 1) if isinstance(idx, int) else ""
        errors.append(prefix + item.get("message", "Lỗi cấu trúc bộ đề."))

    return {"ok": not errors, "count": len(parsed), "errors": errors, "warnings": warnings}
