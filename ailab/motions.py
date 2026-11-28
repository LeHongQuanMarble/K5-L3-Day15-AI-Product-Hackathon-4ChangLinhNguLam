"""Motion (bài giảng dạng video tương tác) — luồng như learning: trò chuyện với AI → kịch bản → dựng bài → phiên bản.

Giáo viên nhắn với chatbot; chatbot viết/sửa KỊCH BẢN (văn bản chia cảnh). Bấm "Dựng bài" thì một việc nền đọc kịch bản, dựng từng
cảnh (có tiến độ "cảnh 2/5", huỷ được) thành MỘT tệp HTML tự chứa (không mạng, không mã do AI viết: AI chỉ viết chữ, mã do khung sinh ra),
lưu thành một phiên bản. Bản HTML chạy trong iframe sandbox. Chỉ thư viện chuẩn.

Kịch bản:  dòng "# Tiêu đề bài", rồi mỗi cảnh:
    ## Tên cảnh
    Hình: 🎯            (tuỳ chọn, một biểu tượng)
    - ý chính 1         (tối đa 5 ý hiện lần lượt)
    Lời: câu thuyết minh (nhiều dòng "Lời:" nối nhau; trình duyệt đọc to nếu có giọng tiếng Việt)
"""
import html as htmllib
import json
import os
import re
import sys
import threading
import time

import store
from store import Err

MAX_SCENES, MAX_SCRIPT, MAX_MSG = 20, 20000, 4000
_wake = threading.Event()
_running = {"id": None, "cancel": False}

SCHEMA = """
CREATE TABLE IF NOT EXISTS motions(id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, title TEXT NOT NULL, script TEXT NOT NULL DEFAULT '',
  created REAL NOT NULL, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS motion_messages(id INTEGER PRIMARY KEY, motion_id INTEGER NOT NULL, role TEXT NOT NULL, kind TEXT NOT NULL,
  body TEXT NOT NULL DEFAULT '', meta TEXT NOT NULL DEFAULT '{}', request_id INTEGER, at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS motion_requests(id INTEGER PRIMARY KEY, motion_id INTEGER NOT NULL, task TEXT NOT NULL, body TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0, total INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS motion_versions(id INTEGER PRIMARY KEY, motion_id INTEGER NOT NULL, n INTEGER NOT NULL, html TEXT NOT NULL,
  scenes INTEGER NOT NULL, seconds INTEGER NOT NULL, created REAL NOT NULL);
"""

FAIL = {
    "empty_script": "Kịch bản đang trống. Nhắn AI viết kịch bản, hoặc tự viết ở cột giữa.",
    "no_scenes": "Kịch bản chưa có cảnh nào. Mỗi cảnh bắt đầu bằng dòng “## Tên cảnh”.",
    "too_many_scenes": "Kịch bản quá %d cảnh. Rút gọn lại." % MAX_SCENES,
    "ai_failed": "Không gọi được model AI. Thử lại sau.",
    "server_restarted": "Máy chủ khởi động lại giữa chừng. Gửi lại yêu cầu.",
    "build_failed": "Không dựng được bài. Thử lại.",
}


def init(c):
    c.executescript(SCHEMA)


# ---------- kịch bản ----------
def parse_script(text):
    """Trả (tiêu đề, [cảnh]) — cảnh {title, icon, points[], lines[]}. Không ném lỗi vì chữ lạ; thiếu cảnh thì trả danh sách rỗng."""
    title, scenes, cur = "", [], None
    for raw in (text or "").splitlines():
        ln = raw.strip()
        if not ln:
            continue
        if ln.startswith("## "):
            cur = {"title": ln[3:].strip()[:120], "icon": "", "points": [], "lines": []}
            scenes.append(cur)
        elif ln.startswith("# ") and not title:
            title = ln[2:].strip()[:120]
        elif cur is None:
            continue
        elif re.match(r"^(Hình|Hinh)\s*:", ln):
            cur["icon"] = ln.split(":", 1)[1].strip()[:4]
        elif re.match(r"^(Lời|Loi)\s*:", ln):
            cur["lines"].append(ln.split(":", 1)[1].strip()[:400])
        elif ln[:2] in ("- ", "* "):
            if len(cur["points"]) < 5:
                cur["points"].append(ln[2:].strip()[:160])
        else:
            cur["lines"].append(ln[:400])
    return title, scenes


