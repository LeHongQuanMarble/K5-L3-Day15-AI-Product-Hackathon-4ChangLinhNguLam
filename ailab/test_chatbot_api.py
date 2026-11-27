"""I01 - kiểm thử API Trợ lý game (server thật ChatbotH, cổng 0, DB tạm, model giả). Spec: docs/chatbot/I01_SPEC.md §7."""
import http.cookiejar
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import atexit
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

_TMP = tempfile.mkdtemp(prefix="ailab_i01_")
os.environ["AILAB_DB"] = os.path.join(_TMP, "boot.db")  # chỉ để import store không chạm DB thật; mỗi lớp test dùng DB riêng
os.environ["MODEL_PROVIDER"] = "fake"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import chatbot_server  # noqa: E402
import store  # noqa: E402

atexit.register(shutil.rmtree, _TMP, True)
_N = 0
TURNS = ["Tạo game ôn toán", "lớp 2", "phép cộng có nhớ, 10 câu"]


class Client:
    def __init__(self, port):
        self.port = port
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def req(self, method, path, body=None):
        data = None
        hd = {}
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            hd["Content-Type"] = "application/json; charset=utf-8"
        r = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), data=data, headers=hd, method=method)
        try:
            resp = self.op.open(r, timeout=30)
            status, raw = resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            status, raw = e.code, e.read().decode("utf-8")
        try:
            js = json.loads(raw)
        except ValueError:
            js = None
        return status, js, raw


class ApiBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="ailab_i01c_")
        cls._old_db = store.DB_PATH
        cls._old_env = os.environ.get("AILAB_DB")
        cls._old_caller = chatbot_server.model_caller
        os.environ["AILAB_DB"] = os.path.join(cls.tmp, "t.db")
        store.DB_PATH = os.path.join(cls.tmp, "t.db")
        store.init("adminpass123")
        chatbot_server.ChatbotH.log_message = lambda *a: None
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), chatbot_server.ChatbotH)
        cls.port = cls.srv.server_address[1]
        cls.th = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.th.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        store.DB_PATH = cls._old_db
        chatbot_server.model_caller = cls._old_caller
        if cls._old_env is None:
            os.environ.pop("AILAB_DB", None)
        else:
            os.environ["AILAB_DB"] = cls._old_env
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def user(self):
        global _N
        _N += 1
        c = Client(self.port)
        s, js, _ = c.req("POST", "/api/register", {"username": "user%d_%d" % (os.getpid() % 1000, _N), "password": "password123"})
        self.assertEqual(s, 200, js)
        return c

    def db(self):
        return sqlite3.connect(store.DB_PATH)

    def counts(self):
        d = self.db()
        try:
            return tuple(d.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0] for t in ("players", "exams", "apps"))
        finally:
            d.close()

    def say(self, c, text, chat_id=None, **kw):
        b = {"text": text}
        if chat_id:
            b["chatId"] = chat_id
        b.update(kw)
        return c.req("POST", "/api/chat", b)

    def flow(self, c):
        """3 lượt tới phương án chờ xác nhận. Trả (chatId, proposal)."""
        cid = None
        js = None
        for i, t in enumerate(TURNS):
            s, js, _ = self.say(c, t, cid, expectedVersion=i if cid else None, requestId="flow-%d-%s" % (i, os.urandom(4).hex()))
            self.assertEqual(s, 200, js)
            cid = js["chatId"]
        return cid, js["reply"]["proposal"]

    def act(self, c, cid, action, pid, ver, **kw):
        b = {"action": action, "proposalId": pid, "version": ver}
        b.update(kw)
        return c.req("POST", "/api/chats/%s/actions" % cid, b)


