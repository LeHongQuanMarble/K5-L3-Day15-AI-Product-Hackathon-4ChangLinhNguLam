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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "codebase")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ai  # noqa: E402  (ProviderError — định nghĩa ở codebase/ai.py)
import agent  # noqa: E402  (Shared Core, dùng chung với python run.py)
import application_contract as ac  # noqa: E402
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


def trusted_registry(c):
    """Registry tin cậy lấy từ Catalog hiện tại (để validate_application_plan ở ranh giới)."""
    def rows(sql):
        out = []
        for r in c.execute(sql).fetchall():
            d = dict(r)
            if "manifest" in d and isinstance(d["manifest"], str):
                try:
                    d["manifest"] = json.loads(d["manifest"])
                except ValueError:
                    d["manifest"] = {}
            out.append(d)
        return out
    return {
        "players": rows("SELECT id,name,manifest FROM players WHERE status='approved'"),
        # Bảng models không có cột status (xem store.py); dùng toàn bộ Catalog model.
        "models": rows("SELECT id,name,kind FROM models"),
        "exams": rows("SELECT id,name,content FROM exams"),
    }


def call(payload, case_id="web-req", registry=None):
    """Gọi Shared Core. Trả dict {envelope, ui, trace, knowledge_review_required}.

    `payload` là Spec request dict (xem handoff T08/T09 mục 1) hoặc chuỗi yêu cầu.
    Không nuốt ProviderError — để server ánh xạ thành 502/503.
    """
    session_id = payload.get("session_id") if isinstance(payload, dict) else None
    tracing.begin(str(session_id or case_id))
    try:
        envelope = agent.run_agent(payload, registry=registry)
    except ai.ProviderError as exc:
        # Kết thúc trace để ghi trung thực lỗi, rồi ném ra cho server ánh xạ 502/503.
        tracing.end()
        raise provider_error(exc) from None
    summary, _ = tracing.end()
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
    return {"envelope": envelope, "ui": ui, "trace": summary,
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
