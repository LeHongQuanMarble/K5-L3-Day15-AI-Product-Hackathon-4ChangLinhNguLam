"""T14 — Cầu nối Shared Core (`codebase/agent.py`) cho Web/Backend.

Mọi lời nhắn của giáo viên đi qua `agent.run_agent()` — KHÔNG nhân đôi prompt/routing
ở `ailab/llm.py`. Module này chỉ làm 4 việc ở ranh giới Web:

1. Gọi Shared Core, ghi trace/token qua `codebase.tracing`.
2. Chiếu envelope sang UI an toàn (`application_contract.to_ui_response`) — không trả HTML thô.
3. Ánh xạ `ProviderError` → HTTP 502/503 (không nuốt lỗi, không lộ key/body).
4. Cưỡng chế HITL: AI chỉ trả `pending_approval`; chỉ teacher bấm phê duyệt mới được
   xuất bản, và sửa nội dung sau duyệt tự động quay về `draft` (plan_hash khác).

Chạy: import từ `ailab/server.py` hoặc `python -m unittest ... test_agent_bridge.py`.
Không ghi DB, không gửi tin, không xuất bản — mọi thao tác có tác động nằm ở server.py.
"""
import hashlib
import json
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "codebase")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ai  # noqa: E402  (ProviderError — định nghĩa ở codebase/ai.py)
import agent  # noqa: E402  (Shared Core, dùng chung với python run.py)
import application_contract as ac  # noqa: E402
import contract  # noqa: E402
import store  # noqa: E402
import tracing  # noqa: E402

# Chỉ các trạng thái AI được phép trả về. AI KHÔNG BAO GIỜ trả "approved".
AI_STATUSES = frozenset(ac.STATUSES.values())
PUBLISHABLE = frozenset(("pending_approval",))
KNOWLEDGE_CODE = "knowledge_review_required"

# ProviderError.kind → (HTTP, mã cho UI, gợi ý cho giáo viên).
# auth/rate_limit/timeout/network/http: 502/503; config/bad_response/usage_missing: 502.
PROVIDER_HTTP = {
    "auth": (502, "provider_auth", "Model từ chối key. Kiểm tra API_KEY trong .env."),
    "config": (502, "provider_config", "Cấu hình model không hợp lệ. Kiểm tra MODEL_NAME/MODEL_PROVIDER."),
    "rate_limit": (503, "provider_rate_limit", "Model đang quá tải lượt gọi. Chờ vài phút rồi thử lại."),
    "timeout": (503, "provider_timeout", "Model phản hồi quá lâu. Thử lại sau."),
    "network": (503, "provider_network", "Không kết nối được tới nhà cung cấp model. Thử lại sau."),
    "http": (502, "provider_http", "Nhà cung cấp model trả lỗi. Thử lại hoặc báo Admin."),
    "bad_response": (502, "provider_bad_response", "Model trả phản hồi không đúng định dạng. Thử lại."),
    "usage_missing": (502, "provider_usage_missing", "Model không trả số token. Không tính lượt này."),
}


class BridgeError(Exception):
    """Lỗi ranh giới Web: (HTTP status, mã máy đọc được, thông điệp an toàn)."""

    def __init__(self, status, code, message):
        self.status, self.code, self.msg = status, code, message
        super().__init__(message)


def provider_error(exc):
    """Chuyển ProviderError thành BridgeError; không đưa provider/code/body thô vào message."""
    if not isinstance(exc, ai.ProviderError):
        raise exc
    status, code, hint = PROVIDER_HTTP.get(
        getattr(exc, "kind", ""), (502, "provider_error", "Không gọi được model. Thử lại sau."))
    # 429/5xx của nhà cung cấp là lỗi tạm thời → 503; 4xx còn lại → 502.
    if getattr(exc, "kind", "") == "http":
        http_status = getattr(exc, "status", None)
        if http_status == 429 or (isinstance(http_status, int) and http_status >= 500):
            status = 503
    return BridgeError(status, code, hint)


