"""I01 — Lưu trữ cho chatbot: state có version, chống trùng requestId, quyền theo chủ chat.

Mọi hàm nhận kết nối `c` (sqlite3, từ handler); không giữ kết nối toàn cục.
Quy tắc giao dịch: không giữ giao dịch khi gọi AI. Hàm nào ghi thì tự BEGIN IMMEDIATE ... COMMIT/ROLLBACK.
Spec: docs/chatbot/I01_SPEC.md §3–§4.
"""
import hashlib
import json
import time

import store
from store import Err

from . import schemas as S

DDL = """
CREATE TABLE IF NOT EXISTS chat_states(chat_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, version INTEGER NOT NULL,
  state TEXT NOT NULL, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS chat_requests(user_id INTEGER NOT NULL, request_id TEXT NOT NULL, chat_id INTEGER, action TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('pending','done')), response TEXT, created REAL NOT NULL,
  PRIMARY KEY(user_id, request_id));
"""

MAX_MESSAGES = 60


def ensure_schema(c):
    """Tạo 2 bảng mới (không đụng bảng cũ), commit."""
    if c.in_transaction:
        c.commit()
    c.executescript(DDL)
    c.commit()


def _begin(c):
    """Mở giao dịch ghi. Giao dịch ngầm còn treo (do sqlite3 tự mở) được commit trước để không lẫn."""
    if c.in_transaction:
        c.commit()
    c.execute("BEGIN IMMEDIATE")


def _uid(user):
    return user["id"]


# ---------------------------------------------------------------- chat
def get_chat(c, chat_id, user):
    """Row `chats` của đúng user; không có hoặc của người khác -> Err(404) (không phân biệt hai trường hợp)."""
    try:
        cid = int(chat_id)
    except (TypeError, ValueError):
        raise Err(404, "not_found", "Không thấy cuộc trò chuyện này.")
    r = c.execute("SELECT * FROM chats WHERE id=? AND user_id=?", (cid, _uid(user))).fetchone()
    if not r:
        raise Err(404, "not_found", "Không thấy cuộc trò chuyện này.")
    return r


def create_chat(c, user, title):
    """Tạo chat rỗng và commit NGAY (trước khi gọi AI) -> chat_id."""
    _begin(c)
    try:
        cur = c.execute("INSERT INTO chats(user_id,title,created) VALUES(?,?,?)", (_uid(user), (title or "")[:60], time.time()))
        c.commit()
    except BaseException:
        c.rollback()
        raise
    return cur.lastrowid


def messages_of(row):
    try:
        msgs = json.loads(row["messages"] or "[]")
    except ValueError:
        msgs = []
    return msgs if isinstance(msgs, list) else []


def history_of(row):
    """Tin nhắn cũ dạng {role,text} (không HTML) để làm ngữ cảnh cho AI thật."""
    out = []
    for m in messages_of(row):
        if isinstance(m, dict) and m.get("role") in ("user", "bot") and isinstance(m.get("text"), str):
            out.append({"role": m["role"], "text": m["text"]})
    return out


# ---------------------------------------------------------------- state
def load_state(c, chat_id, user):
    """(state, version). Chưa có state (chat mới hoặc chat cũ) -> (schemas.new_state(), 0)."""
    r = c.execute("SELECT state, version FROM chat_states WHERE chat_id=? AND user_id=?", (chat_id, _uid(user))).fetchone()
    if not r:
        return S.new_state(), 0
    try:
        data = json.loads(r["state"])
    except ValueError:
        data = None
    st = S.normalize_state(data)
    st["version"] = r["version"]  # cột version là nguồn chuẩn
    return st, r["version"]


# ---------------------------------------------------------------- chống trùng requestId
def fingerprint(payload):
    """Dấu vân tay của nội dung request (action, chatId gửi lên, text/proposalId/version, expectedVersion)."""
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _stored(raw):
    """Đọc cột response: dạng mới {"fp","status","body"}; dạng cũ (chỉ body) vẫn đọc được."""
    try:
        d = json.loads(raw) if raw else None
    except ValueError:
        d = None
    if isinstance(d, dict) and "fp" in d:
        return d
    return {"fp": None, "status": 200, "body": d}


