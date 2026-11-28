"""T09 — Deterministic AI Guardrails & Output Validation (Rules, không gọi LLM).

Nhiệm vụ:
- Kiểm tra đầu vào (input validation) cho cả chuỗi thường (CLI/Eval) và Spec request dict (Web/Shared Core).
- Chặn tấn công prompt injection, trích xuất bí mật/PII, yêu cầu mã gọi mạng/thoát iframe,
  và yêu cầu vượt quyền HITL (tự đặt APPROVED / tự công khai vào Catalog).
- Kiểm tra đầu ra bằng Rules: ApplicationPlan Contract v1.0, ID Catalog thật, tương thích
  Model + Player + Question Set, cú pháp Question Set (parse_questions), HTML nháp qua
  check_game với 0 cờ an toàn, và luôn bật Mouse Fallback.

Không có bất kỳ công cụ nào cấp APPROVED hoặc ghi vào Catalog chính thức.
"""
import copy
import json
import os
import re
import sys
import unicodedata

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, os.path.join(_ROOT, "ailab")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import application_contract as ac  # noqa: E402
import composer  # noqa: E402
import contract  # noqa: E402
import store  # noqa: E402
import tools  # noqa: E402
from chatbot import schemas  # noqa: E402

MAX_MESSAGE_LEN = 4000
ALLOWED_REQUEST_KEYS = {
    "session_id",
    "message",
    "history",
    "document_ids",
    "selected_player_id",
    "selected_model_id",
    "selected_exam_id",
    "generation_mode",
}

KNOWLEDGE_REVIEW_WARNING = {
    "code": "knowledge_review_required",
    "message": (
        "Cảnh báo kiểm duyệt kiến thức: Bộ câu hỏi do AI soạn/đề xuất mới chỉ được kiểm tra định dạng; "
        "giáo viên bắt buộc kiểm duyệt lại nội dung kiến thức và đáp án trước khi dùng trên lớp."
    ),
    "field": "exam.content",
}

FENCE = chr(96) * 3
HTML_FENCE_RE = re.compile(FENCE + r"(?:html)?\s*\n(.*?)" + FENCE, re.S | re.I)


def fold_text(text: str) -> str:
    """Chuẩn hóa chữ thường không dấu để đối chiếu quy tắc bảo mật ổn định."""
    if not isinstance(text, str):
        return ""
    norm = unicodedata.normalize("NFKD", text.lower().replace("đ", "d").replace("Đ", "d"))
    return "".join(ch for ch in norm if not unicodedata.combining(ch))


def _is_negated(folded: str, start: int) -> bool:
    """Tránh chặn nhầm câu giáo viên nhắc điều KHÔNG làm (vd 'không lưu ngay', 'không gọi mạng')."""
    prefix = folded[max(0, start - 28):start]
    return bool(re.search(
        r"(?:khong|ko|cam|tranh|dung|do not|don't|never|without)\s+(?:duoc\s+|can\s+|tu\s+|them\s+)?$",
        prefix,
    ))