def scene_seconds(sc):
    words = len(" ".join(sc["lines"] + sc["points"]).split())
    return max(5, min(40, round(words / 2.5) + 3))


def render(title, scenes):
    """Một tệp HTML tự chứa. Mọi chữ đi qua JSON + textContent ở phía trình duyệt, nên không có chỗ nào chèn mã được."""
    data = [{"title": s["title"], "icon": s["icon"], "points": s["points"], "lines": s["lines"], "sec": scene_seconds(s)} for s in scenes]
    bs = chr(92)
    payload = json.dumps({"title": title, "scenes": data}, ensure_ascii=False).replace("<", bs + "u003c").replace("&", bs + "u0026")
    return PLAYER.replace("__TITLE__", htmllib.escape(title or "Motion")).replace("__DATA__", payload)


# ---------- truy vấn ----------
def _own(c, mid, user):
    r = c.execute("SELECT * FROM motions WHERE id=?", (mid,)).fetchone()
    if not r or (r["owner_id"] != user["id"] and user["role"] != "admin"):
        raise Err(404, "not_found", "Không thấy motion này.")
    return r


def _latest(c, mid):
    return c.execute("SELECT n,scenes,seconds,created FROM motion_versions WHERE motion_id=? ORDER BY n DESC LIMIT 1", (mid,)).fetchone()


def row(c, r, full=False):
    v = _latest(c, r["id"])
    d = {"id": r["id"], "title": r["title"], "created": r["created"], "updated": r["updated"], "version": dict(v) if v else None}
    if full:
        d["script"] = r["script"]
    return d


def mine(c, user):
    rows = c.execute("SELECT * FROM motions WHERE owner_id=? ORDER BY updated DESC", (user["id"],)).fetchall()
    return [row(c, r) for r in rows]


def _title(d):
    title = re.sub(r"\s+", " ", str(d.get("title") or "")).strip()
    if not 1 <= len(title) <= 120:
        raise Err(400, "bad_title", "Tên motion dài 1 đến 120 ký tự.")
    return title


def create(c, user, d):
    title = _title(d)
    now = time.time()
    cur = c.execute("INSERT INTO motions(owner_id,title,script,created,updated) VALUES(?,?,?,?,?)", (user["id"], title, "", now, now))
    c.commit()
    return cur.lastrowid


def get(c, mid, user):
    return row(c, _own(c, mid, user), True)


def rename(c, mid, user, d):
    _own(c, mid, user)
    c.execute("UPDATE motions SET title=?,updated=? WHERE id=?", (_title(d), time.time(), mid))
    c.commit()


def delete(c, mid, user):
    _own(c, mid, user)
    if _open(c, mid):
        raise Err(409, "busy", "Một yêu cầu đang chạy. Huỷ rồi xoá.")
    for t in ("motion_messages", "motion_requests", "motion_versions"):
        c.execute("DELETE FROM %s WHERE motion_id=?" % t, (mid,))
    c.execute("DELETE FROM motions WHERE id=?", (mid,))
    c.commit()


def _msg(c, mid, role, kind, body, meta=None, rid=None):
    c.execute("INSERT INTO motion_messages(motion_id,role,kind,body,meta,request_id,at) VALUES(?,?,?,?,?,?,?)",
              (mid, role, kind, body, json.dumps(meta or {}, ensure_ascii=False), rid, time.time()))


def save_script(c, mid, user, d):
    _own(c, mid, user)
    text = str(d.get("script") or "")
    if len(text) > MAX_SCRIPT:
        raise Err(413, "too_big", "Kịch bản quá dài (tối đa %d ký tự)." % MAX_SCRIPT)
    c.execute("UPDATE motions SET script=?,updated=? WHERE id=?", (text, time.time(), mid))
    _, scenes = parse_script(text)
    _msg(c, mid, "teacher", "script_changed", "Bạn sửa kịch bản (%d cảnh)" % len(scenes))
    c.commit()


