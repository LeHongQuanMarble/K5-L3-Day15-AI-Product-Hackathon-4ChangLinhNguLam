"""Luồng "Soạn trò chơi" mới: hỏi đủ ý chính → Kế hoạch → giáo viên duyệt → tạo game → chơi thử → sửa theo ý → lưu.

Chỉ quan tâm HAI thông tin thiết yếu (trình chơi dùng lại được cho mọi môn nên KHÔNG hỏi môn học/chủ đề):
  1. Số đáp án của mỗi câu hỏi: 2 (Đúng/Sai), 3 hoặc 4 (A–D).
  2. Học sinh điều khiển bằng gì: hình ảnh, tư thế, âm thanh, hay chỉ chuột (không cần model). Chưa có model cũng không sao:
     người dùng tạo model sau ở "Mô hình tương tác" rồi gắn khi tạo ứng dụng.
Đủ hai thông tin thì mới lập Kế hoạch (chưa tốn lượt sinh game). Giáo viên duyệt kế hoạch thì mới tạo game (dùng lại trình chơi có sẵn
nếu có cái khớp, nếu không thì AI viết game mới thành bản nháp). Sau khi chơi thử, giáo viên nói muốn sửa gì thì AI sửa bản nháp
(tối đa MAX_FIXES lần); ưng thì lưu thành trình chơi Nháp (vẫn chờ Admin duyệt công khai như trước).

Trạng thái (brief) do trình duyệt giữ và gửi lại mỗi lượt; máy chủ tính lại kế hoạch từ brief nên không tin kế hoạch từ máy khách.
Chỉ thư viện chuẩn. Lõi sinh HTML dùng lại codebase/agent.py (_run_generate_html, kiểm check_game + cờ an toàn).
"""
import difflib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(os.path.dirname(HERE), "codebase")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import agent  # noqa: E402  (Shared Core)
import agent_bridge  # noqa: E402
import ai  # noqa: E402
import contract  # noqa: E402
import guardrails  # noqa: E402
import llm  # noqa: E402
import store  # noqa: E402

MAX_FIXES = 5
MAX_FEEDBACK = 1500
KIND_VI = {"image": "hình ảnh (camera)", "pose": "tư thế", "audio": "âm thanh", "none": "chỉ chuột"}
ASK_DISAMBIGUATE = "Bạn muốn xem các trò chơi có sẵn trong kho hay soạn một trò chơi mới theo ý riêng?"
CHIPS_DISAMBIGUATE = ["Xem các game trong kho", "Soạn trò chơi mới"]
ASK_ANSWERS = "Mỗi câu hỏi trong game có mấy đáp án: 2 (Đúng/Sai), 3 hay 4 (A, B, C, D)?"
CHIPS_ANSWERS = ["4 đáp án (A, B, C, D)", "2 đáp án (Đúng/Sai)", "3 đáp án"]
ASK_INTERACTION = ("Học sinh điều khiển game bằng gì: hình ảnh (camera), tư thế, âm thanh, hay chỉ chuột (không cần model)? "
                   "Chưa có model cũng không sao, bạn tạo sau được.")
CHIPS_INTERACTION = ["Chỉ dùng chuột", "Hình ảnh (camera)", "Tư thế", "Âm thanh"]

EXTRACT_SYSTEM = """Bạn đọc yêu cầu của giáo viên để soạn một game ôn tập trắc nghiệm. KHÔNG quan tâm môn học hay chủ đề (trình chơi dùng lại cho mọi môn).
Chỉ trích hai thông tin; TUYỆT ĐỐI KHÔNG tự đoán — để null nếu giáo viên CHƯA nói rõ trong câu:
- answers: số đáp án mỗi câu hỏi, một trong 2 (Đúng/Sai), 3, 4 (A–D). Không nêu số đáp án thì PHẢI là null.
- interaction: "image" (camera/hình ảnh), "pose" (tư thế cơ thể), "audio" (âm thanh/giọng nói), hoặc "none" (chỉ chuột/bàn phím, không dùng model). Không nêu cách điều khiển thì PHẢI là null.
  Giáo viên không cần có sẵn model, chỉ cần nói họ định dùng loại nào.
Thêm: intent = "create_game" nếu họ muốn tạo/soạn/sửa một game, ngược lại "other" (hỏi danh sách game trong kho, hỏi thông tin, chào hỏi...);
notes = yêu cầu riêng về cách chơi/giao diện nếu có (≤200 ký tự, không lặp lại số đáp án và cách điều khiển), name = tên game ngắn gợi ý (≤60 ký tự) hoặc "".
Trả ĐÚNG MỘT khối JSON: {"intent": "...", "answers": 4 hoặc null, "interaction": "..." hoặc null, "notes": "", "name": ""}"""