def trusted_registry(c, user=None):
    """Registry tin cậy lấy từ Catalog hiện tại theo quyền của user (để validate_application_plan ở ranh giới)."""
    def rows(sql, params=()):
        out = []
        for r in c.execute(sql, params).fetchall():
            d = dict(r)
            if "manifest" in d and isinstance(d["manifest"], str):
                try:
                    d["manifest"] = json.loads(d["manifest"])
                except ValueError:
                    d["manifest"] = {}
            if "outputs" in d and isinstance(d["outputs"], str):
                try:
                    d["outputs"] = json.loads(d["outputs"])
                except ValueError:
                    d["outputs"] = []
            out.append(d)
        return out

    is_admin = isinstance(user, dict) and user.get("role") == "admin"
    uid = user.get("id") if isinstance(user, dict) else None

    if is_admin:
        players = rows("SELECT id,name,manifest FROM players WHERE status='approved' AND source<>'showcase' ORDER BY id")
        models = rows("SELECT id,name,kind,outputs FROM models ORDER BY id")
        exams = rows("SELECT id,name,content FROM exams ORDER BY id")
    elif uid is not None:
        players = rows(
            "SELECT id,name,manifest FROM players WHERE status='approved' AND source<>'showcase' "
            "AND (visibility='public' OR owner_id IS NULL OR owner_id=?) ORDER BY id",
            (uid,),
        )
        models = rows("SELECT id,name,kind,outputs FROM models WHERE visibility='public' OR owner_id=? ORDER BY id", (uid,))
        exams = rows("SELECT id,name,content FROM exams WHERE owner_id IN (0, ?) ORDER BY id", (uid,))
    else:
        players = rows(
            "SELECT id,name,manifest FROM players WHERE status='approved' AND source<>'showcase' "
            "AND (visibility='public' OR owner_id IS NULL) ORDER BY id"
        )
        models = rows("SELECT id,name,kind,outputs FROM models WHERE visibility='public' ORDER BY id")
        exams = rows("SELECT id,name,content FROM exams WHERE owner_id=0 ORDER BY id")

    return {"players": players, "models": models, "exams": exams}


_TRACE_LOCK = threading.Lock()


def call(payload, case_id="web-req", registry=None):
    """Gọi Shared Core. Trả dict {envelope, ui, trace, knowledge_review_required}.

    `payload` là Spec request dict (xem handoff T08/T09 mục 1) hoặc chuỗi yêu cầu.
    Không nuốt ProviderError — để server ánh xạ thành 502/503.
    """
    session_id = payload.get("session_id") if isinstance(payload, dict) else None
    with _TRACE_LOCK:
        tracing.begin(str(session_id or case_id))
        try:
            envelope = agent.run_agent(payload, registry=registry)
        except ai.ProviderError as exc:
            # Kết thúc trace để ghi trung thực lỗi, rồi ném ra cho server ánh xạ 502/503.
            tracing.end()
            raise provider_error(exc) from None
        summary, events = tracing.end()
    if not isinstance(envelope, dict):
        raise BridgeError(502, "bad_envelope", "Lõi AI trả kết quả không hợp lệ.")
    # Ranh giới Web không tin status do model/plan gửi lên: mọi output đều ở dạng nháp.
    if envelope.get("status") not in AI_STATUSES:
        envelope["status"] = "draft"
    ui = ac.to_ui_response(envelope)
    warnings = envelope.get("warnings") or []
    needs_review = any(isinstance(w, dict) and w.get("code") == KNOWLEDGE_CODE for w in warnings)
    ui["knowledge_review_required"] = bool(needs_review)
    ui["hitl"] = {"status": "draft", "can_publish": False}
    return {"envelope": envelope, "ui": ui, "trace": summary, "events": events,
            "knowledge_review_required": bool(needs_review)}


