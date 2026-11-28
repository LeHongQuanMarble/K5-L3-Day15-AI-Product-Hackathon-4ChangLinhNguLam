"""Hàng đợi train mô hình qua Teachable Machine (tái sử dụng ý của learning/train-worker).

Người dùng tải ảnh và chia lớp ngay trên trang AI Lab; việc HUẤN LUYỆN diễn ra ở trang train của Teachable Machine, do một Chrome không
giao diện điều khiển (ailab/train_worker, cần Playwright: xem ailab/train_worker/requirements.txt). Server chỉ lưu ảnh tạm, chạy từng
việc một trong tiến trình con, rồi tạo mô hình (đường dẫn Teachable Machine + các lớp) cho người đã gửi. Ảnh bị xoá ngay khi xong.
"""
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

import store

HERE = os.path.dirname(os.path.abspath(__file__))
KINDS = ("image", "pose")
MIN_PER_CLASS, MAX_PER_CLASS = 10, 300
MIN_CLASSES, MAX_CLASSES = 2, 8
MAX_IMAGE_BYTES = 400 * 1024
BATCHES = (16, 32, 64, 128, 256, 512)
LRATES = (0.00001, 0.0001, 0.001, 0.003, 0.01)
JOB_TIMEOUT_S = 420
EXT = {b"\xff\xd8\xff": ".jpg", b"\x89PNG\r\n\x1a\n": ".png"}
DATA_URI = re.compile(r"^data:image/(?:jpeg|png);base64,([A-Za-z0-9+/=]+)$")
MESSAGES = {
    "trainer_failed": "Teachable Machine không train xong trong thời gian cho phép. Thử lại, hoặc dùng ít ảnh hơn.",
    "trainer_unavailable": "Máy chủ chưa cài bộ train (Playwright và Chrome). Xem ailab/train_worker/requirements.txt.",
    "server_restarted": "Máy chủ khởi động lại khi đang train. Gửi lại việc này.",
    "cancelled": "Đã huỷ.",
    "timeout": "Quá thời gian train. Thử lại với ít ảnh hơn.",
}
RUNNER = [sys.executable, "-m", "train_worker.runner"]  # tests thay bằng bộ chạy giả (không gọi Teachable Machine thật)
_wake = threading.Event()
_running = {"id": None, "proc": None}
_lock = threading.Lock()


def _dir(jid):
    return os.path.join(os.path.dirname(store.DB_PATH), "train", str(jid))