def fold(s):
    return guardrails.fold_text(s or "")


_CATALOG_LIST_PATTERNS = (
    re.compile(r"\b(?:show|xem|liet ke|danh sach|hien thi|cho xem|ke ten)\b.*\b(?:game|tro choi|trinh choi|kho)\b"),
    re.compile(r"\b(?:trong kho|kho tro choi|kho game|catalog|danh muc)\b.*\b(?:co nhung|co gi|co game|co tro|nhung tro|nhung game|nao|bao nhieu|may|show|xem|liet ke)\b"),
    re.compile(r"\b(?:co nhung|nhung|cac)\s+(?:game|tro choi|trinh choi)\s+(?:nao|gi|trong kho|co san|hien co)\b"),
    re.compile(r"\b(?:game|tro choi|trinh choi)\s+(?:trong kho|co san|hien co)\s+(?:co gi|co nhung|la gi|gom nhung|nao)\b"),
)


def is_catalog_list_query(message):
    """Nhận diện câu hỏi xem/liệt kê danh sách trò chơi hiện có trong kho."""
    f = fold(message)
    if not f:
        return False
    return any(p.search(f) for p in _CATALOG_LIST_PATTERNS)


def _load_registry(c, user, include_showcase=True):
    try:
        return agent_bridge.trusted_registry(c, user=user, include_showcase=include_showcase)
    except TypeError:
        return agent_bridge.trusted_registry(c, user)


_KIND_LABEL = {"image": "Hình ảnh", "pose": "Tư thế", "hands": "Bàn tay", "audio": "Âm thanh"}


def _catalog_reply(c, user, prev_brief):
    reg = _load_registry(c, user, include_showcase=True)
    players = reg.get("players") or []
    items = []
    lines = []
    for p in players:
        man = p.get("manifest") if isinstance(p.get("manifest"), dict) else {}
        kinds = [_KIND_LABEL.get(k, k) for k in (man.get("kinds") or []) if isinstance(k, str)]
        is_quiz = man.get("questions") == "exam" or (man.get("content") or {}).get("kind") == "questions"
        ctrl = ("Chuột + " + ", ".join(kinds)) if kinds else "Chỉ chuột"
        desc = str(man.get("description") or "").strip()
        items.append({
            "id": p["id"],
            "name": p["name"],
            "description": desc,
            "kinds": kinds,
            "control": ctrl,
            "game_kind": "Trắc nghiệm" if is_quiz else "Danh sách / Tương tác",
            "preview_url": "/api/players/%d/try" % p["id"],
        })
        lines.append("• %s (#%d) — %s · Điều khiển: %s" % (p["name"], p["id"], "Trắc nghiệm" if is_quiz else "Tương tác", ctrl))
    if items:
        msg = "Hiện trong kho có %d trò chơi sẵn sàng dùng:\n%s\n\nBạn có thể bấm Chơi thử ngay bên dưới, hoặc mô tả trò chơi mới bạn muốn soạn." % (
            len(items), "\n".join(lines)
        )
    else:
        msg = "Hiện kho trò chơi chưa có trình chơi nào được duyệt. Bạn muốn soạn một trò chơi mới không?"
    notes = [{"tool": "list_players", "status": "ok", "input": "kho trò chơi", "output": "%d trò chơi trong kho" % len(items), "ms": 0}]
    return {
        "stage": "catalog",
        "message": msg,
        "players": items,
        "quick_replies": ["Soạn trò chơi 4 đáp án (A, B, C, D)", "Soạn trò chơi 2 đáp án (Đúng/Sai)", "Soạn trò chơi mới"],
        "brief": clean_brief(prev_brief),
        "notes": notes,
    }


