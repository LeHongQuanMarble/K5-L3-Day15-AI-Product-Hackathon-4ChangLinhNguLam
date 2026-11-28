"""P0 — Structured Conversation State, Multi-turn Requirement Accumulation & Grounded Resource Selection.

Thuần thư viện chuẩn Python — dùng chung cho `codebase/agent.py`, `ailab/agent_bridge.py`, `ailab/server.py`.
Không tự gọi LLM, không ghi DB trực tiếp, không lưu bí mật/frame camera/audio.
"""
import copy
import difflib
import re
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, os.path.join(_ROOT, "ailab")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from chatbot import catalog as chatbot_catalog  # noqa: E402
import guardrails  # noqa: E402

VALID_MODEL_KINDS = ("image", "pose", "hands", "audio", "mouse")
VALID_CREATION_PREFS = ("reuse", "new", "unspecified")
VALID_CONVERSATION_STATUSES = ("collecting", "ready", "draft_pending", "approved", "rejected", "blocked")

_BROKEN_URL_PATTERNS = (
    re.compile(r"models/x/", re.I),
    re.compile(r"placeholder", re.I),
    re.compile(r"fake-url", re.I),
)

_SUBJECT_PATTERNS = (
    ("Toán", re.compile(r"\b(?:toan(?:\s+hoc)?|so\s+hoc|hinh\s+hoc|dai\s+so)\b")),
    ("Tiếng Việt", re.compile(r"\b(?:tieng\s+viet|tap\s+doc|chinh\s+ta|luyen\s+tu)\b")),
    ("Tiếng Anh", re.compile(r"\b(?:tieng\s+anh|english|ngoai\s+ngu)\b")),
    ("Lịch sử", re.compile(r"\b(?:lich\s+su|su\s+hoc)\b")),
    ("Địa lý", re.compile(r"\b(?:dia\s+ly|dia\s+li)\b")),
    ("Khoa học", re.compile(r"\b(?:khoa\s+hoc|tu\s+nhien\s+va\s+xa\s+hoi)\b")),
    ("Vật lý", re.compile(r"\b(?:vat\s+ly|vat\s+li)\b")),
    ("Hóa học", re.compile(r"\b(?:hoa\s+hoc)\b")),
    ("Sinh học", re.compile(r"\b(?:sinh\s+hoc)\b")),
    ("Tin học", re.compile(r"\b(?:tin\s+hoc|lap\s+trinh)\b")),
    ("Ngữ văn", re.compile(r"\b(?:ngu\s+van|van\s+hoc)\b")),
    ("GDCD", re.compile(r"\b(?:gdcd|dao\s+duc|giao\s+duc\s+cong\s+dan)\b")),
)

_GRADE_RE = re.compile(r"\b(?:lop|khoi)\s*(\d{1,2})\b")
_QCOUNT_RE = re.compile(r"\b(\d{1,2})\s*(?:cau(?:\s+hoi)?|questions?)\b")

_EXPLICIT_NEW_PREF_RE = re.compile(
    r"(?:tao|viet|sinh|thiet\s+ke|lam)\s+(?:mot\s+)?(?:player|trinh\s+choi|game|tro\s+choi)\s+moi"
    r"|tao\s+moi\s+hoan\s+toan"
    r"|khong\s+(?:dung|su\s+dung)\s+(?:lai|player|game|trinh\s+choi)\s+(?:co\s+san|cu)"
    r"|khong\s+reuse|dung\s+dung\s+lai|viet\s+moi\s+hoan\s+toan"
)
_EXPLICIT_REUSE_PREF_RE = re.compile(
    r"(?:chi\s+(?:su\s+dung|dung)|uu\s+tien\s+dung\s+lai)\s+(?:game|tro\s+choi|player|trinh\s+choi)\s+(?:trong\s+kho|co\s+san|catalog)"
    r"|khong\s+(?:tao|sinh|viet)\s+(?:player|game|html)\s+moi"
    r"|dung\s+lai\s+(?:game|trinh\s+choi|player)\s+(?:trong\s+kho|co\s+san)"
)
_NEW_TASK_RE = re.compile(
    r"(?:bat\s+dau\s+lai|lam\s+lai\s+tu\s+dau|cuoc\s+tro\s+chuyen\s+moi|nhiem\s+vu\s+moi|reset\s+yeu\s+cau)"
)
_CHANGE_INTENT_RE = re.compile(r"\b(?:doi\s+sang|chuyen\s+sang|thay\s+bang|doi\s+thanh|sua\s+thanh|khong\s+dung\s+nua)\b")
_CHAT_AGREE_RE = re.compile(r"^(?:ok|oke|duoc|dong\s+y|duyet\s+di|xuat\s+ban\s+di|luu\s+luon\s+di|approved?)[.! ]*$")

