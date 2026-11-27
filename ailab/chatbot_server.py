"""I01 — Điểm chạy AI Lab có Trợ lý game mới (hội thoại nhiều lượt, phương án chờ xác nhận).

    python ailab/chatbot_server.py               # AILAB_HOST, AILAB_PORT (8800), AILAB_DB như server.py

Lớp con của server.H: chỉ thêm route chat mới; mọi route khác (kể cả proposal HTML cũ, GET /api/chats) giao nguyên cho base.
Không sửa file gốc; index.html được chèn <script src="/chatbot.js"> TRONG BỘ NHỚ khi phục vụ.
Không tạo Player/Exam/App, không sinh HTML. Spec: docs/chatbot/I01_SPEC.md.
"""
import os
import sys
import threading
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import llm  # noqa: E402
import server  # noqa: E402
import store  # noqa: E402
from chatbot import repository, schemas, workflow  # noqa: E402
from store import Err  # noqa: E402

SCRIPT_TAG = '<script src="/chatbot.js"></script>'
ACTION_NAMES = ("confirm_plan", "cancel_plan")
ACTION_TEXT = {"confirm_plan": "Đã xác nhận yêu cầu sơ bộ phiên bản %d; chưa duyệt kế hoạch ứng dụng hoặc Game Preview.",
               "cancel_plan": "Đã hủy yêu cầu sơ bộ phiên bản %d."}

_schema_lock = threading.Lock()
_schema_done = set()  # DB_PATH đã ensure_schema trong tiến trình này


def model_caller():
    """call_model của model thật nếu đã nối (llm._real_model), ngược lại None = chế độ giả. Test có thể thay hàm này."""
    return llm._real_model()


def _index_html():
    with open(os.path.join(server.WEB, "index.html"), "r", encoding="utf-8") as f:
        html = f.read()
    if SCRIPT_TAG in html:
        return html
    i = html.lower().rfind("</body>")
    return html[:i] + SCRIPT_TAG + html[i:] if i >= 0 else html + SCRIPT_TAG


def _state_view(state):
    """state công khai cho GET /api/chats/<id>: to_public_reply bỏ role/text/simulated/model."""
    r = schemas.to_public_reply(state, "", False, "")
    for k in ("role", "text", "simulated", "model"):
        r.pop(k, None)
    return r


def _invalid(errors):
    e = errors[0]
    f = schemas.make_error("invalid_input", "request", e.get("message") or "Dữ liệu không hợp lệ.",
                           details={"field": e.get("field"), "fields": [x.get("field") for x in errors if x.get("field")]})
    return f


