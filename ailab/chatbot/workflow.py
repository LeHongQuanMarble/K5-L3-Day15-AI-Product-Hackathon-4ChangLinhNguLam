"""C02 — Điều phối một lượt hội thoại: hiểu → hợp nhất → hỏi phần thiếu hoặc lập phương án chờ xác nhận.

Hàm thuần: nhận state, trả state mới. KHÔNG lưu DB, KHÔNG sinh HTML, KHÔNG tạo Player/Exam/App.
Việc lưu (optimistic version, chống trùng) là của repository (I01). Spec: docs/chatbot/C02_SPEC.md.
"""
import copy
import secrets
import time

from . import conversation as C
from . import schemas as S

SUPPORTED_KINDS = ("image", "pose", "hands")  # runtime play.js; audio chỉ lưu, chưa chạy


def _new_id():
    return "p-" + secrets.token_hex(6)


def _meta(analysis=None, failure=None):
    a = analysis or {}
    return {"failure": failure if failure is not None else a.get("failure"), "simulated": a.get("simulated", True),
            "model": a.get("model", C.FAKE_MODEL), "calls": a.get("calls", 0)}


def _summary(req, list_game):
    if list_game:
        g = req["gamePreference"].get("description") or "game danh sách"
        return "Game danh sách: %s." % g
    parts = []
    for k in ("subject", "gradeOrAudience", "topic"):
        if req.get(k):
            parts.append("%s: %s" % (C.FIELD_LABELS[k], req[k]))
    if req.get("questionCount"):
        parts.append("%d câu" % req["questionCount"])
    if req.get("difficulty"):
        parts.append("độ khó %s" % req["difficulty"])
    return "Game ôn tập — " + "; ".join(parts) + "."


MOUSE_ONLY_NOTE = "Chỉ chơi bằng chuột, không dùng camera."


def _mouse_only(req):
    """Giáo viên đã nói không dùng camera/model (useModel=False) -> phương án chỉ chơi bằng chuột."""
    return req["interaction"].get("useModel") is False


def _is_cancelled(p):
    return bool(p) and p.get("status") == "cancelled"


def _warnings(req):
    out = []
    kinds = req["interaction"].get("requestedKinds") or []
    if "audio" in kinds and not _mouse_only(req):
        out.append({"code": "unsupported_interaction", "label": "Âm thanh chưa hỗ trợ",
                    "reason": "Trang chơi hiện chỉ chạy model ảnh, tư thế và bàn tay. Game vẫn chơi được bằng chuột.",
                    "message": "Điều khiển bằng giọng nói/âm thanh chưa chạy được ở bản này."})
    return out


def _build_proposal(old_proposal, req, catalog, new_id, changes):
    list_game = C.is_list_game(req, catalog)
    gp = req["gamePreference"]
    kinds = [k for k in req["interaction"].get("requestedKinds") or [] if k in SUPPORTED_KINDS]
    assumptions = C.default_assumptions(req, catalog)
    if _mouse_only(req):
        # useModel=False thắng requestedKinds cũ còn lưu: không chọn model, chuột luôn bật
        interaction_model = {"modelId": None, "kind": None, "mapping": {}, "mouse": True}
        assumptions = [x for x in assumptions if not x.startswith("Luôn chơi được bằng chuột")] + [MOUSE_ONLY_NOTE]
    else:
        interaction_model = {"modelId": None, "kind": kinds[0] if kinds else None, "mapping": {}, "mouse": True}
    if old_proposal:
        pid, version = old_proposal["proposalId"], old_proposal["version"] + 1
    else:
        pid, version = new_id(), 1
    return {
        "kind": "plan_v2", "scope": "requirements", "proposalId": pid, "version": version, "status": "awaiting_confirmation",
        "generationMode": gp.get("mode") if gp.get("mode") != "auto" else None,  # C03 định tuyến khi auto
        "reason": _summary(req, list_game),
        "assumptions": assumptions,
        "changes": list(changes),
        "player": {"playerId": gp.get("playerId"), "name": None, "plan": gp.get("description")},
        "exam": None,  # C04 chuẩn bị bộ đề sau khi xác nhận
        "interactionModel": interaction_model,
        "warnings": _warnings(req),
        "validation": None,
    }


def _cancelled_text(p):
    if not p:
        return "Hiện chưa có phương án nào. Bạn muốn làm game ôn bài gì?"
    return ("Phương án phiên bản %d đã bị hủy, chưa có phương án nào đang chờ xác nhận. "
            "Bạn muốn đổi gì (môn, lớp, chủ đề, số câu, cách chơi…)? Mình sẽ lập phương án mới để bạn xác nhận lại."
            % p["version"])