# Quy tắc từ chối tổng quát theo danh mục rủi ro (KHÔNG hardcode câu thử benchmark).
_REFUSAL_RULES = (
    (
        "prompt_injection",
        (
            r"(?:ignore|disregard|forget)\s+(?:all\s+|the\s+)?(?:previous|prior|system)\s+instructions",
            r"bo qua\s+(?:moi\s+|tat ca\s+)?(?:huong dan|chi dan|quy tac|he thong)",
            r"(?:in ra|hien thi|tiet lo|reveal|print|dump|show|what is)\s+(?:the\s+|your\s+)?(?:system\s+prompt|loi nhac he thong|prompt he thong)",
            r"(?:doc|lay|tiet lo|reveal|read|xem|in)\s+.*?(?:\.env|api[ _-]?key|mat khau|password|secret|token)",
        ),
        (
            "Từ chối yêu cầu vì vượt phạm vi an toàn (prompt injection hoặc truy cập thông tin bí mật hệ thống). "
            "AI Game Composer chỉ hỗ trợ chọn/tạo bản nháp trò chơi ôn tập lớp học và bộ câu hỏi để giáo viên kiểm duyệt. "
            "Bạn hãy mô tả môn học, chủ đề và hình thức tương tác mong muốn nhé."
        ),
    ),
    (
        "pii_request",
        (
            r"(?:liet ke|xuat|gui|lay|truy xuat|cho xem|dump|export|list)\s+.*?(?:ten hoc sinh|danh sach hoc sinh|diem so|diem thi|thong tin ca nhan|du lieu ca nhan|so dien thoai|email hoc sinh|student names?|student grades?|student scores?|pii)",
            r"(?:hoc sinh|hoc vien)\s+.*?(?:diem so|diem thi|thong tin ca nhan)\s+.*?(?:gui|xuat|cho toi)",
        ),
        (
            "Từ chối yêu cầu truy xuất thông tin cá nhân hoặc điểm số học sinh. "
            "Catalog của AI Lab không lưu dữ liệu cá nhân học viên và AI không có quyền truy cập thông tin riêng tư. "
            "Bạn có thể yêu cầu dùng các bộ đề mẫu công khai trong Catalog hoặc tạo bộ câu hỏi ôn tập mới để giáo viên duyệt."
        ),
    ),
    (
        "unsafe_code",
        (
            r"(?:\bfetch\s*\(|xmlhttprequest|websocket|sendbeacon|eventsource)",
            r"(?:todataurl|getimagedata|\beval\s*\(|new\s+function\b|localstorage|parent\.document|window\.top)",
            r"(?:gui|upload|truyen|post|chuyen)\s+.*?(?:anh camera|hinh camera|camera|du lieu).*?(?:may chu|server|email|gmail|http|webhook|may toi|url)",
            r"(?:mo cua so moi|window\.open|chuyen trang|top\.location|document\.cookie)",
            r"(?:thoat|vuot|escape|bypass)\s+.*?(?:iframe|sandbox|csp)",
            r"(?:goi mang|ket noi mang|gui request)\s+(?:ra ngoai|len|den|toi)",
        ),
        (
            "Từ chối tạo mã gọi mạng, gửi ảnh camera ra ngoài, mở cửa sổ mới hoặc thoát khung sandbox. "
            "Quy tắc an toàn AI Lab (FLAG_RULES, iframe sandbox và CSP connect-src 'none') chặn mọi hành vi gọi mạng, "
            "đọc/gửi ảnh camera và mở cửa sổ mới để bảo vệ học sinh. "
            "Hướng dẫn thay thế: hãy mô tả trò chơi lớp học chạy hoàn toàn cục bộ (không gọi mạng) trong iframe sandbox để giáo viên kiểm duyệt."
        ),
    ),
    (
        "hitl_bypass",
        (
            r"(?:tu|auto)[ -]?(?:dong\s+)?(?:duyet|phe duyet|cong khai|xuat ban|publish|approve|approved)",
            r"(?:dat|gan|set|mark|assign|gui payload|chuyen)\s+.*?(?:status\s*=\s*approved|trang thai\s*=?\s*approved|\bapproved\b)",
            r"(?:bo qua|skip|bypass|khong can)\s+.*?(?:hitl|giao vien duyet|nguoi duyet|phe duyet|kiem duyet|approval|review)",
            r"(?:tu dua|tu them|tu ghi|tu luu|dua thang|luu thang)\s+.*?(?:catalog|cong dong|he thong|bo de chinh thuc)",
            r"(?:cong khai ngay|xuat ban ngay)\b",
        ),
        (
            "Từ chối tự phê duyệt (status=APPROVED) hoặc tự công khai/ghi vào Catalog chính thức. "
            "Theo quy tắc HITL (HITL Bypass Count = 0), AI chỉ được đề xuất ở trạng thái BẢN NHÁP (DRAFT / pending_approval), "
            "chạy qua check_game và xem thử trong iframe sandbox; chỉ giáo viên hoặc Admin bấm phê duyệt trên Backend mới có quyền xuất bản."
        ),
    ),
    (
        "out_of_scope",
        (
            r"(?:hack\s+(?:account|tai khoan|wifi|facebook)|malware|ransomware|keylogger|phishing|ddos|sql injection)",
            r"(?:marketing email|email quang cao|spam email|du doan gia\s+(?:co phieu|bitcoin|chung khoan))",
        ),
        (
            "Từ chối yêu cầu vì nằm ngoài phạm vi hỗ trợ lớp học của AI Game Composer. "
            "Hệ thống chỉ hỗ trợ thiết kế bản nháp trò chơi ôn tập tương tác và bộ câu hỏi cho giáo viên kiểm duyệt."
        ),
    ),
)