def plan_hash(plan):
    """Hash ổn định của ApplicationPlan — dùng để phát hiện sửa sau khi duyệt."""
    raw = json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def publish(body, user, registry=None):
    """Cổng HITL: chỉ teacher phê duyệt rõ ràng mới được xuất bản.

    `body`: {"envelope": <envelope từ call()>, "approved": true, "reviewed_knowledge": true}
    Trả bản ghi phê duyệt {status: "approved", plan_hash, approved_by, ...}.
    - envelope.status ∈ {draft, rejected, pending_approval} → 403 (không tự duyệt).
    - payload cố gửi status="approved"/APPROVED → 400 (AI/user không tự đặt trạng thái).
    - decision REFUSE/ASK_CLARIFY/ERROR hoặc thiếu application_plan → 403.
    - `approved` không phải True hoặc `reviewed_knowledge` không phải True → 403.
    - plan không qua validate_application_plan → 400.
    """
    if not isinstance(body, dict):
        raise BridgeError(400, "bad_json", "JSON phải là một đối tượng.")
    envelope = body.get("envelope")
    if not isinstance(envelope, dict):
        raise BridgeError(400, "bad_envelope", "Thiếu envelope từ lõi AI.")
    # Chặn mọi cố gắng tự gắn status APPROVED từ phía payload/AI.
    for key in ("status", "state"):
        v = envelope.get(key)
        if isinstance(v, str) and v.strip().upper() in ("APPROVED", "PUBLISHED"):
            raise BridgeError(400, "hitl_forbidden", "Không được tự đặt trạng thái APPROVED.")
    status = envelope.get("status")
    if isinstance(status, str) and status.strip().upper() in ("DRAFT", "REJECTED"):
        raise BridgeError(403, "hitl_not_ready", "Bản nháp hoặc bản bị từ chối chưa được phê duyệt để xuất bản.")
    if status not in PUBLISHABLE:
        raise BridgeError(403, "hitl_not_ready", "Trạng thái hiện tại chưa cho phép xuất bản.")
    if body.get("approved") is not True:
        raise BridgeError(403, "hitl_required", "Cần giáo viên bấm Phê duyệt trước khi xuất bản.")
    plan = envelope.get("application_plan")
    if not isinstance(plan, dict):
        raise BridgeError(403, "hitl_no_plan", "Không có ApplicationPlan để xuất bản.")
    if envelope.get("decision") not in ("REUSE", "GENERATE"):
        raise BridgeError(403, "hitl_decision", "Chỉ bản REUSE/GENERATE được xuất bản.")
    needs_review = any(isinstance(w, dict) and w.get("code") == KNOWLEDGE_CODE
                       for w in (envelope.get("warnings") or []))
    if needs_review and body.get("reviewed_knowledge") is not True:
        raise BridgeError(403, "knowledge_review_required",
                          "Bộ đề AI sinh: giáo viên phải xác nhận đã kiểm duyệt kiến thức.")
    errors = ac.validate_application_plan(plan, registry=registry)
    if errors:
        raise BridgeError(400, "invalid_plan", "; ".join(e["message"] for e in errors[:4]))
    digest = plan_hash(plan)
    return {"status": "approved", "plan_hash": digest, "decision": envelope["decision"],
            "approved_by": (user or {}).get("username") or "teacher",
            "knowledge_reviewed": bool(needs_review), "bypass_count": 0}


def review(body, approval):
    """Kiểm tra sau duyệt: nội dung đổi thì tự quay về DRAFT, cần duyệt lại."""
    if not isinstance(approval, dict) or approval.get("status") != "approved":
        raise BridgeError(403, "hitl_required", "Chưa có phê duyệt hợp lệ.")
    if not isinstance(body, dict):
        raise BridgeError(400, "bad_json", "JSON phải là một đối tượng.")
    envelope = body.get("envelope")
    plan = envelope.get("application_plan") if isinstance(envelope, dict) else body.get("application_plan")
    if not isinstance(plan, dict):
        raise BridgeError(400, "bad_plan", "Thiếu ApplicationPlan để so sánh.")
    if plan_hash(plan) != approval.get("plan_hash"):
        return {"status": "draft", "can_publish": False,
                "message": "Nội dung đã thay đổi sau khi duyệt. Vui lòng kiểm tra và duyệt lại."}
    return {"status": "approved", "can_publish": True, "message": "Nội dung khớp bản đã duyệt."}


def _ensure_drafts_table(c):
    c.execute(
        "CREATE TABLE IF NOT EXISTS agent_drafts("
        "id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, decision TEXT NOT NULL, "
        "status TEXT NOT NULL DEFAULT 'pending_approval' CHECK(status IN ('pending_approval','published','rejected')), "
        "envelope_json TEXT NOT NULL, plan_hash TEXT NOT NULL DEFAULT '', "
        "app_id INTEGER, player_id INTEGER, exam_id INTEGER, reject_reason TEXT NOT NULL DEFAULT '', "
        "created REAL NOT NULL, updated REAL NOT NULL)"
    )