def _reply_text(st, intent, model_reply, list_game):
    if intent == "off_topic":
        return model_reply or "Mình chỉ hỗ trợ chuẩn bị game học tập. Bạn muốn làm game ôn bài gì?"
    if st["status"] == "clarifying":
        qs = "\n".join("- " + q["text"] for q in st["questions"])
        return "Mình cần thêm vài thông tin:\n" + qs
    p = st["proposal"]
    if st["status"] == "needs_revision" or _is_cancelled(p):
        return _cancelled_text(p)
    lines = ["Yêu cầu sơ bộ (phiên bản %d): %s" % (p["version"], p["reason"])]
    if p["changes"]:
        lines.append("Đã đổi: " + "; ".join(p["changes"]))
    lines.append("Giả định: " + " ".join(p["assumptions"]))
    for w in p["warnings"]:
        lines.append("Lưu ý: " + w["message"])
    if st["confirmations"].get("version") == p["version"] and p.get("status") == "confirmed":
        lines.append("Bạn đã xác nhận yêu cầu phiên bản này; chưa duyệt kế hoạch ứng dụng hoặc Game Preview.")
    else:
        lines.append("Nếu đúng ý, bấm “Xác nhận phương án” để xác nhận yêu cầu sơ bộ. Kế hoạch ứng dụng sẽ cần duyệt riêng.")
    return "\n".join(lines)


def _cancel(st):
    """Hủy phương án đang có (dùng chung cho reject_intent và cancel_plan): proposal cancelled, xác nhận cũ hết hiệu lực,
    status needs_revision, KHÔNG đổi requirements, version +1."""
    new = copy.deepcopy(st)
    new["proposal"]["status"] = "cancelled"
    new["confirmations"] = {}
    new["status"] = "needs_revision"
    new["questions"] = []
    new["version"] = st["version"] + 1
    return new


def process_turn(request, state, context=None):
    """Một lượt tin nhắn. -> (new_state, reply_text, meta). meta = {failure, simulated, model, calls}.

    - expectedVersion lệch -> stale_version, KHÔNG gọi AI, state giữ nguyên.
    - Lỗi AI -> state giữ nguyên, meta.failure có mã lỗi.
    - Không bao giờ đặt status ready; không ghi xác nhận (chỉ confirm_plan làm).
    """
    ctx = context or {}
    st = S.normalize_state(state)
    ev = (request or {}).get("expectedVersion")
    if ev is not None and ev != st["version"]:
        f = S.make_error("stale_version", "turn", "Cuộc trò chuyện đã có lượt mới hơn. Tải lại để xem bản mới nhất.",
                         details={"expectedVersion": ev, "currentVersion": st["version"]})
        return st, f["message"], _meta(failure=f)
    text = request.get("text") or ""
    a = C.analyze_turn(text, st, ctx)
    if a["failure"]:
        return st, a["failure"]["message"], _meta(a)
    out = a["output"]
    intent = out["intent"]
    catalog = ctx.get("catalog")
    new_id = ctx.get("new_id") or _new_id
    old_req = st["requirements"]

    if intent == "off_topic":
        return st, _reply_text(st, intent, out["reply"], False), _meta(a)

    if intent == "reject_intent":
        # Hủy phương án: chỉ hủy, KHÔNG tự lập phương án mới, KHÔNG đổi requirements, xác nhận cũ hết hiệu lực.
        p = st["proposal"]
        if _is_cancelled(p):
            return st, _cancelled_text(p), _meta(a)
        if not p:
            text_out = "Hiện chưa có phương án nào để hủy. "
            if st["status"] == "clarifying" and st["questions"]:
                text_out += _reply_text(st, intent, out["reply"], False)
            else:
                text_out += "Bạn muốn làm game ôn bài gì?"
            return st, text_out, _meta(a)
        new = _cancel(st)
        return new, _cancelled_text(new["proposal"]), _meta(a)

    if intent == "new_request" and (st["proposal"] or any(old_req.get(k) for k in ("subject", "topic", "gradeOrAudience"))):
        base, old_proposal = S.empty_requirements(), None
    else:
        base, old_proposal = old_req, st["proposal"]
    req = C.merge_requirements(base, out["requirementsPatch"])
    missing = C.find_missing_fields(req, catalog)
    changed = req != old_req or (base is not old_req)

    new = copy.deepcopy(st)
    new["requirements"] = req
    new["missingFields"] = missing
    new["assumptions"] = out["assumptions"]
    if missing:
        new["status"] = "clarifying"
        by_model = {q["field"]: q["text"] for q in out["questions"] if q["field"] in missing}
        new["questions"] = [{"field": f, "text": by_model.get(f) or C.FIELD_QUESTIONS[f]} for f in missing]
        if changed and st["proposal"]:
            new["proposal"] = None  # phương án cũ không còn đủ thông tin -> bỏ, xác nhận cũ hết hiệu lực
            new["confirmations"] = {}
    elif _is_cancelled(old_proposal) and not changed:
        # đã hủy, lượt này không đổi yêu cầu -> giữ needs_revision, không hồi sinh phương án cũ
        new["questions"] = []
        new["status"] = "needs_revision"
    else:
        new["questions"] = []
        new["status"] = "awaiting_confirmation"
        if old_proposal is None or changed:
            changes = C.diff_requirements(old_req, req) if old_proposal else []
            new["proposal"] = _build_proposal(old_proposal, req, catalog, new_id, changes)
            new["proposal"]["simulated"] = bool(a["simulated"])
            new["confirmations"] = {}  # phương án đổi -> hủy xác nhận cũ
    list_game = C.is_list_game(req, catalog)
    if intent == "confirm_intent" and new["status"] == "awaiting_confirmation" \
            and new["confirmations"].get("version") != new["proposal"]["version"]:
        text_out = ("Để chắc chắn đúng bản, bạn bấm nút “Xác nhận phương án” (phiên bản %d) nhé. Chữ “đồng ý” trong khung chat "
                    "chưa được tính là xác nhận." % new["proposal"]["version"])
    elif intent == "confirm_intent" and new["status"] == "needs_revision":
        text_out = ("Phương án phiên bản %d đã bị hủy nên không có gì để xác nhận. Bạn nhắn điều muốn đổi, mình sẽ lập "
                    "phương án mới để bạn bấm “Xác nhận phương án”." % new["proposal"]["version"])
    else:
        text_out = _reply_text(new, intent, out["reply"], list_game)
    if new != st:
        new["version"] = st["version"] + 1
    return new, text_out, _meta(a)