def thread(c, mid, user):
    _own(c, mid, user)
    msgs = [{"id": r["id"], "role": r["role"], "kind": r["kind"], "body": r["body"], "meta": json.loads(r["meta"] or "{}"), "requestId": r["request_id"], "at": r["at"]}
            for r in c.execute("SELECT * FROM motion_messages WHERE motion_id=? ORDER BY id", (mid,))]
    o = c.execute("SELECT * FROM motion_requests WHERE motion_id=? AND status IN ('queued','running') ORDER BY id LIMIT 1", (mid,)).fetchone()
    open_ = {"id": o["id"], "task": o["task"], "status": o["status"], "done": o["done"], "total": o["total"]} if o else None
    return {"messages": msgs, "open": open_}


def versions(c, mid, user):
    _own(c, mid, user)
    return [dict(r) for r in c.execute("SELECT n,scenes,seconds,created FROM motion_versions WHERE motion_id=? ORDER BY n DESC", (mid,))]


def version_html(c, mid, n, user):
    _own(c, mid, user)
    r = c.execute("SELECT html FROM motion_versions WHERE motion_id=? AND n=?", (mid, n)).fetchone()
    if not r:
        raise Err(404, "not_found", "Không thấy phiên bản này.")
    return r["html"]


def _open(c, mid):
    return c.execute("SELECT 1 FROM motion_requests WHERE motion_id=? AND status IN ('queued','running')", (mid,)).fetchone()


def ask(c, mid, user, d):
    """Giáo viên nhắn AI (viết/sửa kịch bản)."""
    _own(c, mid, user)
    body = str(d.get("body") or "").strip()
    if not body:
        raise Err(400, "empty", "Hãy nhập nội dung.")
    if len(body) > MAX_MSG:
        raise Err(413, "too_big", "Tin nhắn quá dài.")
    if _open(c, mid):
        raise Err(409, "busy", "Một yêu cầu đang chạy. Chờ xong hoặc huỷ.")
    now = time.time()
    cur = c.execute("INSERT INTO motion_requests(motion_id,task,body,status,created) VALUES(?,?,?,'queued',?)", (mid, "script", body, now))
    _msg(c, mid, "teacher", "text", body)
    c.execute("UPDATE motions SET updated=? WHERE id=?", (now, mid))
    c.commit()
    _wake.set()
    return cur.lastrowid


def build(c, mid, user):
    _own(c, mid, user)
    if _open(c, mid):
        raise Err(409, "busy", "Một yêu cầu đang chạy. Chờ xong hoặc huỷ.")
    cur = c.execute("INSERT INTO motion_requests(motion_id,task,status,created) VALUES(?,?,'queued',?)", (mid, "build", time.time()))
    _msg(c, mid, "ai", "build_queued", "", rid=cur.lastrowid)
    c.commit()
    _wake.set()
    return cur.lastrowid


def cancel(c, mid, user, rid):
    _own(c, mid, user)
    r = c.execute("SELECT * FROM motion_requests WHERE id=? AND motion_id=?", (rid, mid)).fetchone()
    if not r or r["status"] not in ("queued", "running"):
        return
    if r["status"] == "running" and _running["id"] == rid:
        _running["cancel"] = True
        return
    c.execute("UPDATE motion_requests SET status='cancelled' WHERE id=? AND status='queued'", (rid,))
    _msg(c, mid, "ai", "cancelled", "", {"task": r["task"]})
    c.commit()


# ---------- AI viết kịch bản ----------
SYSTEM = """Bạn là trợ lý soạn bài giảng dạng video ngắn cho giáo viên Việt Nam. Viết bằng tiếng Việt, dễ hiểu, hợp lứa tuổi học sinh.
Khi giáo viên nhờ viết hoặc sửa, trả lời MỘT lời nhắn ngắn (1-2 câu), rồi KỊCH BẢN ĐẦY ĐỦ trong khối ba dấu huyền với nhãn script. Định dạng kịch bản:
# Tiêu đề bài
## Tên cảnh
Hình: một biểu tượng emoji
- ý chính ngắn (tối đa 5 ý)
Lời: câu thuyết minh của cảnh
Từ 3 đến 8 cảnh: mở bài, nội dung chính, ví dụ, tóm tắt. Không viết mã, không chèn đường dẫn. Nếu chỉ hỏi han, trả lời bình thường, không cần kịch bản."""
FENCE = chr(96) * 3
SCRIPT_RE = re.compile(FENCE + r"script\s*\n(.*?)" + FENCE, re.S | re.I)