_MECHANIC_PATTERNS = (
    ("sút penalty", re.compile(r"\b(?:sut\s+penalt\w*|penat\w*|da\s+phat\s+den)\b")),
    ("cầu lông", re.compile(r"\b(?:cau\s+long|badminton)\b")),
    ("đua xe", re.compile(r"\b(?:dua\s+xe|racing)\b")),
    ("vòng quay chọn tên", re.compile(r"\b(?:vong\s+quay|quay\s+ten|boc\s+tham)\b")),
    ("ghép cặp thẻ", re.compile(r"\b(?:ghep\s+cap|lat\s+the|matching)\b")),
    ("đúng / sai", re.compile(r"\b(?:dung\s*[/\-]?\s*sai|true\s*[/\-]?\s*false)\b")),
    ("giải cứu thế giới", re.compile(r"\b(?:giai\s+cuu\s+the\s+gioi)\b")),
    ("tết 2027", re.compile(r"\b(?:tet\s+2027|de\s+vang|cong\s+bang)\b")),
    ("chim bay nói", re.compile(r"\b(?:chim\s+bay|flappy)\b")),
    ("bắn bóng", re.compile(r"\b(?:ban\s+bong|ban\s+bong\s+bay)\b")),
    ("thu hoạch", re.compile(r"\b(?:thu\s+hoach|hai\s+tao|hung\s+tao)\b")),
    ("quiz trắc nghiệm", re.compile(r"\b(?:quiz|trac\s+nghiem|abcd)\b")),
)


def new_state(conversation_id=None, user_id=None) -> dict:
    """Khởi tạo structured conversation state rỗng, chuẩn hóa."""
    return {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "learning_subject": None,
        "grade_level": None,
        "learning_topic": None,
        "learning_objective": None,
        "question_count": None,
        "question_type": None,
        "preferred_model_kind": None,
        "selected_model_id": None,
        "selected_player_id": None,
        "selected_exam_id": None,
        "interaction_requirements": [],
        "game_mechanic": None,
        "creation_preference": "unspecified",
        "confirmed_requirements": {},
        "missing_requirements": [],
        "active_draft_id": None,
        "active_plan_hash": None,
        "conversation_status": "collecting",
    }


def normalize_state(raw, conversation_id=None, user_id=None) -> dict:
    """Chuẩn hóa dict state an toàn; không tin dữ liệu bẩn, không làm mất giá trị hợp lệ."""
    st = new_state(conversation_id=conversation_id, user_id=user_id)
    if not isinstance(raw, dict):
        return st
    if raw.get("conversation_id") is not None and st["conversation_id"] is None:
        st["conversation_id"] = raw.get("conversation_id")
    if raw.get("user_id") is not None and st["user_id"] is None:
        st["user_id"] = raw.get("user_id")

    for str_key in ("learning_subject", "grade_level", "learning_topic", "learning_objective", "question_type", "game_mechanic"):
        v = raw.get(str_key)
        if isinstance(v, str) and v.strip():
            st[str_key] = guardrails.redact_text(v.strip(), 200)

    qcnt = raw.get("question_count")
    if isinstance(qcnt, int) and not isinstance(qcnt, bool) and 1 <= qcnt <= 100:
        st["question_count"] = qcnt

    mk = raw.get("preferred_model_kind")
    if isinstance(mk, str) and mk.strip().lower() in VALID_MODEL_KINDS:
        st["preferred_model_kind"] = mk.strip().lower()

    for id_key in ("selected_model_id", "selected_player_id", "selected_exam_id", "active_draft_id"):
        v = raw.get(id_key)
        if isinstance(v, int) and not isinstance(v, bool) and v > 0:
            st[id_key] = v

    ph = raw.get("active_plan_hash")
    if isinstance(ph, str) and ph.strip():
        st["active_plan_hash"] = ph.strip()[:128]

    cp = raw.get("creation_preference")
    if cp in VALID_CREATION_PREFS:
        st["creation_preference"] = cp

    cs = raw.get("conversation_status")
    if cs in VALID_CONVERSATION_STATUSES:
        st["conversation_status"] = cs

    ireqs = raw.get("interaction_requirements")
    if isinstance(ireqs, list):
        seen = []
        for x in ireqs:
            if isinstance(x, str) and x.strip():
                sx = guardrails.redact_text(x.strip(), 80)
                if sx not in seen:
                    seen.append(sx)
        st["interaction_requirements"] = seen[:10]

    st["confirmed_requirements"] = _build_confirmed(st)
    st["missing_requirements"] = compute_missing_requirements(st)
    return st


def _build_confirmed(st: dict) -> dict:
    keys = (
        "learning_subject", "grade_level", "learning_topic", "learning_objective",
        "question_count", "question_type", "preferred_model_kind",
        "selected_model_id", "selected_player_id", "selected_exam_id",
        "game_mechanic", "creation_preference",
    )
    out = {}
    for k in keys:
        v = st.get(k)
        if k == "creation_preference":
            if v in ("reuse", "new"):
                out[k] = v
        elif v is not None:
            out[k] = v
    if st.get("interaction_requirements"):
        out["interaction_requirements"] = list(st["interaction_requirements"])
    return out