def save_draft(c, user, envelope):
    """Lưu bản nháp kế hoạch phía máy chủ để khóa chống sửa đổi/replay khi HITL duyệt."""
    _ensure_drafts_table(c)
    plan = envelope.get("application_plan") if isinstance(envelope, dict) else None
    if not isinstance(plan, dict):
        return None
    digest = plan_hash(plan)
    now = time.time()
    cur = c.execute(
        "INSERT INTO agent_drafts(owner_id,decision,status,envelope_json,plan_hash,created,updated) "
        "VALUES(?,?,?,?,?,?,?)",
        (user["id"], envelope.get("decision") or "REUSE", "pending_approval",
         json.dumps(envelope, ensure_ascii=False), digest, now, now),
    )
    c.commit()
    return {"draft_id": cur.lastrowid, "plan_hash": digest}


def get_draft(c, draft_id, user):
    """Đọc bản nháp có kiểm tra quyền sở hữu (owner hoặc admin)."""
    _ensure_drafts_table(c)
    try:
        did = int(draft_id)
    except (TypeError, ValueError):
        raise BridgeError(400, "bad_draft_id", "Mã bản nháp không hợp lệ.")
    row = c.execute("SELECT * FROM agent_drafts WHERE id=?", (did,)).fetchone()
    if not row or not (row["owner_id"] == user["id"] or user.get("role") == "admin"):
        raise BridgeError(404, "not_found", "Không thấy bản nháp này.")
    return row


def draft_preview(c, draft_id, user, sample_questions=None):
    """Trả dữ liệu xem thử trong iframe sandbox cho cả bản nháp REUSE và GENERATE (đã bọc CSP, đúng bộ đề sẽ xuất bản)."""
    row = get_draft(c, draft_id, user)
    if row["status"] == "rejected":
        raise BridgeError(409, "draft_rejected", "Bản nháp này đã bị từ chối.")
    env = json.loads(row["envelope_json"])
    plan = env.get("application_plan") or {}
    player = plan.get("player") or {}
    if player.get("mode") == "generate_new" and isinstance(player.get("html"), str):
        html = player["html"]
        man, err = contract.parse(html)
        if err:
            raise BridgeError(400, err[0], err[1])
    elif player.get("mode") == "reuse_existing" and player.get("player_id") is not None:
        prow = store.get_player(c, int(player["player_id"]), user)
        html = prow["html"]
        man = json.loads(prow["manifest"])
    else:
        raise BridgeError(400, "invalid_draft_player", "Bản nháp không có trình chơi hợp lệ để xem thử.")

    qs = sample_questions or []
    exam = plan.get("exam") or {}
    if isinstance(exam.get("content"), str) and exam["content"].strip():
        try:
            parsed = store.parse_questions(exam["content"])
            if parsed:
                qs = parsed
        except store.Err:
            pass
    elif exam.get("exam_id") is not None:
        ex_row = c.execute("SELECT owner_id, content FROM exams WHERE id=?", (int(exam["exam_id"]),)).fetchone()
        if ex_row and (ex_row["owner_id"] in (0, user["id"]) or user.get("role") == "admin"):
            try:
                parsed = store.parse_questions(ex_row["content"])
                if parsed:
                    qs = parsed
            except store.Err:
                pass
    return {"manifest": man, "srcdoc": contract.secure(html), "sampleQuestions": qs}


def reject_draft(c, draft_id, user, reason=""):
    """Giáo viên từ chối bản nháp (HITL Reject): khóa không cho xuất bản, không lưu ứng dụng."""
    row = get_draft(c, draft_id, user)
    if row["status"] == "published":
        raise BridgeError(409, "already_published", "Bản nháp này đã được xuất bản, không thể từ chối.")
    if row["status"] == "rejected":
        raise BridgeError(409, "already_rejected", "Bản nháp này đã bị từ chối trước đó.")
    clean_reason = (reason or "").strip()[:300]
    c.execute(
        "UPDATE agent_drafts SET status='rejected', reject_reason=?, updated=? WHERE id=?",
        (clean_reason, time.time(), row["id"]),
    )
    c.commit()
    return {
        "draft_id": row["id"],
        "status": "rejected",
        "can_publish": False,
        "reason": clean_reason,
        "message": "Đã từ chối bản nháp — không tạo ứng dụng và không tạo liên kết chơi.",
    }