def begin_request(c, user, request_id, chat_id, action, fp=None):
    """None nếu request mới (ghi pending + commit); dict response đã lưu nếu done; Err(409,'duplicate_pending') nếu đang xử lý.
    fp (fingerprint) khác với lần đầu -> Err(409,'request_mismatch') (không xử lý như request mới).
    Khóa (user_id, request_id): chỉ thấy request của chính user. request_id=None -> bỏ qua (None)."""
    if not request_id:
        return None
    _begin(c)
    try:
        r = c.execute("SELECT status, response FROM chat_requests WHERE user_id=? AND request_id=?",
                      (_uid(user), request_id)).fetchone()
        if r is None:
            c.execute("INSERT INTO chat_requests(user_id,request_id,chat_id,action,status,response,created) "
                      "VALUES(?,?,?,?, 'pending', ?, ?)",
                      (_uid(user), request_id, chat_id, action, json.dumps({"fp": fp}), time.time()))
            c.commit()
            return None
        c.rollback()
    except BaseException:
        if c.in_transaction:
            c.rollback()
        raise
    st = _stored(r["response"])
    if st["fp"] is not None and fp is not None and st["fp"] != fp:
        raise Err(409, "request_mismatch", "requestId này đã dùng cho một yêu cầu khác. Hãy tạo requestId mới.")
    if r["status"] == "done" and st.get("body") is not None:
        return st["body"]
    raise Err(409, "duplicate_pending", "Yêu cầu này đang được xử lý. Chờ một chút rồi tải lại.")


def finish_request(c, user, request_id, response, chat_id=None, status=200):
    """Ghi done + response (giữ fingerprint lúc begin). KHÔNG commit: gọi bên trong giao dịch lưu (save_turn)."""
    if not request_id:
        return
    r = c.execute("SELECT response FROM chat_requests WHERE user_id=? AND request_id=?", (_uid(user), request_id)).fetchone()
    fp = _stored(r["response"])["fp"] if r else None
    blob = json.dumps({"fp": fp, "status": status, "body": response}, ensure_ascii=False)
    c.execute("UPDATE chat_requests SET status='done', response=?, chat_id=COALESCE(?, chat_id) "
              "WHERE user_id=? AND request_id=?", (blob, chat_id, _uid(user), request_id))


def drop_request(c, user, request_id):
    """Xoá bản ghi pending (lỗi giữa chừng / stale) để client thử lại được cùng requestId. Tự commit."""
    if not request_id:
        return
    if c.in_transaction:
        c.rollback()
    c.execute("DELETE FROM chat_requests WHERE user_id=? AND request_id=? AND status='pending'", (_uid(user), request_id))
    c.commit()


# ---------------------------------------------------------------- lưu một lượt (nguyên tử)
def save_turn(c, chat_id, user, old_version, new_state, new_messages, request_id, response):
    """Một giao dịch BEGIN IMMEDIATE: đọc lại version -> lệch thì ROLLBACK và trả failure stale_version;
    khớp thì nối tin nhắn vào chats.messages, ghi state (chỉ khi version đổi), finish_request, COMMIT -> None.

    Trả (failure, current_version): failure=None khi lưu xong."""
    uid = _uid(user)
    _begin(c)
    try:
        r = c.execute("SELECT version FROM chat_states WHERE chat_id=?", (chat_id,)).fetchone()
        current = r["version"] if r else 0
        if current != old_version:
            c.rollback()
            f = S.make_error("stale_version", "persist", "Cuộc trò chuyện đã có lượt mới hơn. Tải lại để xem bản mới nhất.",
                             details={"expectedVersion": old_version, "currentVersion": current})
            return f, current
        if new_messages:
            row = c.execute("SELECT messages FROM chats WHERE id=? AND user_id=?", (chat_id, uid)).fetchone()
            if row is None:
                c.rollback()
                raise Err(404, "not_found", "Không thấy cuộc trò chuyện này.")
            msgs = messages_of(row) + list(new_messages)
            c.execute("UPDATE chats SET messages=? WHERE id=?", (json.dumps(msgs, ensure_ascii=False), chat_id))
        nv = new_state["version"]
        if nv != old_version:
            blob = json.dumps(new_state, ensure_ascii=False)
            if r is None:
                c.execute("INSERT INTO chat_states(chat_id,user_id,version,state,updated) VALUES(?,?,?,?,?)",
                          (chat_id, uid, nv, blob, time.time()))
            else:
                cur = c.execute("UPDATE chat_states SET version=?, state=?, updated=? WHERE chat_id=? AND version=?",
                                (nv, blob, time.time(), chat_id, old_version))
                if cur.rowcount != 1:  # không thể xảy ra dưới BEGIN IMMEDIATE, giữ cho chắc
                    c.rollback()
                    return S.make_error("stale_version", "persist", "Cuộc trò chuyện đã có lượt mới hơn.",
                                        details={"expectedVersion": old_version}), None
        finish_request(c, user, request_id, response, chat_id)
        c.commit()
        return None, nv
    except BaseException:
        if c.in_transaction:
            c.rollback()
        raise


# ---------------------------------------------------------------- danh mục cho AI
def catalog_for(c, user):
    """{"players":[{id,name,manifest}]} — chỉ Player user dùng được (store.player_usable), không HTML."""
    out = []
    for r in c.execute("SELECT id, owner_id, name, manifest, status, visibility FROM players ORDER BY id").fetchall():
        if not store.player_usable(r, user):
            continue
        try:
            man = json.loads(r["manifest"])
        except ValueError:
            man = {}
        out.append({"id": r["id"], "name": r["name"], "manifest": man})
    return {"players": out}
