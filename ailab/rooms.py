"""Phòng chơi: một chủ phòng (đăng nhập) mở phòng cho một ứng dụng, các thành viên vào bằng mã phòng + biệt danh (không cần tài khoản).
Mỗi người chơi trên máy của mình; điểm gửi về phòng khi trò chơi báo 'finish'. Đồng bộ bằng polling (khung chỉ dùng thư viện chuẩn).
Vòng đời: lobby (chờ) → playing (chủ bấm Bắt đầu) → ended (chủ kết thúc, hoặc quá 24 giờ)."""
import json
import secrets
import time

import store
from store import Err

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # bỏ I, O, 0, 1 cho dễ đọc
CODE_LEN = 6
MAX_MEMBERS = 60
MAX_OPEN_ROOMS = 10  # mỗi chủ phòng
TTL = 24 * 3600
CODE_CHARS = set(ALPHABET)

SCHEMA = """
CREATE TABLE IF NOT EXISTS rooms(code TEXT PRIMARY KEY, app_id INTEGER NOT NULL, host_id INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'lobby' CHECK(status IN ('lobby','playing','ended')), created REAL NOT NULL, started REAL, ended REAL);
CREATE TABLE IF NOT EXISTS room_members(id INTEGER PRIMARY KEY, code TEXT NOT NULL REFERENCES rooms(code) ON DELETE CASCADE,
  name TEXT NOT NULL, token TEXT NOT NULL UNIQUE, joined REAL NOT NULL, correct INTEGER, total INTEGER, finished REAL,
  UNIQUE(code, name));
"""


def ensure(c):
    c.executescript(SCHEMA)


def norm_code(code):
    code = (code or "").strip().upper()
    if len(code) != CODE_LEN or not set(code) <= CODE_CHARS:
        raise Err(404, "no_room", "Không thấy phòng này. Kiểm tra lại mã phòng.")
    return code


def _room(c, code):
    code = norm_code(code)
    r = c.execute("SELECT * FROM rooms WHERE code=?", (code,)).fetchone()
    if not r:
        raise Err(404, "no_room", "Không thấy phòng này. Kiểm tra lại mã phòng.")
    if r["status"] != "ended" and time.time() - r["created"] > TTL:
        c.execute("UPDATE rooms SET status='ended', ended=? WHERE code=?", (time.time(), code))
        c.commit()
        r = c.execute("SELECT * FROM rooms WHERE code=?", (code,)).fetchone()
    return r


def create(c, user, app_id):
    try:
        aid = int(app_id)
    except (TypeError, ValueError):
        raise Err(400, "app", "Chọn trò chơi để mở phòng.")
    a = c.execute("SELECT * FROM apps WHERE id=?", (aid,)).fetchone()
    if not a or not (a["owner_id"] == user["id"] or user["role"] == "admin"):
        raise Err(404, "not_found", "Không thấy trò chơi này.")
    n = c.execute("SELECT COUNT(*) FROM rooms WHERE host_id=? AND status!='ended' AND created>?", (user["id"], time.time() - TTL)).fetchone()[0]
    if n >= MAX_OPEN_ROOMS:
        raise Err(409, "too_many_rooms", "Bạn đang mở quá nhiều phòng. Kết thúc bớt phòng cũ rồi thử lại.")
    for _ in range(20):
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LEN))
        if not c.execute("SELECT 1 FROM rooms WHERE code=?", (code,)).fetchone():
            c.execute("INSERT INTO rooms(code,app_id,host_id,created) VALUES(?,?,?,?)", (code, aid, user["id"], time.time()))
            c.commit()
            return code
    raise Err(500, "server", "Không tạo được mã phòng, thử lại.")


def _member_by_token(c, code, token):
    if not token:
        return None
    return c.execute("SELECT * FROM room_members WHERE code=? AND token=?", (code, token)).fetchone()


def _is_host(r, user):
    return bool(user) and (user["id"] == r["host_id"] or user["role"] == "admin")