def publish_and_persist(c, body, user, registry=None):
    """Cổng HITL + Lưu SQLite nguyên tử (atomic transaction) cho Web API POST /api/agent/publish.

    Yêu cầu `draft_id` (lưu phía máy chủ khi gọi POST /api/agent) và `plan_hash` khớp 100%,
    chống sửa kế hoạch, chống bypass HITL và chống double-publish/replay.
    """
    if not isinstance(body, dict):
        raise BridgeError(400, "bad_json", "JSON phải là một đối tượng.")
    if "draft_id" not in body:
        raise BridgeError(400, "draft_id_required", "Thiếu draft_id của bản nháp do máy chủ tạo.")
    row = get_draft(c, body.get("draft_id"), user)
    if row["status"] == "rejected":
        raise BridgeError(403, "hitl_rejected", "Bản nháp đã bị từ chối, không thể xuất bản.")
    if row["status"] == "published":
        raise BridgeError(409, "already_published", "Bản nháp này đã được xuất bản trước đó.")

    provided_hash = body.get("plan_hash")
    if not isinstance(provided_hash, str) or not provided_hash.strip() or provided_hash.strip() != row["plan_hash"]:
        raise BridgeError(409, "plan_mismatch", "Mã băm kế hoạch (plan_hash) không khớp hoặc thiếu — vui lòng xem lại và duyệt lại.")

    env = json.loads(row["envelope_json"])
    if isinstance(body.get("envelope"), dict):
        # Chặn mọi cố gắng bơm status APPROVED qua client payload dù đã có draft_id
        for key in ("status", "state"):
            v = body["envelope"].get(key)
            if isinstance(v, str) and v.strip().upper() in ("APPROVED", "PUBLISHED"):
                raise BridgeError(400, "hitl_forbidden", "Không được tự đặt trạng thái APPROVED.")

    active_reg = registry if registry is not None else trusted_registry(c, user=user)
    approval = publish(
        {
            "envelope": env,
            "approved": body.get("approved"),
            "reviewed_knowledge": body.get("reviewed_knowledge"),
        },
        user,
        registry=active_reg,
    )
    if approval["plan_hash"] != row["plan_hash"]:
        raise BridgeError(409, "plan_mismatch", "Kế hoạch đã thay đổi so với bản nháp ban đầu.")

    plan = env["application_plan"]
    player_cfg = plan["player"]
    model_cfg = plan.get("model")
    exam_cfg = plan.get("exam")
    now = time.time()

    try:
        # 1. Player: REUSE giữ nguyên player_id; GENERATE lưu player status='draft', visibility='private' (KHÔNG vào Catalog công khai)
        if player_cfg["mode"] == "reuse_existing":
            player_id = int(player_cfg["player_id"])
            prow = c.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
            if not prow or prow["status"] != "approved":
                raise BridgeError(400, "invalid_player", "Trình chơi tái sử dụng không tồn tại hoặc chưa được duyệt.")
            manifest = json.loads(prow["manifest"])
        else:
            html = player_cfg["html"]
            man, err = contract.parse(html)
            if err:
                raise BridgeError(400, err[0], err[1])
            flags = contract.scan(html)
            if flags:
                raise BridgeError(400, "unsafe_html", "Bản nháp HTML còn cờ cảnh báo an toàn, không thể xuất bản.")
            p_count = c.execute("SELECT COUNT(*) FROM players WHERE owner_id=?", (user["id"],)).fetchone()[0]
            if p_count >= 50:
                raise BridgeError(409, "storage_full", "Mỗi tài khoản có tối đa 50 trình chơi.")
            pcur = c.execute(
                "INSERT INTO players(owner_id,name,description,html,manifest,flags,status,source,visibility,created,updated) "
                "VALUES(?,?,?,?,?,?, 'draft','ai','private',?,?)",
                (user["id"], man["name"], man["description"], html, json.dumps(man), json.dumps(flags), now, now),
            )
            player_id = pcur.lastrowid
            manifest = man

        # 2. Exam: reuse_existing giữ exam_id; generate_new lưu vào bảng exams của giáo viên
        exam_id = None
        content = ""
        if isinstance(exam_cfg, dict):
            if exam_cfg.get("mode") == "reuse_existing":
                exam_id = int(exam_cfg["exam_id"])
                ex_row = c.execute("SELECT id,owner_id,content FROM exams WHERE id=?", (exam_id,)).fetchone()
                if not ex_row or not (ex_row["owner_id"] in (0, user["id"]) or user.get("role") == "admin"):
                    raise BridgeError(400, "invalid_exam", "Bộ đề tái sử dụng không hợp lệ hoặc không thuộc quyền truy cập.")
                content = ex_row["content"]
            elif exam_cfg.get("mode") == "generate_new":
                raw_content = (exam_cfg.get("content") or "").strip()
                if not store.parse_questions(raw_content):
                    raise BridgeError(400, "invalid_exam", "Bộ đề mới không có câu hỏi hợp lệ.")
                e_count = c.execute("SELECT COUNT(*) FROM exams WHERE owner_id=?", (user["id"],)).fetchone()[0]
                if e_count >= 100:
                    raise BridgeError(409, "storage_full", "Mỗi tài khoản có tối đa 100 bộ đề.")
                exam_name = ("Bộ đề: " + plan["name"])[:80]
                ecur = c.execute(
                    "INSERT INTO exams(owner_id,name,description,image,content,created,updated) VALUES(?,?,?,?,?,?,?)",
                    (user["id"], exam_name, "Bộ đề do AI soạn và giáo viên đã kiểm duyệt (HITL).", "", raw_content, now, now),
                )
                exam_id = ecur.lastrowid
                content = raw_content
        elif "content" in manifest:
            demo_items = (manifest.get("demo") or {}).get("content")
            if isinstance(demo_items, list) and demo_items:
                lines = [it.get("text") if isinstance(it, dict) else str(it) for it in demo_items]
                content = "\n".join(x.strip() for x in lines if x and x.strip())

        # 3. App: xác thực qua store.clean_app() (single source of truth cho mapping/sure/hold_ms/share) rồi lưu vào bảng apps (share=0)
        a_count = c.execute("SELECT COUNT(*) FROM apps WHERE owner_id=?", (user["id"],)).fetchone()[0]
        if a_count >= 200:
            raise BridgeError(409, "storage_full", "Mỗi tài khoản có tối đa 200 ứng dụng.")
        model_id = int(model_cfg["model_id"]) if isinstance(model_cfg, dict) and model_cfg.get("model_id") else None
        mapping = model_cfg.get("mapping") if isinstance(model_cfg, dict) and isinstance(model_cfg.get("mapping"), dict) else {}
        sure = model_cfg.get("sure", 0.8) if isinstance(model_cfg, dict) else 0.8
        hold_ms = model_cfg.get("hold_ms", 800) if isinstance(model_cfg, dict) else 800
        app_desc = (
            "Ứng dụng tạo qua AI Game Composer (%s — đã qua HITL)." % env.get("decision", "REUSE")
        )
        v = store.clean_app(c, user, {
            "name": plan["name"].strip()[:80],
            "description": app_desc,
            "playerId": player_id,
            "modelId": model_id,
            "mapping": mapping,
            "content": content,
            "sure": sure,
            "holdMs": hold_ms,
            "share": False,
            "examId": exam_id,
            "image": "",
        })
        acur = c.execute(
            "INSERT INTO apps(owner_id,name,description,player_id,model_id,mapping,content,sure,hold_ms,share,exam_id,image,created) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (user["id"], v[0], v[1], v[2], v[3], json.dumps(v[4], ensure_ascii=False), v[5], v[6], v[7], v[8], v[9], v[10], now),
        )
        app_id = acur.lastrowid

        # 4. Chuyển trạng thái nguyên tử có điều kiện (chống race condition / double publish đồng thời)
        ucur = c.execute(
            "UPDATE agent_drafts SET status='published', app_id=?, player_id=?, exam_id=?, updated=? "
            "WHERE id=? AND status='pending_approval'",
            (app_id, player_id, exam_id, now, row["id"]),
        )
        if ucur.rowcount != 1:
            raise BridgeError(409, "already_published", "Bản nháp này đã được xử lý đồng thời trước đó.")
        c.commit()
    except (BridgeError, store.Err):
        c.rollback()
        raise
    except Exception:
        c.rollback()
        raise

    return approval | {
        "draft_id": row["id"],
        "app_id": app_id,
        "play_url": "/play/%d" % app_id,
        "player_id": player_id,
        "exam_id": exam_id,
        "share": 0,
    }