class ChatbotH(server.H):
    server_version = "AILab-Chatbot/1"

    # ---- tĩnh: chèn chatbot.js vào index trong bộ nhớ ----
    def _static(self, path):
        if path in ("/", "", "/index.html"):
            return self._send(200, _index_html(), "text/html; charset=utf-8")
        return super()._static(path)

    # ---- đảm bảo bảng mới có (kể cả khi test khởi ChatbotH mà không qua main) ----
    def _ensure(self, c):
        if store.DB_PATH in _schema_done:
            return
        with _schema_lock:
            if store.DB_PATH not in _schema_done:
                repository.ensure_schema(c)
                _schema_done.add(store.DB_PATH)

    def _authed(self, c, method, p, user):
        parts = p.split("/")
        res = parts[0]
        if res in ("chat", "chats"):
            if parts == ["chat"] and method == "POST":
                self._ensure(c)
                return self._chat_v2(c, user)
            if len(parts) == 2 and res == "chats" and method == "GET":
                self._ensure(c)
                return self._chat_get(c, parts[1], user)
            if len(parts) == 3 and res == "chats" and parts[2] == "actions" and method == "POST":
                self._ensure(c)
                return self._chat_action(c, parts[1], user)
        return super()._authed(c, method, p, user)

    # ---- tiện ích phản hồi lỗi chatbot ----
    def _fail(self, status, failure, extra=None):
        pf = schemas.to_public_failure(failure)
        body = {"error": failure["code"], "message": pf.get("message", ""), "failure": pf}
        body.update(extra or {})
        return self._json(status, body)

    # ---- GET /api/chats/<id> ----
    def _chat_get(self, c, cid, user):
        r = repository.get_chat(c, cid, user)
        msgs = repository.messages_of(r)
        st, _ = repository.load_state(c, r["id"], user)
        return self._json(200, {"id": r["id"], "title": r["title"],
                                "messages": [server._pub(m, i) for i, m in enumerate(msgs)],
                                "state": _state_view(st)})

    # ---- POST /api/chat ----
    def _chat_v2(self, c, user):
        body = self._body()
        body = {k: v for k, v in body.items() if k != "action"}  # route này chỉ nhận tin nhắn
        req, errors = schemas.validate_request(body)
        if errors:
            return self._fail(400, _invalid(errors))
        rid = req["requestId"]
        # Thứ tự: (1) quyền chat -> (2) chống trùng (replay trả response cũ) -> (3) chỉ request MỚI mới bị kiểm chat đầy.
        if req["chatId"]:
            row = repository.get_chat(c, req["chatId"], user)  # của người khác / không có -> 404 trước mọi thứ
            cid = row["id"]
        else:
            row, cid = None, None
        fp = repository.fingerprint({"action": "message", "chatId": req["chatId"], "text": req["text"],
                                     "expectedVersion": req["expectedVersion"]})
        # chống trùng TRƯỚC khi tạo chat mới: gửi lại cùng requestId không tạo thêm chat rỗng
        prev = repository.begin_request(c, user, rid, cid, "message", fp)
        if prev is not None:
            return self._json(200, prev)
        try:
            if row is not None and len(repository.messages_of(row)) >= repository.MAX_MESSAGES:
                raise Err(409, "chat_full", "Cuộc trò chuyện này đã dài. Mở cuộc mới nhé.")  # except bên dưới xoá pending
            if cid is None:
                cid = repository.create_chat(c, user, req["text"][:60])
                row = repository.get_chat(c, cid, user)
            state, version = repository.load_state(c, cid, user)
            context = {"call_model": model_caller(), "history": repository.history_of(row),
                       "catalog": repository.catalog_for(c, user)}
            if c.in_transaction:
                c.commit()
            assert not c.in_transaction  # không giữ giao dịch khi gọi AI
            new_state, text, meta = workflow.process_turn(req, state, context)
            failure = meta.get("failure")
            if failure and failure.get("code") == "stale_version":
                repository.drop_request(c, user, rid)
                return self._fail(409, failure, {"stateVersion": version, "chatId": cid})
            if failure:
                new_state = state  # lỗi AI: state KHÔNG đổi, nhưng vẫn lưu lịch sử
            reply = schemas.to_public_reply(new_state, text, meta.get("simulated"), meta.get("model") or "", failure)
            bot = {"role": "bot", "text": reply["text"], "simulated": reply["simulated"], "model": reply["model"],
                   "kind": "chat_v2", "status": reply["status"], "stateVersion": reply["stateVersion"]}
            if reply.get("error"):
                bot["error"] = reply["error"]
            response = {"chatId": cid, "reply": reply}
            f2, cur = repository.save_turn(c, cid, user, version, new_state,
                                           [{"role": "user", "text": req["text"]}, bot], rid, response)
            if f2:
                repository.drop_request(c, user, rid)
                return self._fail(409, f2, {"stateVersion": cur, "chatId": cid})
            return self._json(200, response)
        except BaseException:
            repository.drop_request(c, user, rid)
            raise

    # ---- POST /api/chats/<id>/actions ----
    def _chat_action(self, c, cid_raw, user):
        row = repository.get_chat(c, cid_raw, user)
        cid = row["id"]
        body = self._body()
        action = body.get("action")
        if action not in ACTION_NAMES:
            f = schemas.make_error("invalid_input", "request", "action chỉ nhận: " + ", ".join(ACTION_NAMES) + ".",
                                   details={"field": "action"})
            return self._fail(400, f)
        req, errors = schemas.validate_request({"action": action, "chatId": cid, "proposalId": body.get("proposalId"),
                                                "version": body.get("version"), "requestId": body.get("requestId")})
        if errors:
            return self._fail(400, _invalid(errors))
        rid = req["requestId"]
        fp = repository.fingerprint({"action": action, "chatId": cid, "proposalId": req["proposalId"], "version": req["version"]})
        prev = repository.begin_request(c, user, rid, cid, action, fp)
        if prev is not None:
            return self._json(200, prev)
        try:
            state, version = repository.load_state(c, cid, user)
            if action == "confirm_plan":
                new_state, failure = workflow.confirm_plan(state, req["proposalId"], req["version"])
            else:
                new_state, failure = workflow.cancel_plan(state, req["proposalId"], req["version"])
            if failure:
                repository.drop_request(c, user, rid)
                status = 409 if failure["code"] == "stale_version" else 400
                return self._fail(status, failure, {"stateVersion": version, "chatId": cid})
            text = ACTION_TEXT[action] % req["version"]
            # A confirmation click does not make a mock-generated proposal real.
            proposal = new_state.get("proposal") or {}
            simulated = proposal.get("simulated")
            if not isinstance(simulated, bool):
                simulated = True  # unknown provenance on legacy proposals
            reply = schemas.to_public_reply(new_state, text, simulated, "")
            new_msgs = []
            if new_state["version"] != version:  # bấm lại xác nhận cùng bản: không thêm tin nhắn, không tăng version
                new_msgs = [{"role": "bot", "text": reply["text"], "simulated": simulated, "model": "", "kind": "action_v2",
                             "action": action, "status": reply["status"], "stateVersion": reply["stateVersion"]}]
            response = {"chatId": cid, "reply": reply}
            f2, cur = repository.save_turn(c, cid, user, version, new_state, new_msgs, rid, response)
            if f2:
                repository.drop_request(c, user, rid)
                return self._fail(409, f2, {"stateVersion": cur, "chatId": cid})
            return self._json(200, response)
        except BaseException:
            repository.drop_request(c, user, rid)
            raise