def compute_missing_requirements(st: dict) -> list:
    """Xác định các thông tin cốt lõi thực sự còn thiếu (không hỏi lại thông tin đã có)."""
    missing = []
    has_content = bool(
        st.get("learning_subject")
        or st.get("learning_topic")
        or st.get("selected_exam_id")
        or st.get("game_mechanic")
    )
    if not has_content:
        missing.append("learning_topic")
    has_interaction = bool(
        st.get("preferred_model_kind")
        or st.get("selected_model_id")
        or st.get("interaction_requirements")
    )
    if not has_interaction:
        missing.append("preferred_model_kind")
    return missing


def _detect_model_kind(message: str):
    """Nhận diện loại Model / tương tác người dùng nêu rõ (không nhầm 'tiếng Anh' thành 'image')."""
    f = guardrails.fold_text(message or "")
    if not f:
        return None
    if re.search(r"\b(?:chi\s+(?:dung|choi)\s+chuot|khong\s+can\s+camera|mouse[\s-]?only|bang\s+chuot\s+thoi)\b", f):
        return "mouse"
    if re.search(r"\b(?:am\s+thanh|giong\s+noi|micro|\bmic\b|\baudio\b|vo\s+tay)\b", f):
        return "audio"
    if re.search(r"\b(?:ban\s+tay|mediapipe|\bhands\b|cu\s+chi\s+tay|nam\s+tay|xoe\s+tay)\b", f):
        return "hands"
    if re.search(r"\b(?:tu\s+the|\bpose\b|cu\s+chi\s+co\s+the|dong\s+tac\s+co\s+the)\b", f):
        return "pose"
    if re.search(r"\b(?:model\s+hinh\s+anh|mo\s+hinh\s+hinh\s+anh|hinh\s+anh|\bimage\b|nhan\s+dien\s+anh)\b", f):
        return "image"
    return None


def _detect_topic(message: str, current_state: dict):
    """Trích chủ đề học tập từ câu tường minh hoặc câu trả lời ngắn bổ sung (vd 'Phép nhân', 'Chủ đề động vật')."""
    raw = (message or "").strip()
    f = guardrails.fold_text(raw)
    f_clean = f.strip(" .,:;!?")
    if not f_clean:
        return None
    # Mẫu có nhãn tường minh: "chủ đề X", "bài học X", "về X" (khớp cả có dấu lẫn không dấu)
    m = re.search(r"(?:chủ\s+đề|chu\s+de|bài\s+học|bai\s+hoc|phần|phan|về|ve)\s+([^\.,;\n]{2,80})", raw, re.I)
    if m:
        cand = m.group(1).strip(" .,:;!?")
        cand = re.sub(
            r"\s+(?:gồm|gom|có|co|với|voi|bằng|bang|dùng|dung|sử\s+dụng|su\s+dung|\d{1,2}\s+(?:câu|cau)).*$",
            "",
            cand,
            flags=re.I,
        ).strip(" .,:;!?")
        if len(cand) >= 2:
            return cand[:80]
    # Câu trả lời ngắn bổ sung chủ đề trong multi-turn (vd "Phép nhân", "Động vật", "Bảng cửu chương")
    # Chỉ nhận khi câu ngắn (<= 6 từ), không phải chỉ định số câu / lớp / model / preference thuần túy
    words = raw.split()
    if 1 <= len(words) <= 6 and not _CHAT_AGREE_RE.match(f_clean):
        is_only_grade = bool(re.fullmatch(r"(?:lop|khoi)\s*\d{1,2}", f_clean))
        is_only_count = bool(re.fullmatch(r"\d{1,2}\s*(?:cau(?:\s+hoi)?|questions?)", f_clean))
        is_only_kind = bool(_detect_model_kind(raw)) and len(words) <= 4
        is_only_pref = bool(_EXPLICIT_NEW_PREF_RE.search(f_clean) or _EXPLICIT_REUSE_PREF_RE.search(f_clean))
        is_only_subject = any(pat.fullmatch(f_clean) for _, pat in _SUBJECT_PATTERNS)
        has_verb = bool(re.search(r"\b(?:tao|lam|soan|doi|chuyen|xem|show|liet\s+ke|duyet|huy)\b", f_clean))
        if not any((is_only_grade, is_only_count, is_only_kind, is_only_pref, is_only_subject, has_verb)):
            if current_state.get("learning_subject") or current_state.get("grade_level") or current_state.get("conversation_status") == "collecting":
                return raw.strip(" .,:;!?")[:80]
    return None