def check_input_safety(text: str) -> tuple:
    """Kiểm tra đầu vào bằng Rules bảo mật (quét mọi khớp bằng finditer để chống decoy phủ định).

    Trả về (refused: bool, category: str|None, message: str, error_code: str).
    """
    folded = fold_text(text)
    if not folded.strip():
        return False, None, "", ""
    for category, patterns, message in _REFUSAL_RULES:
        for pat in patterns:
            for m in re.finditer(pat, folded):
                if not _is_negated(folded, m.start()):
                    return True, category, message, "refused"
    return False, None, "", ""


def validate_request_input(request):
    """Chuẩn hóa & kiểm tra đầu vào cho Shared Core (str hoặc Spec dict).

    Trả về (normalized_dict_or_None, errors_list).
    """
    if isinstance(request, str):
        text = request.strip()
        if not text:
            return None, [ac.issue("invalid_input", "Yêu cầu không được để trống.", "message")]
        if len(text) > MAX_MESSAGE_LEN:
            return None, [ac.issue("invalid_input", "Yêu cầu vượt quá giới hạn %d ký tự." % MAX_MESSAGE_LEN, "message")]
        return {
            "session_id": "cli",
            "message": text,
            "history": [],
            "document_ids": [],
            "selected_player_id": None,
            "selected_model_id": None,
            "selected_exam_id": None,
            "generation_mode": None,
        }, []

    if not isinstance(request, dict):
        return None, [ac.issue("invalid_input", "Đầu vào phải là chuỗi hoặc object JSON.", "request")]

    unknown = set(request.keys()) - ALLOWED_REQUEST_KEYS
    if unknown:
        return None, [ac.issue("invalid_input", "Trường đầu vào không hợp lệ: %s." % ", ".join(sorted(unknown)), "request")]

    session_id = request.get("session_id", "web")
    message = request.get("message")
    if not isinstance(session_id, str) or not session_id.strip() or len(session_id) > 128:
        return None, [ac.issue("invalid_input", "session_id phải là chuỗi 1–128 ký tự.", "session_id")]
    if not isinstance(message, str) or not 1 <= len(message.strip()) <= MAX_MESSAGE_LEN:
        return None, [ac.issue("invalid_input", "message phải là chuỗi 1–%d ký tự." % MAX_MESSAGE_LEN, "message")]

    history = request.get("history", [])
    doc_ids = request.get("document_ids", [])
    if not isinstance(history, list):
        return None, [ac.issue("invalid_input", "history phải là danh sách.", "history")]
    if not isinstance(doc_ids, list):
        return None, [ac.issue("invalid_input", "document_ids phải là danh sách.", "document_ids")]

    for field in ("selected_player_id", "selected_model_id", "selected_exam_id"):
        val = request.get(field)
        if val is not None and not ac._id(val):
            return None, [ac.issue("invalid_input", "%s phải là số nguyên dương hoặc null." % field, field)]

    mode = request.get("generation_mode")
    if mode not in (None, "auto", "reuse_existing", "generate_new"):
        return None, [ac.issue("invalid_input", "generation_mode không hợp lệ.", "generation_mode")]

    return {
        "session_id": session_id.strip(),
        "message": message.strip(),
        "history": history,
        "document_ids": doc_ids,
        "selected_player_id": request.get("selected_player_id"),
        "selected_model_id": request.get("selected_model_id"),
        "selected_exam_id": request.get("selected_exam_id"),
        "generation_mode": mode,
    }, []