# ---------- đọc ý chính từ lời giáo viên ----------
def keywords(message):
    """Đọc bằng từ khoá (dùng khi chưa nối model, hoặc khi model lỗi). Trả {answers, interaction, intent}."""
    f = fold(message)
    answers = None
    if re.search(r"dung ?[/-]? ?sai|true ?[/-]? ?false|\bt ?/ ?f\b", f):
        answers = 2
    else:
        m = re.search(r"\b([2-4])\s*(dap an|lua chon|phuong an)", f)
        if m:
            answers = int(m.group(1))
        elif re.search(r"abcd|a, ?b, ?c, ?d|bon dap an", f):
            answers = 4
        elif re.search(r"\babc\b|a, ?b, ?c\b|ba dap an", f):
            answers = 3
    interaction = None
    if re.search(r"chi (dung |can |choi )?(bang )?(chuot|ban phim|cam ung)|chuot thoi|khong (can |dung |co )?(model|mo hinh|camera|cam)", f):
        interaction = "none"
    elif re.search(r"am thanh|giong noi|vo tay|micro|\bmic\b|tieng noi|tieng dong", f):
        interaction = "audio"
    elif re.search(r"tu the|\bpose\b", f):
        interaction = "pose"
    elif re.search(r"hinh anh|camera|cu chi|ban tay|(?<!tieng )\banh\b", f):
        interaction = "image"
    intent = "other" if is_catalog_list_query(message) else (
        "create_game" if re.search(r"game|tro choi|quiz|cau hoi|soan|tao |dap an|chuot|camera|am thanh|tu the|hinh anh", f) else "other"
    )
    return {"answers": answers, "interaction": interaction, "intent": intent}


def _parse_extract_json(reply_text):
    """Trích JSON từ phản hồi EXTRACT_SYSTEM (không đòi trường 'decision' như routing JSON)."""
    if not isinstance(reply_text, str):
        return None
    stripped = reply_text.strip()
    if not stripped:
        return None
    candidates = []
    m = agent.JSON_FENCE_RE.search(stripped)
    if m:
        candidates.append(m.group(1).strip())
    if stripped.startswith("{") and stripped.endswith("}"):
        candidates.append(stripped)
    else:
        first, last = stripped.find("{"), stripped.rfind("}")
        if 0 <= first < last:
            candidates.append(stripped[first:last + 1])
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except ValueError:
            continue
        if isinstance(obj, dict) and any(k in obj for k in ("intent", "answers", "interaction")):
            return obj
    return None


def _llm_extract(message, prev):
    """Một lượt gọi model đọc ý chính. Trả dict hoặc None (chưa nối model / model trả không đúng dạng)."""
    if llm._real_model() is None:
        return None
    ctx = "Thông tin đã có: %s\n\nLời giáo viên: %s" % (json.dumps({k: prev.get(k) for k in ("answers", "interaction")}, ensure_ascii=False), message)
    reply = ai.call_model(EXTRACT_SYSTEM, ctx)
    return _parse_extract_json(reply.get("text") or "")


_FORCE_NEW_RE = re.compile(
    r"(?:dung|khong|ko|k)\s+(?:dung|xai|chon|lay)(?:\s+lai)?\s+(?:game\s+)?(?:quiz|cu|co san|trong kho)"
    r"|(?:tao|viet|lam|sinh|doi)\s+(?:mot\s+)?(?:game|tro choi|trinh choi)\s+(?:khac|moi(?:\s+hoan toan)?)"
    r"|(?:khong|dung)\s+dung\s+lai"
)


def wants_new_game(message):
    """Nhận diện khi giáo viên yêu cầu viết game mới / không dùng lại game có sẵn (vd Quiz)."""
    return bool(_FORCE_NEW_RE.search(fold(message)))


_GENERIC_TOKENS = frozenset((
    "tao", "lam", "soan", "viet", "sinh", "them", "muon", "can", "hay", "giup", "cho", "cua", "voi", "bang", "tu",
    "mot", "cac", "nhung", "nay", "kia", "nao", "di", "nhe", "nha", "a", "b", "c", "d", "e", "f", "t", "abcd", "abc",
    "game", "tro", "choi", "trinh", "quiz", "quizz", "trac", "nghiem", "on", "tap", "cau", "hoi", "dap", "an", "lua", "chon",
    "phuong", "dung", "sai", "true", "false", "bon", "ba", "hai", "2", "3", "4", "may", "so", "moi", "khac", "rieng",
    "chuot", "ban", "phim", "cam", "ung", "hinh", "anh", "camera", "tu", "the", "pose", "am", "thanh", "giong", "noi",
    "micro", "mic", "tay", "cu", "chi", "model", "mo", "kho", "trong", "co", "san", "chi", "khong", "khong", "dung",
    "lai", "cu", "hoan", "toan", "toi", "minh", "em", "co", "thay", "hoc", "sinh", "lop", "mon", "vui", "nhe", "1",
    "toan", "van", "ly", "hoa", "su", "dia", "lich", "tieng", "viet", "khoa", "tu", "nhien", "xa", "hoi", "tin", "ngoai",
    "ngu", "nhac", "my", "thuat", "dao", "duc", "cong", "dan", "va", "hoac", "de", "theo", "y", "ve", "xai", "lay",
))