def state(c, code, user, token):
    """Trạng thái phòng cho người đang xem. Không bao giờ trả token của thành viên khác."""
    r = _room(c, code)
    host = _is_host(r, user)
    me = _member_by_token(c, r["code"], token)
    app = c.execute("SELECT name, description FROM apps WHERE id=?", (r["app_id"],)).fetchone()
    rows = c.execute("SELECT id,name,correct,total,finished,joined FROM room_members WHERE code=?", (r["code"],)).fetchall()
    members = [dict(x) for x in rows]
    done = sorted([m for m in members if m["finished"] is not None], key=lambda m: (-m["correct"], m["finished"]))
    wait = sorted([m for m in members if m["finished"] is None], key=lambda m: m["joined"])
    for i, m in enumerate(done):
        m["rank"] = i + 1
    out = {"code": r["code"], "status": r["status"], "app": {"id": r["app_id"], "name": app["name"] if app else "(đã xoá)",
           "description": app["description"] if app else ""},
           "host": host, "role": "host" if host else ("member" if me else None), "members": done + wait,
           "me": {"id": me["id"], "name": me["name"]} if me else None, "now": time.time()}
    return out


def join(c, code, name):
    r = _room(c, code)
    if r["status"] == "ended":
        raise Err(409, "ended", "Phòng này đã kết thúc.")
    if not isinstance(name, str) or not (1 <= len(name.strip()) <= 20):
        raise Err(400, "name", "Biệt danh dài 1–20 ký tự.")
    name = " ".join(name.split())
    if c.execute("SELECT COUNT(*) FROM room_members WHERE code=?", (r["code"],)).fetchone()[0] >= MAX_MEMBERS:
        raise Err(409, "full", "Phòng đã đủ %d người." % MAX_MEMBERS)
    if c.execute("SELECT 1 FROM room_members WHERE code=? AND lower(name)=lower(?)", (r["code"], name)).fetchone():
        raise Err(409, "name_taken", "Biệt danh này đã có người dùng trong phòng. Chọn biệt danh khác.")
    token = secrets.token_urlsafe(18)
    cur = c.execute("INSERT INTO room_members(code,name,token,joined) VALUES(?,?,?,?)", (r["code"], name, token, time.time()))
    c.commit()
    return {"token": token, "member": {"id": cur.lastrowid, "name": name}}


def start(c, code, user):
    r = _room(c, code)
    if not _is_host(r, user):
        raise Err(403, "forbidden", "Chỉ chủ phòng được bắt đầu.")
    if r["status"] == "ended":
        raise Err(409, "ended", "Phòng này đã kết thúc.")
    if r["status"] == "lobby":
        c.execute("UPDATE rooms SET status='playing', started=? WHERE code=?", (time.time(), r["code"]))
        c.commit()


def end(c, code, user):
    r = _room(c, code)
    if not _is_host(r, user):
        raise Err(403, "forbidden", "Chỉ chủ phòng được kết thúc.")
    if r["status"] != "ended":
        c.execute("UPDATE rooms SET status='ended', ended=? WHERE code=?", (time.time(), r["code"]))
        c.commit()


def kick(c, code, user, member_id):
    r = _room(c, code)
    if not _is_host(r, user):
        raise Err(403, "forbidden", "Chỉ chủ phòng được mời người ra.")
    c.execute("DELETE FROM room_members WHERE code=? AND id=?", (r["code"], member_id if isinstance(member_id, int) else -1))
    c.commit()


def submit(c, code, token, correct, total):
    r = _room(c, code)
    me = _member_by_token(c, r["code"], token)
    if not me:
        raise Err(403, "not_member", "Bạn chưa vào phòng này.")
    if r["status"] != "playing":
        raise Err(409, "not_playing", "Phòng không đang chơi.")
    if not (isinstance(correct, int) and isinstance(total, int)) or isinstance(correct, bool) or isinstance(total, bool) \
            or not (0 <= correct <= total <= 1000):
        raise Err(400, "score", "Điểm không hợp lệ.")
    if me["finished"] is not None:
        return  # chỉ tính lần đầu
    c.execute("UPDATE room_members SET correct=?, total=?, finished=? WHERE id=?", (correct, total, time.time(), me["id"]))
    c.commit()


def play_data(c, code, user, token):
    """Dữ liệu chạy trò chơi của phòng: không cần ứng dụng bật Chia sẻ. Thành viên chỉ nhận khi phòng đang chơi; chủ phòng xem thử được."""
    r = _room(c, code)
    host = _is_host(r, user)
    if not host:
        if not _member_by_token(c, r["code"], token):
            raise Err(403, "not_member", "Bạn chưa vào phòng này.")
        if r["status"] != "playing":
            raise Err(409, "not_playing", "Chủ phòng chưa bắt đầu." if r["status"] == "lobby" else "Phòng đã kết thúc.")
    return store.play_data(c, r["app_id"], user, force=True)