def _real():
    try:
        import llm
        return llm._real_model()
    except Exception:
        return None


def fake_script(topic, current):
    t = re.sub(r"\s+", " ", topic).strip()[:80] or "Bài mới"
    if current.strip():
        return "Mình đã thêm một cảnh tóm tắt vào cuối kịch bản (chế độ giả, chưa nối model).", current.rstrip() + "\n\n## Tóm tắt thêm\nHình: ✅\n- Nhắc lại ý chính\nLời: %s. Các em ghi nhớ nhé." % t
    s = ("# %s\n\n## Mở bài\nHình: 🎯\n- Hôm nay chúng ta học: %s\nLời: Chào các em, hôm nay chúng ta cùng tìm hiểu về %s.\n\n"
         "## Nội dung chính\nHình: 📘\n- Khái niệm cơ bản\n- Cách nhận biết\nLời: Đầu tiên, chúng ta làm quen với khái niệm cơ bản và cách nhận biết.\n\n"
         "## Ví dụ\nHình: 💡\n- Một ví dụ gần gũi\nLời: Cùng xem một ví dụ gần gũi để hiểu rõ hơn.\n\n"
         "## Tóm tắt\nHình: ✅\n- Nhớ lại ý chính\nLời: Chúng ta đã học xong %s. Các em ôn lại nhé.") % (t, t, t, t)
    return "Mình dựng kịch bản mẫu 4 cảnh (chế độ giả, chưa nối model). Bạn sửa ở cột giữa hoặc nhắn thêm để chỉnh.", s


def ai_script(history, current, message):
    """(lời nhắn, kịch bản mới hoặc None, mô tả lần gọi: chế độ giả hay tên model + token thật)."""
    call = _real()
    if call is None:
        text, script = fake_script(message, current)
        return text, script, "Chế độ giả: dựng từ khuôn, không gọi model."
    convo = "\n".join(("Giáo viên: " if m["role"] == "teacher" else "Trợ lý: ") + m["body"][:600] for m in history[-8:] if m["kind"] == "text")
    user = "Kịch bản hiện tại:\n%s\n\nHội thoại:\n%s\n\nGiáo viên: %s" % (current or "(chưa có)", convo, message)
    res = call(SYSTEM, user)
    reply = res["text"]
    info = "Model %s · %s token vào, %s token ra." % (res.get("model"), res.get("tokens_in"), res.get("tokens_out"))
    m = SCRIPT_RE.search(reply)
    if not m:
        return reply.strip(), None, info
    return (reply[:m.start()].strip() or "Mình đã cập nhật kịch bản."), m.group(1).strip(), info


# ---------- việc nền ----------
def _tool(c, mid, rid, name, inp):
    """Mở một thẻ công cụ trong chat (đang chạy). Trả (id tin nhắn, giờ bắt đầu); đóng bằng _tool_end."""
    c.execute("INSERT INTO motion_messages(motion_id,role,kind,body,meta,request_id,at) VALUES(?,?,?,?,?,?,?)",
              (mid, "ai", "tool", "", json.dumps({"tool": name, "status": "run", "input": inp}, ensure_ascii=False), rid, time.time()))
    c.commit()
    return c.execute("SELECT last_insert_rowid()").fetchone()[0], time.time()


def _tool_end(c, h, status, out):
    mid_, t0 = h
    r = c.execute("SELECT meta FROM motion_messages WHERE id=?", (mid_,)).fetchone()
    meta = json.loads(r["meta"])
    meta.update({"status": status, "output": out, "ms": int((time.time() - t0) * 1000)})
    c.execute("UPDATE motion_messages SET meta=? WHERE id=?", (json.dumps(meta, ensure_ascii=False), mid_))
    c.commit()


def _finish(c, rid, status, mid, kind=None, body="", meta=None):
    c.execute("UPDATE motion_requests SET status=? WHERE id=?", (status, rid))
    if kind:
        _msg(c, mid, "ai", kind, body, meta, rid)
    c.commit()


def _cancelled(c, r):
    if _running["cancel"]:
        _finish(c, r["id"], "cancelled", r["motion_id"], "cancelled", "", {"task": r["task"]})
        return True
    return False