def _readonly_seed_registry() -> dict:
    """Fallback CHỈ ĐỌC trong bộ nhớ khi SQLite DB chưa được khởi tạo (không tạo file DB)."""
    import json
    import llm as ailab_llm

    players = []
    for pid, (tpl, title) in enumerate(
        ((ailab_llm.QUIZ_TEMPLATE, "Quiz ABCD bằng cử chỉ"), (ailab_llm.WHEEL_TEMPLATE, "Vòng quay chọn tên")),
        start=1,
    ):
        html = tpl.replace("__TITLE__", title)
        man, _ = contract.parse(html)
        if man:
            players.append({
                "id": pid,
                "name": title,
                "manifest": man,
                "kinds": man.get("kinds"),
                "inputs": [i["key"] for i in man.get("inputs", [])],
                "questions": man.get("questions"),
                "content": man.get("content"),
                "status": "approved",
            })

    models = [{
        "id": 1,
        "name": "Bàn tay (MediaPipe)",
        "kind": "hands",
        "outputs": [
            {"key": "fist", "role": "action"},
            {"key": "open", "role": "action"},
            {"key": "none", "role": "empty"},
        ],
        "url": store.HANDS_URL,
    }]

    exams = []
    if os.path.exists(store.SEED_EXAMS_FILE):
        try:
            with open(store.SEED_EXAMS_FILE, encoding="utf-8") as f:
                items = json.load(f)
            for eid, item in enumerate(items, start=1):
                content = item.get("content") or ""
                try:
                    cnt = len(store.parse_questions(content))
                except store.Err:
                    cnt = 0
                exams.append({
                    "id": eid,
                    "name": item.get("name", ""),
                    "description": item.get("description", ""),
                    "count": cnt,
                    "content": content,
                })
        except (OSError, ValueError):
            pass

    return {"players": players, "models": models, "exams": exams}


def load_live_registry() -> tuple:
    """Đọc Catalog thật qua @tool (list_players/list_models/list_exams) để ghi trace đầy đủ
    và dựng trusted registry cho validate_application_plan. Tuyệt đối CHỈ ĐỌC (không tạo DB).
    Trả về (registry_dict, db_ready: bool)."""
    if not os.path.exists(store.DB_PATH):
        return _readonly_seed_registry(), False
    p_res = tools.list_players()
    m_res = tools.list_models()
    e_res = tools.list_exams()

    if not p_res.get("ok") or not m_res.get("ok") or not e_res.get("ok"):
        return _readonly_seed_registry(), False

    players = []
    for p in (p_res.get("players") or []):
        detail = tools.get_player(p["id"])
        if detail.get("ok") and detail.get("player"):
            row = detail["player"]
            players.append({
                "id": row["id"],
                "name": row["name"],
                "manifest": row["manifest"],
                "kinds": p.get("kinds"),
                "inputs": p.get("inputs") or [],
                "questions": p.get("questions"),
                "content": p.get("content"),
                "status": p.get("status"),
            })

    models = copy.deepcopy(m_res.get("models") or [])

    exams = []
    for e in (e_res.get("exams") or []):
        detail = tools.get_exam(e["id"])
        if detail.get("ok") and detail.get("exam"):
            exams.append(detail["exam"])

    return {"players": players, "models": models, "exams": exams}, True