def _concept_tokens(text):
    """Tách các từ khóa chủ đề/cơ chế game đặc trưng (vd 'sut', 'penaty', 'dua', 'xe', 'cau', 'long')."""
    toks = re.findall(r"[a-z0-9]+", fold(text))
    return [t for t in toks if len(t) >= 2 and t not in _GENERIC_TOKENS]


def _fuzzy_token_match(tok, target_tokens):
    if tok in target_tokens:
        return 1.0
    best = 0.0
    for tt in target_tokens:
        if len(tok) >= 4 and len(tt) >= 4:
            r = difflib.SequenceMatcher(None, tok, tt).ratio()
            if r > best:
                best = r
    return best if best >= 0.72 else 0.0


def _player_concept_score(concept_tokens, player):
    """Điểm khớp ngữ nghĩa/tên giữa ý tưởng game giáo viên nêu và một Player trong kho."""
    if not concept_tokens:
        return 0.0
    man = player.get("manifest") if isinstance(player.get("manifest"), dict) else {}
    name_toks = [t for t in re.findall(r"[a-z0-9]+", fold(player.get("name") or "")) if len(t) >= 2]
    desc_toks = [t for t in re.findall(r"[a-z0-9]+", fold(man.get("description") or "")) if len(t) >= 2]
    score = 0.0
    for ct in concept_tokens:
        nm = _fuzzy_token_match(ct, name_toks)
        if nm > 0:
            score += nm * 2.0
        else:
            dm = _fuzzy_token_match(ct, desc_toks)
            if dm > 0:
                score += dm * 0.8
    return score


def _is_start_new_flow_chip(message):
    f = fold(message).strip()
    return f in ("soan tro choi moi", "tao tro choi moi", "soan game moi", "tao game moi")


def _needs_disambiguate(message, prev_brief, kw):
    """Câu yêu cầu mơ hồ (chưa rõ muốn xem game trong kho hay soạn game mới) → hỏi câu tách riêng."""
    if prev_brief.get("mode_confirmed") or prev_brief.get("answers") or prev_brief.get("interaction"):
        return False
    if kw["answers"] is not None or kw["interaction"] is not None:
        return False
    if _is_start_new_flow_chip(message):
        return False
    f = fold(message)
    if re.search(r"\b(?:kho|trong kho|co san|catalog)\b", f):
        return True
    if not _concept_tokens(message) and not re.search(r"on tap|trac nghiem|quiz", f):
        return True
    return False


def _is_fresh_game_idea(message, prev_brief, kw):
    """Người dùng đổi sang yêu cầu một game hoàn toàn mới khi brief cũ đã có thông tin."""
    if not (prev_brief.get("answers") or prev_brief.get("interaction")):
        return False
    if wants_new_game(message):
        return False
    f = fold(message)
    if not re.search(r"\b(?:tao|lam|soan)\s+(?:mot\s+)?(?:game|tro choi)\b", f):
        return False
    new_concepts = _concept_tokens(message)
    old_concepts = _concept_tokens((prev_brief.get("notes") or "") + " " + (prev_brief.get("name") or ""))
    if new_concepts and set(new_concepts) != set(old_concepts):
        return True
    if prev_brief.get("answers") and prev_brief.get("interaction") and kw["answers"] is None and kw["interaction"] is None:
        return True
    return False


def clean_brief(b):
    b = b if isinstance(b, dict) else {}
    ans = b.get("answers")
    ans = ans if isinstance(ans, int) and not isinstance(ans, bool) and ans in (2, 3, 4) else None
    inter = b.get("interaction") if b.get("interaction") in ("none", "image", "pose", "audio") else None
    out = {"answers": ans, "interaction": inter, "notes": str(b.get("notes") or "")[:300], "name": str(b.get("name") or "")[:80]}
    if b.get("force_new") is True:
        out["force_new"] = True
    if b.get("mode_confirmed") is True:
        out["mode_confirmed"] = True
    return out