def confirm_plan(state, proposal_id, version, now=None):
    """Xác nhận tường minh (nút bấm) đúng proposalId + version. -> (new_state, failure|None).
    Chưa tạo App/Player/Exam: chỉ ghi xác nhận. Bước chuẩn bị là W2."""
    st = S.normalize_state(state)
    p = st["proposal"]
    if not p or p.get("proposalId") != proposal_id:
        return st, S.make_error("invalid_input", "confirm", "Không thấy phương án này trong cuộc trò chuyện.")
    if _is_cancelled(p):
        return st, S.make_error("stale_version", "confirm",
                                "Phương án đã bị hủy. Hãy nhắn điều muốn đổi để có phương án mới rồi xác nhận lại.",
                                details={"expectedVersion": version, "currentVersion": p.get("version")})
    if p.get("version") != version or st["status"] != "awaiting_confirmation":
        return st, S.make_error("stale_version", "confirm", "Phương án đã đổi. Hãy xem bản mới nhất rồi xác nhận lại.",
                                details={"expectedVersion": version, "currentVersion": p.get("version")})
    if st["confirmations"].get("version") == version:
        return st, None  # bấm lại: giữ nguyên, không tăng version
    new = copy.deepcopy(st)
    new["confirmations"] = {"proposalId": proposal_id, "version": version, "at": now if now is not None else time.time(),
                            "scope": "requirements"}
    new["proposal"]["status"] = "confirmed"
    new["version"] = st["version"] + 1
    return new, None


def cancel_plan(state, proposal_id, version):
    """Hủy tường minh (nút "Hủy phương án") đúng proposalId + version. -> (new_state, failure|None).
    Sai id -> invalid_input; đã hủy hoặc sai version -> stale_version; đúng -> như nhánh reject_intent."""
    st = S.normalize_state(state)
    p = st["proposal"]
    if not p or p.get("proposalId") != proposal_id:
        return st, S.make_error("invalid_input", "cancel", "Không thấy phương án này trong cuộc trò chuyện.")
    if _is_cancelled(p):
        return st, S.make_error("stale_version", "cancel", "Phương án này đã bị hủy rồi.",
                                details={"expectedVersion": version, "currentVersion": p.get("version")})
    if p.get("version") != version:
        return st, S.make_error("stale_version", "cancel", "Phương án đã đổi. Hãy xem bản mới nhất rồi thao tác lại.",
                                details={"expectedVersion": version, "currentVersion": p.get("version")})
    return _cancel(st), None