def _match_resource_by_name(message: str, rows: list):
    f = guardrails.fold_text(message or "")
    if not f or not rows:
        return None
    hits = []
    for r in rows:
        name = (r.get("name") or "").strip()
        fn = guardrails.fold_text(name)
        if len(fn) >= 4 and fn in f:
            hits.append((len(fn), r))
    if not hits:
        return None
    hits.sort(key=lambda x: x[0], reverse=True)
    return hits[0][1]


def classify_turn_intent(message: str, current_state: dict) -> str:
    """Phân loại ý định lượt tin nhắn trong ngữ cảnh conversation hiện tại."""
    f = guardrails.fold_text(message or "").strip()
    if not f:
        return "other"
    if _NEW_TASK_RE.search(f):
        return "new_task"
    if _CHAT_AGREE_RE.match(f):
        return "chat_agreement"
    if re.search(r"\b(?:bao\s+nhieu\s+cau|so\s+cau|co\s+nhung\s+(?:game|tro\s+choi|model)|show\s+game|liet\s+ke)\b", f) and not re.search(r"\b(?:tao|ghep|soan|viet)\b", f):
        return "info_query"
    if _CHANGE_INTENT_RE.search(f):
        return "modify_requirement"
    if any(current_state.get(k) for k in ("learning_subject", "grade_level", "learning_topic", "preferred_model_kind", "question_count", "selected_model_id", "selected_player_id")):
        return "supplement_requirement"
    return "new_requirement"