def merge(prev, message):
    """Gộp lời mới vào brief cũ: giá trị mới nói thì ghi đè, chưa nói thì giữ cái cũ. Trả (brief, intent, cách đọc)."""
    prev = clean_brief(prev)
    kw = keywords(message)
    if _is_start_new_flow_chip(message):
        return {"answers": None, "interaction": None, "notes": "", "name": "", "mode_confirmed": True}, "create_game", "từ khoá"
    if _is_fresh_game_idea(message, prev, kw):
        prev = clean_brief({"mode_confirmed": True})
    got, how = None, "từ khoá"
    try:
        got = _llm_extract(message, prev)
        if got is not None:
            how = "model"
    except ai.ProviderError:
        how = "từ khoá (model lỗi)"
    new = clean_brief(got or {})
    answers = new["answers"] or kw["answers"] or prev["answers"]
    inter = new["interaction"] or kw["interaction"] or prev["interaction"]
    force_new = bool(prev.get("force_new") or wants_new_game(message))
    mode_confirmed = bool(prev.get("mode_confirmed") or answers or inter or _concept_tokens(message))
    intent = (got or {}).get("intent") or kw["intent"]
    if any(prev.get(k) for k in ("answers", "interaction")) or force_new:
        intent = "create_game"  # đang giữa chừng một game: lời tiếp theo là trả lời cho nó
    if prev["notes"] and new["notes"] and fold(new["notes"]) not in fold(prev["notes"]):
        notes_val = (prev["notes"] + " | " + new["notes"])[:300]
    else:
        notes_val = prev["notes"] or new["notes"]
    if wants_new_game(message):
        extra = re.sub(r"\s+", " ", message).strip()[:160]
        if extra and extra not in notes_val:
            notes_val = (notes_val + " | " + extra).strip(" |")[:300]
    out = {"answers": answers, "interaction": inter, "notes": notes_val, "name": new["name"] or prev["name"]}
    if force_new:
        out["force_new"] = True
    if mode_confirmed:
        out["mode_confirmed"] = True
    if not out["notes"] and not prev["notes"] and kw["intent"] == "create_game":
        out["notes"] = re.sub(r"\s+", " ", message).strip()[:200]
    return out, intent, how


# ---------- kế hoạch ----------
def pick_player(players, brief):
    """Chọn trình chơi có sẵn khớp ý tưởng game + hai ý chính, hoặc None (khi đó AI viết game mới).
    - Nếu giáo viên nêu tên/cơ chế game cụ thể (vd 'sút penalty', 'cầu lông', 'đua xe'):
      ưu tiên khớp tên/mô tả game đó trong kho; nếu kho KHÔNG có game khớp cơ chế đó → trả None để AI viết mới (KHÔNG ép về Quiz ABCD).
    - Nếu giáo viên chỉ yêu cầu game trắc nghiệm chung chung → chọn trình chơi trắc nghiệm khớp số đáp án & loại điều khiển."""
    n, kind = brief["answers"], brief["interaction"]
    compatible = []
    for p in players:
        man = p.get("manifest") or {}
        quizzy = man.get("questions") == "exam" or (man.get("content") or {}).get("kind") == "questions"
        if not quizzy:
            continue
        inputs = man.get("inputs") or []
        if kind != "none":
            if kind not in (man.get("kinds") or []) or len(inputs) < n:
                continue
        required = len([i for i in inputs if i.get("required")])
        base_score = (abs((required or n) - n), 0 if (kind != "none" or not inputs) else 1, p["id"])
        compatible.append((base_score, p))
    if not compatible:
        return None
    concept = _concept_tokens((brief.get("notes") or "") + " " + (brief.get("name") or ""))
    if concept:
        matched = []
        for base_score, p in compatible:
            c_score = _player_concept_score(concept, p)
            if c_score > 0:
                matched.append((-c_score, base_score, p))
        if matched:
            matched.sort(key=lambda x: (x[0], x[1]))
            return matched[0][2]
        return None  # Có ý tưởng game cụ thể nhưng kho không có game khớp → AI viết game mới, không ép về Quiz
    compatible.sort(key=lambda x: x[0])
    return compatible[0][1]