def _run_script(c, r):
    mid = r["motion_id"]
    m = c.execute("SELECT script FROM motions WHERE id=?", (mid,)).fetchone()
    hist = [{"role": x["role"], "kind": x["kind"], "body": x["body"]}
            for x in c.execute("SELECT role,kind,body FROM motion_messages WHERE motion_id=? ORDER BY id", (mid,))][:-1]
    h = _tool(c, mid, r["id"], "read_script", "kịch bản hiện tại")
    cur_scenes = parse_script(m["script"])[1]
    _tool_end(c, h, "ok", ("%d cảnh, %d ký tự" % (len(cur_scenes), len(m["script"]))) if m["script"].strip() else "chưa có kịch bản")
    h = _tool(c, mid, r["id"], "call_model", "viết/sửa kịch bản theo: " + r["body"][:120])
    try:
        text, script, info = ai_script(hist, m["script"], r["body"])
    except Exception as e:
        sys.stderr.write("motion script: %r\n" % e)
        _tool_end(c, h, "bad", "Không gọi được model (%s)." % type(e).__name__)
        return _finish(c, r["id"], "failed", mid, "script_failed", FAIL["ai_failed"], {"code": "ai_failed"})
    _tool_end(c, h, "ok", info)
    if _cancelled(c, r):
        return
    if script and len(script) <= MAX_SCRIPT:
        h = _tool(c, mid, r["id"], "save_script", "%d ký tự" % len(script))
        c.execute("UPDATE motions SET script=?,updated=? WHERE id=?", (script, time.time(), mid))
        _tool_end(c, h, "ok", "%d cảnh: %s" % (len(parse_script(script)[1]), ", ".join(s["title"] for s in parse_script(script)[1])[:200]))
    _msg(c, mid, "ai", "text", text, rid=r["id"])
    if script and len(script) <= MAX_SCRIPT:
        _msg(c, mid, "ai", "script_changed", "%d cảnh" % len(parse_script(script)[1]), rid=r["id"])
    _finish(c, r["id"], "done", mid)


def _run_build(c, r):
    mid = r["motion_id"]
    m = c.execute("SELECT script,title FROM motions WHERE id=?", (mid,)).fetchone()

    def fail(code):
        _finish(c, r["id"], "failed", mid, "build_failed", FAIL[code], {"code": code})
    if not m["script"].strip():
        return fail("empty_script")
    h = _tool(c, mid, r["id"], "parse_script", "%d ký tự" % len(m["script"]))
    title, scenes = parse_script(m["script"])
    _tool_end(c, h, "ok" if scenes else "bad", "%d cảnh" % len(scenes))
    if not scenes:
        return fail("no_scenes")
    if len(scenes) > MAX_SCENES:
        return fail("too_many_scenes")
    c.execute("UPDATE motion_requests SET total=?,done=0 WHERE id=?", (len(scenes), r["id"]))
    c.commit()
    for i, sc in enumerate(scenes, 1):
        if _cancelled(c, r):
            return
        h = _tool(c, mid, r["id"], "build_scene", "cảnh %d/%d: %s" % (i, len(scenes), sc["title"]))
        time.sleep(float(os.environ.get("AILAB_MOTION_STEP_S", "0.4")))  # mỗi cảnh một nhịp: thấy tiến độ và huỷ kịp
        _tool_end(c, h, "ok", "%d ý chính, %d câu thuyết minh, %d giây" % (len(sc["points"]), len(sc["lines"]), scene_seconds(sc)))
        c.execute("UPDATE motion_requests SET done=? WHERE id=?", (i, r["id"]))
        c.commit()
    if _cancelled(c, r):
        return
    h = _tool(c, mid, r["id"], "render_html", "%d cảnh" % len(scenes))
    html = render(title or m["title"], scenes)
    _tool_end(c, h, "ok", "trang tự chứa %.1f KB, không gọi mạng" % (len(html.encode("utf-8")) / 1024))
    n = (c.execute("SELECT MAX(n) FROM motion_versions WHERE motion_id=?", (mid,)).fetchone()[0] or 0) + 1
    secs = sum(scene_seconds(s) for s in scenes)
    c.execute("INSERT INTO motion_versions(motion_id,n,html,scenes,seconds,created) VALUES(?,?,?,?,?,?)", (mid, n, html, len(scenes), secs, time.time()))
    c.execute("UPDATE motions SET updated=? WHERE id=?", (time.time(), mid))
    _finish(c, r["id"], "done", mid, "build_done", "", {"version": n, "scenes": len(scenes), "seconds": secs})