def update_state_from_turn(current_state: dict, message: str, registry: dict = None, request_hints: dict = None):
    """Cập nhật structured conversation state từ tin nhắn mới + hints UI.

    Quy tắc bất biến:
    - Không ghi đè thông tin đã xác nhận bằng None hay giá trị mặc định.
    - Thông tin mới rõ ràng từ người dùng thay thế đúng trường tương ứng.
    - Nếu thay đổi làm mất hiệu lực draft cũ → đặt `invalidated_draft = True` và xóa `active_draft_id` / `active_plan_hash`.
    Trả về `(updated_state, turn_meta)`.
    """
    st = normalize_state(current_state)
    reg = registry if isinstance(registry, dict) else {}
    hints = request_hints if isinstance(request_hints, dict) else {}
    f = guardrails.fold_text(message or "")
    turn_intent = classify_turn_intent(message, st)

    if turn_intent == "new_task":
        st = new_state(conversation_id=st.get("conversation_id"), user_id=st.get("user_id"))
        return st, {"turn_intent": "new_task", "changed_fields": ["reset"], "invalidated_draft": True, "explicit_model_id_requested": None, "explicit_player_id_requested": None}

    changed = []
    invalidated_draft = False

    # 1. Subject
    for subj_label, pat in _SUBJECT_PATTERNS:
        if pat.search(f):
            if st["learning_subject"] != subj_label:
                st["learning_subject"] = subj_label
                changed.append("learning_subject")
            break

    # 2. Grade level
    m_grade = _GRADE_RE.search(f)
    if m_grade:
        g = "Lớp %s" % m_grade.group(1)
        if st["grade_level"] != g:
            st["grade_level"] = g
            changed.append("grade_level")

    # 3. Question count
    m_cnt = _QCOUNT_RE.search(f)
    if m_cnt:
        cnt = int(m_cnt.group(1))
        if 1 <= cnt <= 100 and st["question_count"] != cnt:
            st["question_count"] = cnt
            changed.append("question_count")

    # 4. Question type
    if re.search(r"\b(?:dung\s*[/\-]?\s*sai|true\s*[/\-]?\s*false)\b", f):
        if st["question_type"] != "truefalse":
            st["question_type"] = "truefalse"
            changed.append("question_type")
    elif re.search(r"\b(?:trac\s+nghiem|abcd|4\s+dap\s+an|3\s+dap\s+an)\b", f):
        if st["question_type"] != "single":
            st["question_type"] = "single"
            changed.append("question_type")
    elif re.search(r"\b(?:vong\s+quay\s+chon\s+ten|danh\s+sach\s+ten|boc\s+tham\s+ten)\b", f):
        if st["question_type"] != "texts":
            st["question_type"] = "texts"
            changed.append("question_type")

    # 5. Game mechanic
    for mech_name, pat in _MECHANIC_PATTERNS:
        if pat.search(f):
            if st["game_mechanic"] != mech_name:
                st["game_mechanic"] = mech_name
                changed.append("game_mechanic")
            break

    # 6. Creation preference (explicit constraints)
    gen_mode = hints.get("generation_mode")
    if gen_mode == "generate_new" or _EXPLICIT_NEW_PREF_RE.search(f):
        if st["creation_preference"] != "new":
            st["creation_preference"] = "new"
            st["selected_player_id"] = None
            changed.append("creation_preference")
    elif gen_mode == "reuse_existing" or _EXPLICIT_REUSE_PREF_RE.search(f):
        if st["creation_preference"] != "reuse":
            st["creation_preference"] = "reuse"
            changed.append("creation_preference")

    # 7. Explicit Model / Player / Exam IDs from UI hints or exact Catalog names
    explicit_model_id_req = hints.get("selected_model_id")
    explicit_player_id_req = hints.get("selected_player_id")
    explicit_exam_id_req = hints.get("selected_exam_id")

    if explicit_model_id_req is not None:
        if st["selected_model_id"] != explicit_model_id_req:
            st["selected_model_id"] = explicit_model_id_req
            changed.append("selected_model_id")
        m_row = next((m for m in (reg.get("models") or []) if m.get("id") == explicit_model_id_req), None)
        if m_row and m_row.get("kind") in VALID_MODEL_KINDS:
            if st["preferred_model_kind"] != m_row["kind"]:
                st["preferred_model_kind"] = m_row["kind"]
                changed.append("preferred_model_kind")
    else:
        named_m = _match_resource_by_name(message, reg.get("models") or [])
        if named_m is not None:
            if st["selected_model_id"] != named_m["id"]:
                st["selected_model_id"] = named_m["id"]
                changed.append("selected_model_id")
            if named_m.get("kind") in VALID_MODEL_KINDS and st["preferred_model_kind"] != named_m["kind"]:
                st["preferred_model_kind"] = named_m["kind"]
                changed.append("preferred_model_kind")

    if explicit_player_id_req is not None:
        if st["selected_player_id"] != explicit_player_id_req:
            st["selected_player_id"] = explicit_player_id_req
            changed.append("selected_player_id")
    else:
        named_p = _match_resource_by_name(message, reg.get("players") or [])
        if named_p is not None and st["creation_preference"] != "new":
            if st["selected_player_id"] != named_p["id"]:
                st["selected_player_id"] = named_p["id"]
                changed.append("selected_player_id")

    if explicit_exam_id_req is not None:
        if st["selected_exam_id"] != explicit_exam_id_req:
            st["selected_exam_id"] = explicit_exam_id_req
            changed.append("selected_exam_id")
    else:
        named_e = _match_resource_by_name(message, reg.get("exams") or [])
        if named_e is not None:
            if st["selected_exam_id"] != named_e["id"]:
                st["selected_exam_id"] = named_e["id"]
                changed.append("selected_exam_id")

    # 8. Preferred model kind (when user mentions image / pose / hands / audio / mouse)
    new_kind = _detect_model_kind(message)
    if new_kind is not None:
        old_kind = st["preferred_model_kind"]
        if old_kind != new_kind:
            st["preferred_model_kind"] = new_kind
            changed.append("preferred_model_kind")
            # Nếu đổi kind (vd image -> audio) thì xóa model/player cũ không còn khớp kind mới
            if explicit_model_id_req is None and st["selected_model_id"] is not None:
                cur_m = next((m for m in (reg.get("models") or []) if m.get("id") == st["selected_model_id"]), None)
                if cur_m is None or cur_m.get("kind") != new_kind:
                    st["selected_model_id"] = None
            if explicit_player_id_req is None and st["selected_player_id"] is not None and new_kind != "mouse":
                cur_p = next((p for p in (reg.get("players") or []) if p.get("id") == st["selected_player_id"]), None)
                man = (cur_p or {}).get("manifest") or {}
                if new_kind not in (man.get("kinds") or []):
                    st["selected_player_id"] = None
        if new_kind not in st["interaction_requirements"]:
            st["interaction_requirements"] = [x for x in st["interaction_requirements"] if x not in VALID_MODEL_KINDS] + [new_kind]

    # 9. Topic (after model kind / subject / grade so we don't misclassify short kind/grade answers as topic)
    topic = _detect_topic(message, st)
    if topic and st["learning_topic"] != topic:
        st["learning_topic"] = topic
        changed.append("learning_topic")

    # 10. Invalidate active draft if any substantive requirement changed
    substantive = {
        "learning_subject", "grade_level", "learning_topic", "question_count", "question_type",
        "preferred_model_kind", "selected_model_id", "selected_player_id", "selected_exam_id",
        "game_mechanic", "creation_preference",
    }
    if st.get("active_draft_id") is not None and (substantive & set(changed)):
        st["active_draft_id"] = None
        st["active_plan_hash"] = None
        if st.get("conversation_status") in ("draft_pending", "approved"):
            st["conversation_status"] = "collecting"
        invalidated_draft = True

    st["confirmed_requirements"] = _build_confirmed(st)
    st["missing_requirements"] = compute_missing_requirements(st)
    if not st["missing_requirements"] and st["conversation_status"] == "collecting":
        st["conversation_status"] = "ready"

    return st, {
        "turn_intent": turn_intent,
        "changed_fields": changed,
        "invalidated_draft": invalidated_draft,
        "explicit_model_id_requested": explicit_model_id_req,
        "explicit_player_id_requested": explicit_player_id_req,
    }