def make_plan(c, user, brief):
    reg = _load_registry(c, user, include_showcase=True)
    force_new = bool(brief.get("force_new"))
    p = None if force_new else pick_player(reg["players"], brief)
    n, kind = brief["answers"], brief["interaction"]
    ans_txt = "Đúng/Sai" if n == 2 else "%d đáp án (%s)" % (n, ", ".join("ABCD"[:n]))
    reuse = {"mode": "reuse_existing", "player_id": p["id"], "player_name": p["name"]} if p else {"mode": "generate_new"}
    if p:
        player_line = "Trình chơi: dùng lại “%s” (#%d) có sẵn trong kho, không cần viết mới (hoặc bạn có thể bấm Tạo game mới / Xem kho game bên dưới)." % (p["name"], p["id"])
    elif force_new:
        player_line = "Trình chơi: theo yêu cầu của bạn, AI sẽ viết một trò chơi mới hoàn toàn (không dùng lại mẫu sẵn có), kiểm an toàn trước khi cho chơi thử."
    else:
        player_line = "Trình chơi: kho chưa có trình chơi khớp, AI sẽ viết một game mới (bản nháp, kiểm an toàn trước khi cho chơi thử)."
    lines = ["Câu hỏi: mỗi câu có %s. Môn học tuỳ bạn: nội dung câu hỏi gắn vào khi tạo ứng dụng, nên trình chơi dùng lại được cho mọi môn." % ans_txt,
             ("Điều khiển: chuột/bàn phím/cảm ứng luôn dùng được" + ("" if kind == "none" else ", thêm điều khiển bằng %s. Chưa có model cũng không sao: bạn tạo ở “Mô hình tương tác” rồi gắn khi tạo ứng dụng" % KIND_VI[kind])) + ".",
             player_line,
             "Sau khi bạn duyệt: AI tạo game ngay, bạn chơi thử, nói AI sửa theo ý, ưng thì lưu thành bản Nháp rồi gửi Admin duyệt công khai."]
    name = brief["name"] or ("Game trắc nghiệm %s" % ans_txt)
    return {"name": name[:80], "answers": n, "interaction": kind, "player": reuse,
            "model": None if kind == "none" else {"kind": kind, "status": "create_later"},
            "exam": {"mode": "attach_later"}, "mouse_fallback": True, "lines": lines}


def step(c, user, message, brief):
    """Một lượt chat. Trả {stage: ask|plan|refuse|other, message, brief, quick_replies?, plan?, notes[]}."""
    message = (message or "").strip()
    if not 2 <= len(message) <= 2000:
        raise agent_bridge.BridgeError(400, "text", "Hãy nhập 2–2000 ký tự.")
    refused, _cat, ref_msg, _code = guardrails.check_input_safety(message)
    if refused:
        return {"stage": "refuse", "message": ref_msg, "brief": clean_brief(brief), "notes": []}
    if is_catalog_list_query(message):
        return _catalog_reply(c, user, brief)
    prev_clean = clean_brief(brief)
    kw_pre = keywords(message)
    if kw_pre["intent"] == "create_game" and _needs_disambiguate(message, prev_clean, kw_pre):
        notes = [{"tool": "disambiguate", "status": "ok", "input": message[:160], "output": "Yêu cầu chưa rõ: hỏi xem kho hay soạn mới", "ms": 0}]
        return {
            "stage": "disambiguate",
            "message": ASK_DISAMBIGUATE,
            "quick_replies": CHIPS_DISAMBIGUATE,
            "brief": prev_clean,
            "notes": notes,
        }
    b, intent, how = merge(brief, message)
    notes = [{"tool": "read_brief", "status": "ok", "input": message[:160], "output": "Số đáp án: %s · Điều khiển: %s (đọc bằng %s)" % (
        b["answers"] or "chưa rõ", KIND_VI.get(b["interaction"], "chưa rõ"), how), "ms": 0}]
    if intent != "create_game":
        return {"stage": "other", "message": "", "brief": b, "notes": notes}
    if b["answers"] is None:
        return {"stage": "ask", "message": ASK_ANSWERS, "quick_replies": CHIPS_ANSWERS, "brief": b, "notes": notes}
    if b["interaction"] is None:
        return {"stage": "ask", "message": ASK_INTERACTION, "quick_replies": CHIPS_INTERACTION, "brief": b, "notes": notes}
    plan = make_plan(c, user, b)
    notes.append({"tool": "make_plan", "status": "ok", "input": "đáp án=%s, điều khiển=%s" % (b["answers"], b["interaction"]),
                  "output": ("dùng lại #%d %s" % (plan["player"]["player_id"], plan["player"]["player_name"])) if plan["player"]["mode"] == "reuse_existing" else "cần viết game mới", "ms": 0})
    return {"stage": "plan", "message": "Mình đã đủ thông tin. Bạn đọc kế hoạch, ổn thì bấm duyệt để mình tạo game ngay.", "brief": b, "plan": plan, "notes": notes}