def _utf8_streams():
    """Windows: stdout/stderr chuyển ra file/pipe mặc định cp1252 -> in tiếng Việt bị UnicodeEncodeError. Ép UTF-8 an toàn."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        except (AttributeError, ValueError, OSError):
            pass


def main():
    _utf8_streams()
    if len(sys.argv) > 1 and sys.argv[1] in ("create-user", "set-password"):
        sys.exit(server.cli(sys.argv[1:]))
    host = os.environ.get("AILAB_HOST", "127.0.0.1")
    port = int(os.environ.get("AILAB_PORT", "8800"))
    made = store.init(os.environ.get("AILAB_ADMIN_PASSWORD"))
    c = store.connect()
    try:
        repository.ensure_schema(c)
        _schema_done.add(store.DB_PATH)
    finally:
        c.close()
    print("AI Lab (Trợ lý game mới): http://%s:%d   (SQLite: %s)" % (host, port, store.DB_PATH))
    print("Model AI: %s" % ("GIẢ (fake-rules, không phải AI thật)" if llm._real_model() is None else "thật"))
    if made:
        print("Tài khoản Admin đầu tiên: admin / %s   (hiện một lần — hãy đổi bằng set-password)" % made
              if not os.environ.get("AILAB_ADMIN_PASSWORD") else "Tài khoản Admin đầu tiên: admin (mật khẩu từ AILAB_ADMIN_PASSWORD)")
    ThreadingHTTPServer((host, port), ChatbotH).serve_forever()


if __name__ == "__main__":
    main()