def _clean(body):
    kind = body.get("kind")
    if kind not in KINDS:
        raise store.Err(400, "kind", "Loại mô hình train được: image hoặc pose.")
    name = store._s(body.get("name"), 1, 80, "name", "Tên mô hình")
    desc = body.get("description") or ""
    if not isinstance(desc, str) or len(desc) > 300:
        raise store.Err(400, "description", "Mô tả tối đa 300 ký tự.")
    classes = body.get("classes")
    if not isinstance(classes, list) or not (MIN_CLASSES <= len(classes) <= MAX_CLASSES):
        raise store.Err(400, "classes", "Cần %d–%d lớp." % (MIN_CLASSES, MAX_CLASSES))
    out, seen = [], set()
    for c in classes:
        cname = (c.get("name") if isinstance(c, dict) else None)
        imgs = (c.get("images") if isinstance(c, dict) else None)
        if not isinstance(cname, str) or not (1 <= len(cname.strip()) <= 60) or cname.strip().lower() in seen:
            raise store.Err(400, "classes", "Mỗi lớp cần tên 1–60 ký tự, không trùng nhau.")
        if not isinstance(imgs, list) or not (MIN_PER_CLASS <= len(imgs) <= MAX_PER_CLASS):
            raise store.Err(400, "images", "Lớp “%s” cần %d–%d ảnh." % (cname.strip(), MIN_PER_CLASS, MAX_PER_CLASS))
        seen.add(cname.strip().lower())
        files = []
        for u in imgs:
            m = DATA_URI.match(u) if isinstance(u, str) else None
            if not m:
                raise store.Err(400, "images", "Ảnh phải là JPEG hoặc PNG.")
            raw = base64.b64decode(m.group(1))
            ext = next((e for magic, e in EXT.items() if raw.startswith(magic)), None)
            if not ext or len(raw) > MAX_IMAGE_BYTES:
                raise store.Err(400, "images", "Mỗi ảnh là JPEG/PNG thật, tối đa %d KB (trình duyệt tự thu nhỏ)." % (MAX_IMAGE_BYTES // 1024))
            files.append((raw, ext))
        out.append((cname.strip(), files))
    settings = {}
    s = body.get("settings") or {}
    if "epochs" in s and s["epochs"] is not None:
        if not isinstance(s["epochs"], int) or isinstance(s["epochs"], bool) or not 1 <= s["epochs"] <= 500:
            raise store.Err(400, "epochs", "Epochs là số nguyên 1–500.")
        settings["epochs"] = s["epochs"]
    if s.get("batch_size") is not None:
        if s["batch_size"] not in BATCHES:
            raise store.Err(400, "batch_size", "Batch size: %s." % ", ".join(map(str, BATCHES)))
        settings["batch_size"] = s["batch_size"]
    if s.get("learning_rate") is not None:
        if s["learning_rate"] not in LRATES:
            raise store.Err(400, "learning_rate", "Learning rate: %s." % ", ".join(map(str, LRATES)))
        settings["learning_rate"] = s["learning_rate"]
    return kind, name, desc, out, settings


def submit(c, user, body):
    kind, name, desc, classes, settings = _clean(body)
    busy = c.execute("SELECT COUNT(*) FROM train_jobs WHERE owner_id=? AND status IN ('queued','running')", (user["id"],)).fetchone()[0]
    if busy >= 1:
        raise store.Err(409, "busy", "Bạn đang có một việc train chưa xong. Đợi xong hoặc huỷ nó trước.")
    if c.execute("SELECT COUNT(*) FROM models WHERE owner_id=?", (user["id"],)).fetchone()[0] >= 100:
        raise store.Err(409, "storage_full", "Mỗi tài khoản có tối đa 100 mô hình.")
    cur = c.execute("INSERT INTO train_jobs(owner_id,kind,name,description,classes,settings,status,created) VALUES(?,?,?,?,?,?, 'queued', ?)",
                    (user["id"], kind, name, desc, json.dumps([n for n, _ in classes], ensure_ascii=False), json.dumps(settings), time.time()))
    jid = cur.lastrowid
    base = _dir(jid)
    try:
        spec = {}
        for i, (cname, files) in enumerate(classes):
            os.makedirs(os.path.join(base, str(i)), exist_ok=True)
            paths = []
            for n, (raw, ext) in enumerate(files):
                p = os.path.join(base, str(i), "%d%s" % (n, ext))
                with open(p, "wb") as f:
                    f.write(raw)
                paths.append(p)
            spec[cname] = paths
        with open(os.path.join(base, "job.json"), "w", encoding="utf-8") as f:
            json.dump({"kind": kind, "name": name, "classes": spec, "settings": settings}, f, ensure_ascii=False)
    except OSError:
        shutil.rmtree(base, ignore_errors=True)
        c.execute("DELETE FROM train_jobs WHERE id=?", (jid,))
        c.commit()
        raise store.Err(500, "disk", "Không lưu được ảnh tạm.")
    c.commit()
    _wake.set()
    return jid


def row(r):
    d = {k: r[k] for k in ("id", "kind", "name", "status", "url", "model_id", "created", "started", "finished")}
    d["classes"] = json.loads(r["classes"])
    d["error"] = MESSAGES.get(r["error"], r["error"]) if r["error"] else None
    d["errorCode"] = r["error"]
    d["queued"] = 0
    return d


def get(c, user, jid):
    r = c.execute("SELECT * FROM train_jobs WHERE id=?", (jid,)).fetchone()
    if not r or not (r["owner_id"] == user["id"] or user["role"] == "admin"):
        raise store.Err(404, "not_found", "Không thấy việc train này.")
    d = row(r)
    if r["status"] == "queued":
        d["queued"] = c.execute("SELECT COUNT(*) FROM train_jobs WHERE status IN ('queued','running') AND id<?", (jid,)).fetchone()[0]
    return d


def mine(c, user):
    return [row(r) for r in c.execute("SELECT * FROM train_jobs WHERE owner_id=? ORDER BY id DESC LIMIT 20", (user["id"],)).fetchall()]


def cancel(c, user, jid):
    r = c.execute("SELECT * FROM train_jobs WHERE id=?", (jid,)).fetchone()
    if not r or not (r["owner_id"] == user["id"] or user["role"] == "admin"):
        raise store.Err(404, "not_found", "Không thấy việc train này.")
    if r["status"] not in ("queued", "running"):
        raise store.Err(409, "finished", "Việc này đã xong.")
    c.execute("UPDATE train_jobs SET status='failed', error='cancelled', finished=? WHERE id=? AND status IN ('queued','running')", (time.time(), jid))
    c.commit()
    with _lock:
        if _running["id"] == jid and _running["proc"] is not None:
            try:
                _running["proc"].kill()
            except OSError:
                pass
    shutil.rmtree(_dir(jid), ignore_errors=True)


def _finish(jid, status, error=None, url=None, model_id=None):
    c = store.connect()
    try:
        # đã huỷ trong lúc chạy thì giữ nguyên trạng thái huỷ
        c.execute("UPDATE train_jobs SET status=?, error=?, url=?, model_id=?, finished=? WHERE id=? AND error IS NOT 'cancelled'",
                  (status, error, url, model_id, time.time(), jid))
        c.commit()
    finally:
        c.close()


def _make_model(jid):
    c = store.connect()
    try:
        r = c.execute("SELECT * FROM train_jobs WHERE id=?", (jid,)).fetchone()
        outs = [{"key": n, "role": "action"} for n in json.loads(r["classes"])]
        cur = c.execute("INSERT INTO models(owner_id,name,description,kind,url,outputs,visibility,created) VALUES(?,?,?,?,?,?, 'private',?)",
                        (r["owner_id"], r["name"], r["description"], r["kind"], r["url"], json.dumps(outs, ensure_ascii=False), time.time()))
        c.commit()
        return cur.lastrowid
    finally:
        c.close()


def _run_one(jid):
    base = _dir(jid)
    if not os.path.exists(os.path.join(base, "job.json")):
        return _finish(jid, "failed", "trainer_failed")
    cmd = [*RUNNER, base]
    try:
        proc = subprocess.Popen(cmd, cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return _finish(jid, "failed", "trainer_unavailable")
    with _lock:
        _running.update(id=jid, proc=proc)
    try:
        proc.wait(timeout=JOB_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return _finish(jid, "failed", "timeout")
    finally:
        with _lock:
            _running.update(id=None, proc=None)
    try:
        with open(os.path.join(base, "result.json"), encoding="utf-8") as f:
            res = json.load(f)
    except (OSError, ValueError):
        return _finish(jid, "failed", "trainer_failed")
    if res.get("url"):
        c = store.connect()
        try:
            c.execute("UPDATE train_jobs SET url=? WHERE id=?", (res["url"], jid))
            c.commit()
        finally:
            c.close()
        return _finish(jid, "done", None, res["url"], _make_model(jid))
    return _finish(jid, "failed", res.get("error") or "trainer_failed")


def _loop():
    while True:
        _wake.wait(5)
        _wake.clear()
        while True:
            c = store.connect()
            try:
                r = c.execute("SELECT id FROM train_jobs WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
                if r:
                    c.execute("UPDATE train_jobs SET status='running', started=? WHERE id=? AND status='queued'", (time.time(), r["id"]))
                    c.commit()
            finally:
                c.close()
            if not r:
                break
            try:
                _run_one(r["id"])
            except Exception:  # một việc hỏng không được làm chết hàng đợi
                _finish(r["id"], "failed", "trainer_failed")
            shutil.rmtree(_dir(r["id"]), ignore_errors=True)


def start():
    """Gọi một lần khi server chạy: việc đang chạy dở trước khi tắt máy thì báo hỏng; việc đang chờ vẫn được làm tiếp."""
    c = store.connect()
    try:
        for r in c.execute("SELECT id FROM train_jobs WHERE status='running'").fetchall():
            c.execute("UPDATE train_jobs SET status='failed', error='server_restarted', finished=? WHERE id=?", (time.time(), r["id"]))
            shutil.rmtree(_dir(r["id"]), ignore_errors=True)
        c.commit()
    finally:
        c.close()
    threading.Thread(target=_loop, name="train-queue", daemon=True).start()
    _wake.set()