class ChatbotApiTests(ApiBase):
    def test_i01_01_index_has_script(self):
        c = Client(self.port)
        s, _, raw = c.req("GET", "/")
        self.assertEqual(s, 200)
        self.assertIn('<script src="/chatbot.js"></script>', raw)
        self.assertEqual(c.req("GET", "/chatbot.js")[0], 200)

    def test_i01_02_unauth(self):
        s, _, _ = Client(self.port).req("POST", "/api/chat", {"text": "Tạo game ôn toán"})
        self.assertEqual(s, 401)

    def test_i01_03_three_turns(self):
        c = self.user()
        seq, cid = [], None
        for i, t in enumerate(TURNS):
            s, js, _ = self.say(c, t, cid, expectedVersion=i if cid else None)
            self.assertEqual(s, 200, js)
            cid = js["chatId"]
            seq.append((js["reply"]["status"], js["reply"]["stateVersion"], js["reply"]["missingFields"]))
        self.assertEqual([x[0] for x in seq], ["clarifying", "clarifying", "awaiting_confirmation"])
        self.assertEqual([x[1] for x in seq], [1, 2, 3])
        self.assertEqual(seq[1][2], ["topic"])

    def test_i01_04_reload(self):
        c = self.user()
        cid, prop = self.flow(c)
        s, js, _ = c.req("GET", "/api/chats/%s" % cid)
        self.assertEqual(s, 200)
        self.assertEqual(len(js["messages"]), 6)
        st = js["state"]
        self.assertEqual((st["status"], st["stateVersion"], st["proposal"]["version"]), ("awaiting_confirmation", 3, 1))
        self.assertEqual(st["proposal"]["proposalId"], prop["proposalId"])
        self.assertNotIn("role", st)

    def test_i01_05_other_user(self):
        a, b = self.user(), self.user()
        cid, prop = self.flow(a)
        self.assertEqual(b.req("GET", "/api/chats/%s" % cid)[0], 404)
        self.assertEqual(self.say(b, "lớp 3", cid)[0], 404)
        s, _, raw = self.act(b, cid, "confirm_plan", prop["proposalId"], 1)
        self.assertEqual(s, 404)
        self.assertNotIn("phép cộng", raw)
        # chat của A không đổi
        self.assertEqual(a.req("GET", "/api/chats/%s" % cid)[1]["state"]["status"], "awaiting_confirmation")

    def test_i01_06_duplicate_request_id(self):
        c = self.user()
        cid, _ = self.flow(c)
        body = {"chatId": cid, "text": "đổi thành 15 câu", "requestId": "dup-request-01", "expectedVersion": 3}
        s1, j1, _ = c.req("POST", "/api/chat", body)
        s2, j2, _ = c.req("POST", "/api/chat", body)
        self.assertEqual((s1, s2), (200, 200))
        self.assertEqual(j1, j2)
        g = c.req("GET", "/api/chats/%s" % cid)[1]
        self.assertEqual(len(g["messages"]), 8)
        self.assertEqual(g["state"]["stateVersion"], 4)

    def test_i01_07_stale_expected_version(self):
        c = self.user()
        cid, _ = self.flow(c)
        s, js, _ = self.say(c, "15 câu", cid, expectedVersion=1)
        self.assertEqual(s, 409)
        self.assertEqual(js["error"], "stale_version")
        self.assertEqual(js["stateVersion"], 3)
        self.assertEqual(len(c.req("GET", "/api/chats/%s" % cid)[1]["messages"]), 6)

    def test_i01_08_concurrent_same_version(self):
        c = self.user()
        cid, _ = self.flow(c)
        res = []
        orig = chatbot_server.workflow.process_turn
        # ép hai request cùng đọc v3 rồi mới lưu
        chatbot_server.workflow.process_turn = lambda *a, **k: (time.sleep(0.4), orig(*a, **k))[1]
        try:
            def go(t):
                res.append(self.say(c, t, cid, expectedVersion=3)[0])
            ts = [threading.Thread(target=go, args=(t,)) for t in ("12 câu", "20 câu")]
            [t.start() for t in ts]
            [t.join() for t in ts]
        finally:
            chatbot_server.workflow.process_turn = orig
        self.assertEqual(sorted(res), [200, 409])
        g = c.req("GET", "/api/chats/%s" % cid)[1]
        self.assertEqual(len(g["messages"]), 8)
        self.assertEqual(g["state"]["stateVersion"], 4)

    def test_i01_09_confirm_ok_old_badid(self):
        c = self.user()
        cid, prop = self.flow(c)
        pid = prop["proposalId"]
        self.assertEqual(self.act(c, cid, "confirm_plan", pid, 2)[0], 409)
        self.assertEqual(self.act(c, cid, "confirm_plan", "p-nope", 1)[0], 400)
        self.assertEqual(self.act(c, cid, "accept_result", pid, 1)[0], 400)
        s, js, _ = self.act(c, cid, "confirm_plan", pid, 1)
        self.assertEqual(s, 200, js)
        self.assertEqual(js["reply"]["proposal"]["status"], "confirmed")
        self.assertTrue(js["reply"]["simulated"])
        self.assertTrue(js["reply"]["proposal"]["simulated"])
        self.assertEqual(js["reply"]["proposal"]["scope"], "requirements")
        self.assertIn("chưa duyệt", js["reply"]["text"])

    def test_i01_10_cancel_then_confirm(self):
        c = self.user()
        cid, prop = self.flow(c)
        pid = prop["proposalId"]
        self.assertEqual(self.act(c, cid, "cancel_plan", pid, 1)[0], 200)
        s, js, _ = self.act(c, cid, "confirm_plan", pid, 1)
        self.assertEqual(s, 409)
        st = c.req("GET", "/api/chats/%s" % cid)[1]["state"]
        self.assertEqual((st["status"], st["proposal"]["status"]), ("needs_revision", "cancelled"))

    def test_i01_11_edit_after_confirm(self):
        c = self.user()
        cid, prop = self.flow(c)
        pid = prop["proposalId"]
        s, js, _ = self.act(c, cid, "confirm_plan", pid, 1)
        self.assertEqual(s, 200)
        s, js, _ = self.say(c, "lớp 3", cid, expectedVersion=js["reply"]["stateVersion"])
        self.assertEqual(s, 200, js)
        self.assertEqual(js["reply"]["proposal"]["version"], 2)
        self.assertEqual(js["reply"]["status"], "awaiting_confirmation")
        self.assertEqual(self.act(c, cid, "confirm_plan", pid, 1)[0], 409)

    def test_i01_12_legacy_chat(self):
        c = self.user()
        d = self.db()
        try:
            uid = d.execute("SELECT id FROM users ORDER BY id DESC LIMIT 1").fetchone()[0]
            legacy = [{"role": "user", "text": "game quiz"},
                      {"role": "bot", "text": "đây", "simulated": True, "model": "",
                       "proposal": {"html": "<html><script>x</script></html>", "name": "X", "description": "", "flags": [],
                                    "status": "pending", "playerId": None, "source": "fake"}}]
            lid = d.execute("INSERT INTO chats(user_id,title,messages,created) VALUES(?,?,?,?)",
                            (uid, "cũ", json.dumps(legacy), time.time())).lastrowid
            d.commit()
        finally:
            d.close()
        s, js, raw = c.req("GET", "/api/chats/%d" % lid)
        self.assertEqual(s, 200)
        self.assertNotIn("html", js["messages"][1]["proposal"])
        self.assertNotIn("<script", raw)
        self.assertEqual(js["state"]["stateVersion"], 0)
        s, rj, _ = c.req("POST", "/api/chats/%d/proposals/1/reject" % lid, {})
        self.assertEqual(s, 200)
        self.assertEqual(rj["status"], "rejected")
        s, js, _ = self.say(c, "Tạo game ôn toán", lid)
        self.assertEqual(s, 200, js)
        self.assertEqual(js["reply"]["stateVersion"], 1)

    def test_i01_13_ai_error(self):
        c = self.user()
        cid, _ = self.flow(c)
        before = c.req("GET", "/api/chats/%s" % cid)[1]

        def boom(system, user):
            raise RuntimeError("no net sk-ant-SECRETKEY12345")
        orig = chatbot_server.model_caller
        chatbot_server.model_caller = lambda: boom
        try:
            s, js, raw = self.say(c, "Tạo game ôn tiếng Việt", cid)
        finally:
            chatbot_server.model_caller = orig
        self.assertEqual(s, 200, js)
        self.assertEqual(js["reply"]["failure"]["code"], "model_unavailable")
        self.assertTrue(js["reply"]["error"])
        self.assertNotIn("SECRET", raw)
        after = c.req("GET", "/api/chats/%s" % cid)[1]
        self.assertEqual(after["state"]["stateVersion"], before["state"]["stateVersion"])
        self.assertEqual(len(after["messages"]), len(before["messages"]) + 2)
        self.assertTrue(after["messages"][-1].get("error"))

    def test_i01_14_15_no_html_no_assets(self):
        c = self.user()
        before = self.counts()
        raws = []
        cid, prop = self.flow(c)
        raws.append(c.req("GET", "/api/chats/%s" % cid)[2])
        for action in ("confirm_plan",):
            raws.append(self.act(c, cid, action, prop["proposalId"], 1)[2])
        s, js, raw = self.say(c, "đổi thành 15 câu", cid)
        raws.append(raw)
        nv = js["reply"]["proposal"]
        raws.append(self.act(c, cid, "cancel_plan", nv["proposalId"], nv["version"])[2])
        raws.append(c.req("GET", "/api/chats")[2])
        for r in raws:
            for bad in ("<script", "<html", "srcdoc"):
                self.assertNotIn(bad, r)
        self.assertEqual(self.counts(), before)

    def test_i01_16_old_routes(self):
        c = self.user()
        for p in ("/api/me", "/api/players", "/api/exams", "/api/chats"):
            self.assertEqual(c.req("GET", p)[0], 200, p)

    def test_extra_invalid_and_bad_request_id(self):
        c = self.user()
        s, js, _ = self.say(c, "x")
        self.assertEqual((s, js["error"]), (400, "invalid_input"))
        s, js, _ = self.say(c, "Tạo game ôn toán", requestId="a b")
        self.assertEqual(s, 400)

    def test_extra_duplicate_new_chat_no_extra_chat(self):
        c = self.user()
        n0 = len(c.req("GET", "/api/chats")[1]["chats"])
        b = {"text": "Tạo game ôn toán", "requestId": "new-chat-0001"}
        r1, r2 = c.req("POST", "/api/chat", b), c.req("POST", "/api/chat", b)
        self.assertEqual(r1[1], r2[1])
        self.assertEqual(len(c.req("GET", "/api/chats")[1]["chats"]), n0 + 1)