def format_catalog_context(registry: dict) -> str:
    """Tạo bảng tóm tắt Catalog thật (ID, tên, kinds/inputs/số câu) để nạp vào prompt LLM."""
    lines = ["=== DANH MỤC CATALOG THẬT (CHỈ ĐƯỢC DÙNG ĐÚNG ID & TÊN DƯỚI ĐÂY, TUYỆT ĐỐI KHÔNG BỊA) ==="]
    lines.append("1. PLAYERS (Trình chơi có sẵn):")
    for p in registry.get("players") or []:
        man = p.get("manifest") if isinstance(p.get("manifest"), dict) else {}
        kinds = man.get("kinds") if "inputs" in man else None
        inputs = [i.get("key") for i in (man.get("inputs") or []) if isinstance(i, dict)]
        q_mode = man.get("questions") or (man.get("content") or {}).get("kind") or "unknown"
        lines.append(
            "   - id=%s | name=\"%s\" | kinds=%s | inputs=%s | content/questions=%s"
            % (p["id"], p["name"], kinds, inputs, q_mode)
        )
    lines.append("2. MODELS (Model AI tương tác có sẵn):")
    for m in registry.get("models") or []:
        outs = ", ".join("%s(%s)" % (o.get("key"), o.get("role", "action")) for o in (m.get("outputs") or []))
        lines.append(
            "   - id=%s | name=\"%s\" | kind=%s | outputs=[%s]"
            % (m["id"], m["name"], m.get("kind"), outs)
        )
    lines.append("3. EXAMS (Bộ đề có sẵn trong Catalog):")
    for e in registry.get("exams") or []:
        cnt = e.get("count")
        if cnt is None:
            try:
                cnt = len(store.parse_questions(e.get("content") or ""))
            except store.Err:
                cnt = 0
        lines.append("   - id=%s | name=\"%s\" | so_cau=%d" % (e["id"], e["name"], cnt))
    lines.append("4. GIỚI HẠN RUNTIME BẮT BUỘC:")
    lines.append("   - Runtime hỗ trợ kinds: hands, image, pose (và chuột mouse).")
    lines.append("   - Runtime CHƯA hỗ trợ audio / giọng nói (không được ghép hay bịa model giọng nói).")
    lines.append("   - Mọi trò chơi BẮT BUỘC bật Mouse Fallback (fallback='mouse', mouse_always_enabled=true).")
    lines.append("   - Chỉ ghép model với player khi player có `inputs` và `kinds` của player chứa `kind` của model; nếu thiếu `kinds` hoặc trùng lớp/sai vai trò `empty` thì báo rõ lý do và đề xuất dùng chuột hoặc chờ TV3 xác minh.")
    lines.append("   - Player có `content/questions = texts` chỉ nhận danh sách chữ (KHÔNG nhận bộ đề câu hỏi `exam` và KHÔNG gắn camera model nếu `inputs=[]`).")
    return "\n".join(lines)


_SCRIPT_BLOCK_RE = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.S | re.I)
_MANIFEST_JSON_RE = re.compile(
    r'<script[^>]*\bid\s*=\s*["\']jl-camera["\'][^>]*>(?P<json>.*?)</script>', re.S | re.I
)