# ---------- tạo game ----------
def _game_prompt(brief):
    n, kind = brief["answers"], brief["interaction"]
    ans = "Đúng/Sai (2 lựa chọn T/F)" if n == 2 else "%d đáp án %s" % (n, "/".join("ABCD"[:n]))
    ctl = ("chỉ chuột/chạm/bàn phím, KHÔNG khai inputs" if kind == "none"
           else "chơi được bằng chuột/chạm VÀ bằng model %s: khai inputs với các ô %s và xử lý camera.result" % (kind, ", ".join("ABCD"[:n])))
    return ("Game ôn tập trắc nghiệm, mỗi câu hỏi có %s. Câu hỏi nhận động qua camera.init (questions: 'exam'), có câu demo; không gắn với môn học nào. "
            "Điều khiển: %s. %s") % (ans, ctl, ("Yêu cầu thêm của giáo viên: " + brief["notes"]) if brief["notes"] else "")


def _draft_envelope(plan, html, brief):
    return {"decision": "GENERATE", "status": "pending_approval", "schema_version": "1.0", "message": "Bản nháp game do AI viết.",
            "application_plan": {"name": plan["name"], "player": {"mode": "generate_new", "player_id": None, "html": html},
                                 "model": None, "exam": None,
                                 "interaction": {"primary": "mouse", "fallback": "mouse", "mouse_always_enabled": True}},
            "flow": {"version": 1, "brief": brief, "feedback": []}}


def build(c, user, brief):
    """Giáo viên đã duyệt kế hoạch: thực hiện luôn. Trả {stage:'built', kind:'reuse'|'generated', preview_url, ...}."""
    b = clean_brief(brief)
    if b["answers"] is None or b["interaction"] is None:
        raise agent_bridge.BridgeError(400, "brief", "Chưa đủ thông tin để tạo game (số đáp án, cách điều khiển).")
    plan = make_plan(c, user, b)
    if plan["player"]["mode"] == "reuse_existing":
        pid = plan["player"]["player_id"]
        return {"stage": "built", "kind": "reuse", "message": "Mình dùng lại “%s” (#%d). Bạn chạy thử xem có hợp không." % (plan["player"]["player_name"], pid),
                "player_id": pid, "player_name": plan["player"]["player_name"], "preview_url": "/api/players/%d/try" % pid, "can_fix": False}
    try:
        if llm._real_model() is None:
            html = llm.QUIZ_TEMPLATE.replace("__TITLE__", plan["name"].replace("<", "").replace("&", ""))
            msg, err = "Chế độ giả: dựng từ khuôn Quiz ABCD (chưa gọi model thật).", None
        else:
            idea = _game_prompt(b)
            html, msg, err = agent._run_generate_html(idea, idea, True)
    except ai.ProviderError as e:
        raise agent_bridge.provider_error(e) from None
    if err or not html:
        raise agent_bridge.BridgeError(502, "generate_failed", "Chưa tạo được game đạt kiểm tra (%s). Bạn bấm duyệt lại hoặc mô tả thêm." % (err or "lỗi không rõ"))
    saved = agent_bridge.save_draft(c, user, _draft_envelope(plan, html, b))
    return {"stage": "built", "kind": "generated", "message": msg or "Mình đã tạo xong bản nháp. Bạn chạy thử rồi nói mình sửa gì nhé.",
            "draft_id": saved["draft_id"], "preview_url": "/api/agent/drafts/%d/try" % saved["draft_id"], "flags": contract.scan(html),
            "name": plan["name"], "version": 1, "fixes_left": MAX_FIXES, "can_fix": True}


# ---------- sửa theo ý giáo viên ----------
def _load(c, user, draft_id):
    row = agent_bridge.get_draft(c, draft_id, user)
    if row["status"] != "pending_approval":
        raise agent_bridge.BridgeError(409, "draft_state", "Bản nháp này đã được lưu hoặc từ chối, không sửa nữa.")
    return row, json.loads(row["envelope_json"])