class ReplayRegressionTests(ApiBase):
    def fill_full(self, c):
        """Lấp chat tới đúng 60 tin (30 lượt). Trả (chatId, body lượt 30, response lượt 30)."""
        cid = None
        last = None
        for i in range(30):
            body = {"text": "Tạo game ôn toán" if i == 0 else "đổi thành %d câu" % (10 + i), "requestId": "fill-%02d-%s" % (i, os.urandom(3).hex())}
            if cid:
                body["chatId"] = cid
            s, js, _ = c.req("POST", "/api/chat", body)
            self.assertEqual(s, 200, (i, js))
            cid = js["chatId"]
            last = (body, js)
        self.assertEqual(len(c.req("GET", "/api/chats/%s" % cid)[1]["messages"]), 60)
        return cid, last[0], last[1]

    def pending(self):
        d = self.db()
        try:
            return d.execute("SELECT COUNT(*) FROM chat_requests WHERE status='pending'").fetchone()[0]
        finally:
            d.close()

    def test_a_replay_in_full_chat(self):
        c = self.user()
        cid, body, js = self.fill_full(c)
        s, js2, _ = c.req("POST", "/api/chat", body)
        self.assertEqual(s, 200, js2)
        self.assertEqual(js2, js)
        self.assertEqual(len(c.req("GET", "/api/chats/%s" % cid)[1]["messages"]), 60)

    def test_b_new_request_in_full_chat(self):
        c = self.user()
        cid, _, _ = self.fill_full(c)
        for extra in ({}, {"requestId": "full-new-req-01"}):
            s, js, _ = self.say(c, "thêm một tin", cid, **extra)
            self.assertEqual((s, js["error"]), (409, "chat_full"))
        self.assertEqual(self.pending(), 0)
        self.assertEqual(len(c.req("GET", "/api/chats/%s" % cid)[1]["messages"]), 60)

    def test_c_request_mismatch(self):
        c = self.user()
        cid, prop = self.flow(c)
        b = {"chatId": cid, "text": "đổi thành 15 câu", "requestId": "mismatch-0001", "expectedVersion": 3}
        self.assertEqual(c.req("POST", "/api/chat", b)[0], 200)
        n = len(c.req("GET", "/api/chats/%s" % cid)[1]["messages"])
        b2 = dict(b, text="đổi thành 20 câu")
        s, js, _ = c.req("POST", "/api/chat", b2)
        self.assertEqual((s, js["error"]), (409, "request_mismatch"))
        self.assertEqual(len(c.req("GET", "/api/chats/%s" % cid)[1]["messages"]), n)
        # actions
        cur = c.req("GET", "/api/chats/%s" % cid)[1]["state"]["proposal"]
        pid, ver = cur["proposalId"], cur["version"]
        self.assertEqual(self.act(c, cid, "confirm_plan", pid, ver, requestId="mismatch-act-1")[0], 200)
        s, js, _ = self.act(c, cid, "cancel_plan", pid, ver, requestId="mismatch-act-1")
        self.assertEqual((s, js["error"]), (409, "request_mismatch"))
        s, js, _ = self.act(c, cid, "confirm_plan", pid, ver + 1, requestId="mismatch-act-1")
        self.assertEqual((s, js["error"]), (409, "request_mismatch"))

    def test_d_other_user_same_request_id_with_chat(self):
        a, b = self.user(), self.user()
        cid, prop = self.flow(a)
        s, js, raw = a.req("POST", "/api/chat", {"chatId": cid, "text": "đổi thành 15 câu", "requestId": "shared-rid-0001", "expectedVersion": 3})
        self.assertEqual(s, 200)
        s, _, raw = b.req("POST", "/api/chat", {"chatId": cid, "text": "đổi thành 15 câu", "requestId": "shared-rid-0001", "expectedVersion": 3})
        self.assertEqual(s, 404)
        self.assertNotIn("15 câu", raw)
        self.assertNotIn("phiên bản", raw)
        s, _, raw = self.act(a, cid, "confirm_plan", js["reply"]["proposal"]["proposalId"], 2, requestId="shared-act-0001")
        self.assertEqual(s, 200)
        s, _, raw = self.act(b, cid, "confirm_plan", js["reply"]["proposal"]["proposalId"], 2, requestId="shared-act-0001")
        self.assertEqual(s, 404)
        self.assertNotIn("xác nhận", raw)
        self.assertNotIn("proposalId", raw)

    def test_e_other_user_same_request_id_new_chat(self):
        a, b = self.user(), self.user()
        body = {"text": "Tạo game ôn toán", "requestId": "shared-new-0001"}
        s1, j1, _ = a.req("POST", "/api/chat", body)
        s2, j2, _ = b.req("POST", "/api/chat", body)
        self.assertEqual((s1, s2), (200, 200))
        self.assertNotEqual(j1["chatId"], j2["chatId"])
        self.assertEqual(b.req("GET", "/api/chats/%s" % j2["chatId"])[0], 200)
        self.assertEqual(a.req("GET", "/api/chats/%s" % j2["chatId"])[0], 404)

    def test_f_replay_confirm(self):
        c = self.user()
        cid, prop = self.flow(c)
        kw = dict(requestId="confirm-rep-0001")
        s1, j1, _ = self.act(c, cid, "confirm_plan", prop["proposalId"], 1, **kw)
        v1 = c.req("GET", "/api/chats/%s" % cid)[1]
        s2, j2, _ = self.act(c, cid, "confirm_plan", prop["proposalId"], 1, **kw)
        v2 = c.req("GET", "/api/chats/%s" % cid)[1]
        self.assertEqual((s1, s2), (200, 200))
        self.assertEqual(j1, j2)
        self.assertEqual(v1["state"]["stateVersion"], v2["state"]["stateVersion"])
        self.assertEqual(len(v1["messages"]), len(v2["messages"]))

    def test_g_replay_new_chat_no_extra_chat(self):
        c = self.user()
        b = {"text": "Tạo game ôn toán", "requestId": "new-replay-0001"}
        n0 = len(c.req("GET", "/api/chats")[1]["chats"])
        c.req("POST", "/api/chat", b)
        c.req("POST", "/api/chat", b)
        self.assertEqual(len(c.req("GET", "/api/chats")[1]["chats"]), n0 + 1)


if __name__ == "__main__":
    unittest.main()