def is_model_usable(model_row: dict) -> tuple:
    """Kiểm tra tính khả dụng thật của Model: readiness, status, runtime support, outputs, artifact URL."""
    if not isinstance(model_row, dict):
        return False, "Model không hợp lệ."
    if model_row.get("ready") is False:
        return False, "Artifact của model chưa sẵn sàng hoặc trả lỗi khi kiểm tra."
    status = str(model_row.get("status") or "ready").strip().lower()
    if status in ("broken", "error", "disabled", "placeholder"):
        return False, "Model đang ở trạng thái %s." % status
    kind = model_row.get("kind")
    if kind == "audio" and not chatbot_catalog.AUDIO_SUPPORTED:
        return False, "Runtime hiện chưa bật hỗ trợ model âm thanh (audio)."
    url = str(model_row.get("url") or "").strip()
    if url and any(p.search(url) for p in _BROKEN_URL_PATTERNS):
        return False, "URL artifact của model là placeholder hoặc không khả dụng."
    outputs = model_row.get("outputs") or []
    action_outs = [o for o in outputs if isinstance(o, dict) and isinstance(o.get("key"), str) and o.get("key").strip() and (o.get("role") or "action") != "empty"]
    if not action_outs:
        return False, "Model không có lớp output hành động hợp lệ."
    return True, ""


def resolve_grounded_model(state: dict, registry: dict, explicit_model_id=None) -> dict:
    """Grounded Model Selection theo đúng thứ tự ưu tiên từ Live Registry:
    1. Model cụ thể người dùng chọn (selected_model_id).
    2. Model kind người dùng yêu cầu (preferred_model_kind).
    Không bao giờ tự ý đổi kind (vd image -> hands/pose/audio/mouse), không chọn model broken/placeholder.
    Trả về dict: {status: 'selected'|'mouse_only'|'missing_model'|'forbidden_model'|'unspecified', model, alternatives, reason}.
    """
    models = (registry or {}).get("models") or []
    usable = []
    unusable_same_kind = []
    for m in models:
        ok, why = is_model_usable(m)
        if ok:
            usable.append(m)
        elif state.get("preferred_model_kind") and m.get("kind") == state.get("preferred_model_kind"):
            unusable_same_kind.append((m, why))

    req_mid = explicit_model_id if explicit_model_id is not None else state.get("selected_model_id")
    if req_mid is not None:
        hit = next((m for m in models if m.get("id") == req_mid), None)
        if hit is None:
            return {
                "status": "forbidden_model",
                "model": None,
                "alternatives": usable,
                "reason": "Model id=%s không tồn tại trong Catalog hoặc bạn không có quyền truy cập." % req_mid,
            }
        ok, why = is_model_usable(hit)
        if not ok and hit.get("status") != "broken":
            return {
                "status": "broken_model",
                "model": None,
                "alternatives": usable,
                "reason": 'Model "%s" hiện KHÔNG tải được artifact hoặc không khả dụng (%s). Vui lòng kiểm tra lại URL Teachable Machine hoặc chọn model khác.'
                % (hit.get("name") or "#%s" % req_mid, why),
            }
        return {"status": "selected", "model": hit, "alternatives": usable, "reason": ""}

    pref_kind = state.get("preferred_model_kind")
    if pref_kind == "mouse":
        return {"status": "mouse_only", "model": None, "alternatives": usable, "reason": ""}

    if pref_kind in ("image", "pose", "hands", "audio"):
        if pref_kind == "audio" and not chatbot_catalog.AUDIO_SUPPORTED:
            return {
                "status": "missing_model",
                "model": None,
                "alternatives": usable,
                "reason": "Runtime hiện chưa bật hỗ trợ model âm thanh (audio).",
            }
        same_kind = [m for m in usable if m.get("kind") == pref_kind]
        if same_kind:
            # Ưu tiên model có nhiều lớp action hơn (tránh model rỗng), giữ ổn định theo id
            same_kind.sort(
                key=lambda m: (
                    -sum(1 for o in (m.get("outputs") or []) if isinstance(o, dict) and (o.get("role") or "action") == "action"),
                    int(m.get("id") or 0),
                )
            )
            return {"status": "selected", "model": same_kind[0], "alternatives": same_kind, "reason": ""}
        if unusable_same_kind:
            bad_m, bad_why = unusable_same_kind[0]
            reason = 'Model loại "%s" ("%s") hiện không khả dụng (%s).' % (pref_kind, bad_m.get("name"), bad_why)
        else:
            reason = 'Trong Catalog hiện tại không có Model loại "%s" nào khả dụng mà bạn có quyền sử dụng.' % pref_kind
        return {"status": "missing_model", "model": None, "alternatives": usable, "reason": reason}

    return {"status": "unspecified", "model": None, "alternatives": usable, "reason": ""}