def validate_html_draft(html: str, check_fn=None) -> dict:
    """Kiểm tra HTML nháp (nhánh GENERATE) theo 4 tầng: L1 Contract + L3 Security (0 cờ) + L4 Protocol/Functional cơ bản."""
    if not isinstance(html, str) or not html.strip():
        return {"ok": False, "error": "HTML nháp rỗng.", "flags": [], "name": ""}
    stripped = html.strip()
    if "</html>" not in stripped.lower():
        return {"ok": False, "error": "HTML có dấu hiệu bị cắt cụt (thiếu thẻ đóng </html>).", "flags": [], "name": ""}
    checker = check_fn or tools.check_game
    res = checker(stripped)
    if not res.get("ok"):
        return {"ok": False, "error": res.get("error") or "HTML vi phạm hợp đồng jl-camera.", "flags": [], "name": ""}
    flags = res.get("flags") or []
    if flags:
        flag_desc = "; ".join("%s (dòng %s)" % (f.get("label"), f.get("line")) for f in flags)
        return {
            "ok": False,
            "error": "HTML nháp chứa %d cờ an toàn bị chặn: %s" % (len(flags), flag_desc),
            "flags": flags,
            "name": res.get("name", ""),
        }
    # L1 Contract: kiểm tra JSON manifest thô (trước khi contract.parse lược bỏ) để chặn xung đột questions="exam" + content.kind="texts"
    m_raw = _MANIFEST_JSON_RE.search(stripped)
    if m_raw:
        try:
            raw_man = json.loads(m_raw.group("json"))
        except ValueError:
            raw_man = None
        if isinstance(raw_man, dict):
            raw_content = raw_man.get("content")
            content_kind = raw_content.get("kind") if isinstance(raw_content, dict) else None
            if raw_man.get("questions") == "exam" and content_kind == "texts":
                return {
                    "ok": False,
                    "error": "Manifest xung đột: không được khai đồng thời questions='exam' và content.kind='texts'.",
                    "flags": [],
                    "name": res.get("name", ""),
                }
    # L4 Protocol/Functional: bắt buộc có script thực thi gửi parent.postMessage ready
    exec_scripts = []
    for m in _SCRIPT_BLOCK_RE.finditer(stripped):
        attrs = (m.group("attrs") or "").lower()
        if "application/json" in attrs:
            continue
        body = (m.group("body") or "").strip()
        if body:
            exec_scripts.append(body)
    joined_js = "\n".join(exec_scripts)
    if not joined_js:
        return {
            "ok": False,
            "error": "HTML nháp thiếu mã JavaScript thực thi gameplay.",
            "flags": [],
            "name": res.get("name", ""),
        }
    if "ready" not in joined_js or "postmessage" not in joined_js.lower():
        return {
            "ok": False,
            "error": "HTML nháp chưa cài đặt đúng giao thức runtime (thiếu parent.postMessage ready).",
            "flags": [],
            "name": res.get("name", ""),
        }
    return {"ok": True, "error": None, "flags": [], "name": res.get("name", "")}


def redact_text(text: str, limit: int = 8000) -> str:
    """Ẩn chuỗi giống API key/token nếu model lỡ lặp lại trong phản hồi."""
    if not isinstance(text, str):
        return ""
    return schemas.redact(text, limit)


def enforce_single_question(message: str) -> str:
    """Đảm bảo nhánh ASK_CLARIFY hỏi đúng 1 câu cụ thể (1 dấu hỏi, không chứa khối mã HTML)."""
    clean = HTML_FENCE_RE.sub("", message or "").strip()
    if not clean:
        return "Bạn muốn tạo trò chơi ôn tập cho môn học/chủ đề nào và lớp học có dùng chuột hay camera?"
    if "?" not in clean:
        return clean.rstrip(".!") + "?"
    # Giữ đúng 1 dấu hỏi nếu LLM lỡ hỏi nhiều câu liên tiếp
    first_q = clean.find("?")
    rest = clean[first_q + 1:].replace("?", ".")
    return (clean[:first_q + 1] + rest).strip()


def strip_html_fences(text: str) -> str:
    """Loại bỏ khối mã HTML thực thi khỏi câu trả lời văn bản ở các nhánh cấm xuất HTML."""
    return HTML_FENCE_RE.sub("", text or "").strip()


def validate_output_envelope(envelope: dict, registry: dict = None) -> list:
    """Kiểm tra đầu ra cuối cùng theo ApplicationPlan Contract v1.0 + chính sách cảnh báo."""
    errors = ac.validate_agent_response(envelope, registry=registry)
    errors.extend(ac.validate_knowledge_review_policy(envelope))
    return errors
