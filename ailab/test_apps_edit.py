"""Sửa ứng dụng (PUT /api/apps/<id>) có gắn ô trình chơi với lớp của mô hình: trước đây lỗi 500 vì lưu dict vào SQLite."""
import json
import os
import socket
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["AILAB_DB"] = os.path.join(tempfile.mkdtemp(), "e.db")
os.environ["MODEL_PROVIDER"] = "fake"

import llm  # noqa: E402
import server  # noqa: E402
import store  # noqa: E402


class EditApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        store.init("pw-test-12345")
        s = socket.socket(); s.bind(("127.0.0.1", 0)); cls.port = s.getsockname()[1]; s.close()
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", cls.port), server.H)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        c = store.connect()
        cls.token = store.demo_login(c, "user") if hasattr(store, "demo_login") else None
        c.close()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def call(self, method, path, body=None):
        req = urllib.request.Request("http://127.0.0.1:%d/api/%s" % (self.port, path), method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json", "Cookie": "%s=%s" % (server.COOKIE, self.token)})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_put_app_with_mapping(self):
        os.environ["AILAB_DEMO"] = "1"
        c = store.connect()
        model_id = c.execute("INSERT INTO models(owner_id,name,description,kind,url,outputs,visibility,created) VALUES(?,?,?,?,?,?,?,?)",
                             (store.user_of(c, self.token)["id"], "M", "", "pose", "https://teachablemachine.withgoogle.com/models/x/",
                              json.dumps([{"key": k, "role": "action"} for k in "abcd"]), "private", 0)).lastrowid
        quiz_id = store.add_player(c, store.user_of(c, self.token), llm.QUIZ_TEMPLATE.replace("__TITLE__", "Quiz test"))  # trình chơi riêng: không phụ thuộc DB dùng chung
        c.commit()
        c.close()
        mapping = {"A": "a", "B": "b", "C": "c", "D": "d"}
        body = {"name": "App thử", "playerId": quiz_id, "modelId": model_id, "mapping": mapping, "content": "1+1=? | 1 | 2 | =B"}
        st, d = self.call("POST", "apps", body)
        self.assertEqual(st, 201, d)
        aid = d["id"]
        body["mapping"] = {"A": "d", "B": "c", "C": "b", "D": "a"}  # gắn lại ô với lớp khác
        st, d = self.call("PUT", "apps/%d" % aid, body)
        self.assertEqual(st, 200, d)
        st, d = self.call("GET", "apps/%d" % aid)
        self.assertEqual(d["app"]["mapping"], body["mapping"])


if __name__ == "__main__":
    unittest.main()