_ACTION_GROUPS = (
    frozenset(("grab", "fist", "close", "hold", "catch", "pinch", "nam", "giu")),
    frozenset(("release", "open", "drop", "palm", "let", "tha", "mo", "xoe")),
    frozenset(("left", "trai")),
    frozenset(("right", "phai")),
    frozenset(("up", "jump", "len", "nhay")),
    frozenset(("down", "duck", "xuong", "cui")),
)


def _semantic_score(ik: str, ok: str) -> int:
    fi = guardrails.fold_text(ik).strip()
    fo = guardrails.fold_text(ok).strip()
    if not fi or not fo:
        return 0
    if fi == fo:
        return 3
    for grp in _ACTION_GROUPS:
        if any(t in fi for t in grp) and any(t in fo for t in grp):
            return 2
    return 0


def semantic_mapping(manifest: dict, model_row: dict) -> dict:
    base = chatbot_catalog.auto_mapping(manifest, model_row)
    if not base or len(base) < 2:
        return base
    info = chatbot_catalog.describe_player(manifest)
    outs = {o["key"]: o.get("role") for o in (model_row.get("outputs") or []) if isinstance(o, dict) and isinstance(o.get("key"), str)}
    inputs = info.get("inputs") or []
    scored = []
    for inp in inputs:
        ik = inp.get("key")
        acc = inp.get("accepts") or ["action"]
        for ok, role in outs.items():
            if role in acc:
                sc = _semantic_score(ik, ok)
                if sc > 0:
                    scored.append((sc, bool(inp.get("required")), ik, ok))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    chosen, used = {}, set()
    for _, _, ik, ok in scored:
        if ik not in chosen and ok not in used:
            chosen[ik] = ok
            used.add(ok)
    for ik, ok in base.items():
        if ik not in chosen and ok not in used:
            chosen[ik] = ok
            used.add(ok)
    if len(chosen) == len(base) and chatbot_catalog.validate_mapping(manifest, model_row, chosen).get("ok"):
        return chosen
    return base


def _mechanic_similarity(mechanic: str, player_row: dict) -> float:
    if not mechanic:
        return 0.0
    m_toks = [t for t in re.findall(r"[a-z0-9]+", guardrails.fold_text(mechanic)) if len(t) >= 2]
    man = player_row.get("manifest") if isinstance(player_row.get("manifest"), dict) else {}
    p_toks = [t for t in re.findall(r"[a-z0-9]+", guardrails.fold_text((player_row.get("name") or "") + " " + (man.get("description") or ""))) if len(t) >= 2]
    if not m_toks or not p_toks:
        return 0.0
    score = 0.0
    for mt in m_toks:
        if mt in p_toks:
            score += 1.0
        else:
            best = max((difflib.SequenceMatcher(None, mt, pt).ratio() for pt in p_toks if len(mt) >= 4 and len(pt) >= 4), default=0.0)
            if best >= 0.75:
                score += best
    return score / len(m_toks)