def fix(c, user, draft_id, feedback):
    feedback = (feedback or "").strip()
    if not 3 <= len(feedback) <= MAX_FEEDBACK:
        raise agent_bridge.BridgeError(400, "feedback", "Hãy nói rõ muốn sửa gì (3–%d ký tự)." % MAX_FEEDBACK)
    refused, _c, ref_msg, _code = guardrails.check_input_safety(feedback)
    if refused:
        raise agent_bridge.BridgeError(400, "refused", ref_msg)
    row, env = _load(c, user, draft_id)
    flow = env.setdefault("flow", {"version": 1, "feedback": []})
    if len(flow.get("feedback") or []) >= MAX_FIXES:
        raise agent_bridge.BridgeError(409, "fix_limit", "Đã sửa %d lần. Hãy lưu bản này, rồi chỉnh tiếp trong Kho mẫu game." % MAX_FIXES)
    html = env["application_plan"]["player"]["html"]
    try:
        if llm._real_model() is None:
            new_html = html.replace("</body>", "<!-- giả: đã ghi nhận yêu cầu sửa -->\n</body>", 1)
            msg = "Chế độ giả: chưa gọi model thật nên mình chỉ ghi nhận yêu cầu, chưa sửa nội dung."
        else:
            fence = agent.FENCE
            prompt = ("Đây là game HTML hiện tại:\n" + fence + "html\n" + html + "\n" + fence + "\n\n"
                      "Giáo viên chơi thử và muốn sửa: " + feedback + "\n"
                      "Chỉ sửa đúng theo yêu cầu, giữ nguyên phần còn lại, vẫn đúng hợp đồng jl-camera, chơi được bằng chuột, 0 cờ an toàn, file gọn. "
                      "Trả 1–2 câu mô tả thay đổi và đủ file HTML trong một khối " + fence + "html.")
            new_html, msg, last_err = None, None, None
            for step_i in range(agent.MAX_STEPS):
                use_prompt = prompt if not last_err else prompt + "\n[Hệ thống] Bản trước bị từ chối: %s. Sửa lại và trả đủ file." % last_err
                reply = agent._call_generator(agent.GENERATE_HTML_SYSTEM, use_prompt, model=agent.GAME_REPAIR_MODEL if step_i else None)
                msg, cand = agent._split((reply.get("text") or "").strip())
                if not cand:
                    last_err = "Không tìm thấy khối mã html đầy đủ (có thể bị cắt cụt, hãy viết gọn hơn)."
                    continue
                cand = agent._ensure_single_camera(cand)
                v = guardrails.validate_html_draft(cand, check_fn=agent.check_game)
                if v["ok"]:
                    new_html = cand.strip()
                    break
                last_err = v["error"]
            if not new_html:
                raise agent_bridge.BridgeError(502, "fix_failed", "Chưa sửa được theo yêu cầu (%s). Bản cũ vẫn giữ nguyên, bạn thử nói cách khác." % last_err)
    except ai.ProviderError as e:
        raise agent_bridge.provider_error(e) from None
    env["application_plan"]["player"]["html"] = new_html
    flow["version"] = int(flow.get("version") or 1) + 1
    flow["feedback"] = (flow.get("feedback") or []) + [{"at": time.time(), "text": feedback[:300]}]
    c.execute("UPDATE agent_drafts SET envelope_json=?, plan_hash=?, updated=? WHERE id=?",
              (json.dumps(env, ensure_ascii=False), agent_bridge.plan_hash(env["application_plan"]), time.time(), row["id"]))
    c.commit()
    return {"stage": "built", "kind": "generated", "message": msg or "Mình đã sửa xong. Bạn chạy thử lại nhé.", "draft_id": row["id"],
            "preview_url": "/api/agent/drafts/%d/try?v=%d" % (row["id"], flow["version"]), "flags": contract.scan(new_html),
            "name": env["application_plan"]["name"], "version": flow["version"], "fixes_left": MAX_FIXES - len(flow["feedback"]), "can_fix": True}


def accept(c, user, draft_id):
    """Giáo viên ưng: lưu bản nháp thành trình chơi Nháp của họ (chưa công khai; Admin duyệt sau như mọi trình chơi)."""
    row, env = _load(c, user, draft_id)
    html = env["application_plan"]["player"]["html"]
    pid = store.add_player(c, user, html, source="ai", status="draft")
    c.execute("UPDATE agent_drafts SET status='published', player_id=?, updated=? WHERE id=?", (pid, time.time(), row["id"]))
    c.commit()
    return {"player_id": pid, "message": "Đã lưu thành trình chơi Nháp. Bạn gửi duyệt công khai hoặc ghép thành ứng dụng ngay."}