def work_once():
    """Chạy một việc đang chờ. Trả True nếu có việc. (Luồng nền gọi lặp; test gọi thẳng.)"""
    c = store.connect()
    try:
        r = c.execute("SELECT * FROM motion_requests WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
        if not r:
            return False
        _running["id"], _running["cancel"] = r["id"], False
        c.execute("UPDATE motion_requests SET status='running' WHERE id=?", (r["id"],))
        c.commit()
        try:
            (_run_script if r["task"] == "script" else _run_build)(c, r)
        except Exception as e:
            sys.stderr.write("motion worker: %r\n" % e)
            _finish(c, r["id"], "failed", r["motion_id"], "build_failed" if r["task"] == "build" else "script_failed", FAIL["build_failed"], {"code": "build_failed"})
        return True
    finally:
        _running["id"] = None
        c.close()


def _loop():
    while True:
        _wake.wait(2)
        _wake.clear()
        while work_once():
            pass


def start():
    c = store.connect()
    init(c)
    for r in c.execute("SELECT * FROM motion_requests WHERE status IN ('queued','running')").fetchall():
        c.execute("UPDATE motion_requests SET status='failed' WHERE id=?", (r["id"],))
        _msg(c, r["motion_id"], "ai", "build_failed" if r["task"] == "build" else "script_failed", FAIL["server_restarted"], {"code": "server_restarted"}, r["id"])
    c.commit()
    c.close()
    threading.Thread(target=_loop, daemon=True, name="motion-worker").start()


PLAYER = r"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
*{box-sizing:border-box}html,body{margin:0;height:100%;background:#000;color:#e8eef8;font:16px system-ui,sans-serif;overflow:hidden}
body{display:flex;align-items:center;justify-content:center}
.stage{position:relative;width:min(100vw,100vh*16/9);aspect-ratio:16/9;overflow:hidden;background:#0b1220;container-type:inline-size}
.bg{position:absolute;inset:0;background:radial-gradient(60% 70% at 12% 8%,rgba(56,189,248,.22),transparent 70%),radial-gradient(60% 70% at 92% 96%,rgba(251,113,133,.16),transparent 70%)}
.scene{position:absolute;inset:0;padding:6cqw 7cqw 11cqw;display:flex;flex-direction:column;justify-content:center;gap:2.2cqw;opacity:0;pointer-events:none;transition:opacity .5s}
.scene.on{opacity:1}
.icon{font-size:9cqw;line-height:1;transform:scale(.4);opacity:0;transition:transform .6s cubic-bezier(.2,1.4,.4,1),opacity .4s}
.on .icon{transform:none;opacity:1}
h1{margin:0;font:800 5.2cqw/1.15 system-ui,sans-serif;transform:translateY(2cqw);opacity:0;transition:transform .6s .15s,opacity .6s .15s}
.on h1{transform:none;opacity:1}
ul{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:1.4cqw}
li{font-size:2.8cqw;padding-left:3cqw;position:relative;opacity:0;transform:translateX(-3cqw);transition:transform .5s,opacity .5s}
li:before{content:"";position:absolute;left:0;top:1.1cqw;width:1.2cqw;height:1.2cqw;border-radius:50%;background:#38bdf8}
li.in{opacity:1;transform:none}
.cap{position:absolute;left:7cqw;right:7cqw;bottom:6.5cqw;font-size:2cqw;color:#cbd5e1;min-height:3cqw}
.bar{position:absolute;left:0;right:0;bottom:0;height:5cqw;display:flex;align-items:center;gap:1.4cqw;padding:0 2.4cqw;background:rgba(2,6,23,.72)}
.bar button{all:unset;cursor:pointer;width:3.4cqw;height:3.4cqw;display:grid;place-items:center;border-radius:50%;font-size:1.8cqw;background:rgba(255,255,255,.12)}
.bar button:hover,.bar button:focus-visible{background:rgba(255,255,255,.28);outline:2px solid #38bdf8}
.track{flex:1;height:.8cqw;border-radius:99px;background:rgba(255,255,255,.18);overflow:hidden;cursor:pointer}
.fill{height:100%;width:0;background:#38bdf8}
.time{font-size:1.5cqw;color:#94a3b8;min-width:9cqw;text-align:right}
</style></head><body><div class="stage" id="stage"><div class="bg"></div><div class="cap" id="cap" aria-live="polite"></div>
<div class="bar"><button id="prev" title="Cảnh trước" aria-label="Cảnh trước">⏮</button><button id="play" title="Phát / tạm dừng" aria-label="Phát hoặc tạm dừng">▶</button><button id="next" title="Cảnh sau" aria-label="Cảnh sau">⏭</button>
<div class="track" id="track" role="slider" aria-label="Tiến độ" tabindex="0"><div class="fill" id="fill"></div></div><span class="time" id="time"></span><button id="mute" title="Tiếng" aria-label="Bật tắt tiếng">🔊</button></div></div>
<script type="application/json" id="data">__DATA__</script>
<script>
(function(){
var D=JSON.parse(document.getElementById('data').textContent),S=D.scenes,stage=document.getElementById('stage');
var els=S.map(function(s){var d=document.createElement('div');d.className='scene';
  var ic=document.createElement('div');ic.className='icon';ic.textContent=s.icon||'';var h=document.createElement('h1');h.textContent=s.title;
  var ul=document.createElement('ul');s.points.forEach(function(p){var li=document.createElement('li');li.textContent=p;ul.appendChild(li);});
  if(s.icon)d.appendChild(ic);d.appendChild(h);d.appendChild(ul);stage.insertBefore(d,document.getElementById('cap'));return d;});
var starts=[],total=0;S.forEach(function(s){starts.push(total);total+=s.sec;});
var t=0,playing=false,cur=-1,last=0,muted=false,cap=document.getElementById('cap');
function fmt(x){x=Math.round(x);return Math.floor(x/60)+':'+('0'+x%60).slice(-2);}
function say(txt){try{speechSynthesis.cancel();if(muted||!txt||!playing)return;var u=new SpeechSynthesisUtterance(txt);u.lang='vi-VN';speechSynthesis.speak(u);}catch(e){}}
function show(i){if(i===cur)return;cur=i;els.forEach(function(e,k){e.classList.toggle('on',k===i);if(k!==i)e.querySelectorAll('li').forEach(function(l){l.classList.remove('in');});});
  cap.textContent=(S[i].lines||[]).join(' ');say(cap.textContent);}
function reveal(){var s=S[cur],local=t-starts[cur],lis=els[cur].querySelectorAll('li');lis.forEach(function(l,k){if(local>1+k*Math.max(.8,(s.sec-2)/(lis.length+1)))l.classList.add('in');});}
function frame(now){var dt=(now-last)/1000;last=now;if(playing){t+=dt;if(t>=total){t=total-.01;set(false);}}
  var i=0;while(i<S.length-1&&t>=starts[i+1])i++;show(i);reveal();
  document.getElementById('fill').style.width=(total?t/total*100:0)+'%';document.getElementById('time').textContent=fmt(t)+' / '+fmt(total);requestAnimationFrame(frame);}
function set(p){playing=p;document.getElementById('play').textContent=p?'⏸':'▶';if(p){if(t>=total-.05)t=0;say(cap.textContent);}else{try{speechSynthesis.cancel();}catch(e){}}}
function go(i){i=Math.max(0,Math.min(S.length-1,i));t=starts[i];cur=-1;}
document.getElementById('play').onclick=function(){set(!playing);};
document.getElementById('next').onclick=function(){go(cur+1);};
document.getElementById('prev').onclick=function(){go(cur-1);};
document.getElementById('mute').onclick=function(){muted=!muted;this.textContent=muted?'🔇':'🔊';if(muted){try{speechSynthesis.cancel();}catch(e){}}else say(cap.textContent);};
var tr=document.getElementById('track');tr.onclick=function(e){var r=tr.getBoundingClientRect();t=Math.max(0,Math.min(total-.01,(e.clientX-r.left)/r.width*total));cur=-1;};
document.addEventListener('keydown',function(e){if(e.key===' '){e.preventDefault();set(!playing);}else if(e.key==='ArrowRight')go(cur+1);else if(e.key==='ArrowLeft')go(cur-1);});
requestAnimationFrame(function(n){last=n;frame(n);});
})();
</script></body></html>"""