def resolve_grounded_player(state: dict, model_row: dict, registry: dict, explicit_player_id=None) -> dict:
    """Deterministic Player Compatibility (Hard Filters → Relevance Ranking).

    Không bao giờ fallback chọn đại Player đầu tiên khi không có Player nào qua Hard Filters.
    Trả về: {action: 'REUSE'|'GENERATE'|'ASK_CLARIFY'|'ERROR', player, mapping, candidates, reason}.
    """
    players = (registry or {}).get("players") or []
    pref = state.get("creation_preference") or "unspecified"
    req_pid = explicit_player_id if explicit_player_id is not None else state.get("selected_player_id")
    wants_texts = state.get("question_type") == "texts"
    wants_exam = not wants_texts

    # Ràng buộc cứng: người dùng yêu cầu tạo Player mới → KHÔNG ĐƯỢC REUSE
    if pref == "new":
        if explicit_player_id is not None:
            return {
                "action": "ERROR",
                "player": None,
                "mapping": {},
                "candidates": [],
                "reason": "Không thể vừa chọn Player có sẵn vừa yêu cầu tạo Player mới.",
            }
        return {"action": "GENERATE", "player": None, "mapping": {}, "candidates": [], "reason": "Người dùng yêu cầu tạo Player mới."}

    # Kiểm tra Hard Filters cho từng player
    def check_player(p):
        st_p = p.get("status")
        if st_p is not None and st_p != "approved":
            return False, None, "Trình chơi chưa được phê duyệt."
        man = p.get("manifest") if isinstance(p.get("manifest"), dict) else {}
        info = chatbot_catalog.describe_player(man)
        is_texts = info.get("gameKind") == "texts"
        is_exam = info.get("gameKind") == "questions"
        if wants_texts and not is_texts:
            return False, None, "Trình chơi không hỗ trợ danh sách chữ (texts)."
        if wants_exam and not is_exam and state.get("selected_exam_id") is not None:
            return False, None, "Trình chơi không nhận bộ câu hỏi (exam)."
        if model_row is not None:
            if not info.get("needsModel"):
                return False, None, "Trình chơi không hỗ trợ gắn Model."
            if model_row.get("kind") not in (info.get("runtimeKinds") or []):
                return False, None, 'Trình chơi không hỗ trợ model kind="%s".' % model_row.get("kind")
            mp = semantic_mapping(man, model_row)
            chk = chatbot_catalog.validate_mapping(man, model_row, mp)
            if not chk.get("ok"):
                return False, None, "; ".join(chk.get("errors") or ["Không ánh xạ được inputs của trình chơi với outputs của Model."])
            return True, mp, ""
        return True, {}, ""

    if req_pid is not None:
        hit = next((p for p in players if p.get("id") == req_pid), None)
        if hit is None:
            return {
                "action": "ERROR",
                "player": None,
                "mapping": {},
                "candidates": [],
                "reason": "Player id=%s không tồn tại trong Catalog hoặc bạn không có quyền truy cập." % req_pid,
            }
        ok, mp, why = check_player(hit)
        if not ok:
            return {
                "action": "ERROR",
                "player": None,
                "mapping": {},
                "candidates": [],
                "reason": 'Player "%s" không tương thích với yêu cầu hiện tại: %s' % (hit.get("name"), why),
            }
        return {"action": "REUSE", "player": hit, "mapping": mp, "candidates": [hit], "reason": ""}

    # Hard-filter toàn bộ Catalog
    passed = []
    mech = state.get("game_mechanic")
    for p in players:
        ok, mp, _ = check_player(p)
        if not ok:
            continue
        man = p.get("manifest") if isinstance(p.get("manifest"), dict) else {}
        info = chatbot_catalog.describe_player(man)
        all_inputs = [i for i in (man.get("inputs") or []) if isinstance(i.get("key"), str)]
        covered = sum(1 for i in all_inputs if isinstance(mp.get(i.get("key")), str) and mp.get(i.get("key"))) if model_row else 0
        coverage = (covered / len(all_inputs)) if (all_inputs and model_row) else 1.0
        mech_sim = _mechanic_similarity(mech, p) if mech else 0.0
        exam_fit = 1 if (wants_exam and info.get("gameKind") == "questions") or (wants_texts and info.get("gameKind") == "texts") else 0
        passed.append(((mech_sim, coverage, exam_fit, -int(p.get("id") or 0)), p, mp, mech_sim))

    if not passed:
        if pref == "reuse":
            return {
                "action": "ASK_CLARIFY",
                "player": None,
                "mapping": {},
                "candidates": [],
                "reason": "Không có trình chơi nào trong kho tương thích với Model/yêu cầu hiện tại. Bạn có muốn chuyển sang tạo trò chơi mới hoặc chọn cách điều khiển khác không?",
            }
        return {
            "action": "GENERATE",
            "player": None,
            "mapping": {},
            "candidates": [],
            "reason": "Không có trình chơi nào trong kho tương thích với yêu cầu hiện tại; chuyển sang tạo bản nháp mới.",
        }

    # Nếu người dùng nêu rõ một cơ chế game đặc thù (không phải quiz chung) mà không có player nào khớp cơ chế đó → không ép REUSE sai
    if mech and mech != "quiz trắc nghiệm":
        matched_mech = [x for x in passed if x[3] >= 0.5]
        if matched_mech:
            passed = matched_mech
        elif pref != "reuse":
            return {
                "action": "GENERATE",
                "player": None,
                "mapping": {},
                "candidates": [],
                "reason": 'Trong kho chưa có trình chơi khớp cơ chế "%s"; chuyển sang tạo bản nháp mới.' % mech,
            }

    passed.sort(key=lambda x: x[0], reverse=True)
    _, best_p, best_mp, _ = passed[0]
    return {
        "action": "REUSE",
        "player": best_p,
        "mapping": best_mp,
        "candidates": [x[1] for x in passed],
        "reason": "",
    }


def format_context_for_llm(state: dict, history: list = None) -> str:
    """Định dạng ngữ cảnh gọn, an toàn (không gửi toàn bộ lịch sử thừa hay dữ liệu nhạy cảm) cho LLM router."""
    confirmed = state.get("confirmed_requirements") or {}
    lines = []
    if confirmed:
        lines.append("[Yêu cầu đã tích lũy trong cuộc trò chuyện hiện tại]:")
        for k, v in confirmed.items():
            lines.append("- %s: %s" % (k, v))
    missing = state.get("missing_requirements") or []
    if missing:
        lines.append("[Thông tin còn thiếu]: " + ", ".join(missing))
    recent = [h for h in (history or []) if isinstance(h, dict) and isinstance(h.get("text"), str) and h["text"].strip()][-4:]
    if recent:
        lines.append("[Các lượt gần nhất]:")
        for h in recent:
            role = "Giáo viên" if h.get("role") == "user" else "AI"
            lines.append("- %s: %s" % (role, guardrails.redact_text(h["text"].strip(), 220)))
    return "\n".join(lines)
