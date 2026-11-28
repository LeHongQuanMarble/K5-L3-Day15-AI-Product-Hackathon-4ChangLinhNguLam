"""Train mô hình qua Teachable Machine: kiểm hàng đợi, kiểm tra đầu vào, tạo mô hình khi xong.
Dùng bộ chạy giả (không mạng, không Chrome); lần chạy thật đã kiểm riêng bằng tay."""
import base64
import io
import os
import sys
import tempfile
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import store  # noqa: E402
import train_jobs  # noqa: E402

JPEG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 64).decode()
URI = "data:image/jpeg;base64," + JPEG
FAKE_OK = [sys.executable, "-c", "import sys,json,os;json.dump({'url':'https://teachablemachine.withgoogle.com/models/FAKE1234/'},open(os.path.join(sys.argv[1],'result.json'),'w'))"]
FAKE_FAIL = [sys.executable, "-c", "import sys,json,os;json.dump({'error':'trainer_failed'},open(os.path.join(sys.argv[1],'result.json'),'w'))"]


def body(**kw):
    b = {"kind": "image", "name": "Giơ tay", "classes": [{"name": "Tay phai", "images": [URI] * 10}, {"name": "Tay trai", "images": [URI] * 10}]}
    b.update(kw)
    return b


class TestTrain(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = store.DB_PATH
        store.DB_PATH = os.path.join(self._tmp.name, "t.db")
        store.init(admin_password="test-admin-pw")
        self.c = store.connect()
        self.u = {"id": 1, "role": "admin", "username": "admin"}
        self._runner = train_jobs.RUNNER

    def tearDown(self):
        train_jobs.RUNNER = self._runner
        self.c.close()
        store.DB_PATH = self._orig
        self._tmp.cleanup()

    def bad(self, b, field):
        with self.assertRaises(store.Err) as cm:
            train_jobs.submit(self.c, self.u, b)
        self.assertEqual(cm.exception.code, field)

    def test_validation(self):
        self.bad(body(kind="audio"), "kind")
        self.bad(body(classes=[{"name": "A", "images": [URI] * 10}]), "classes")
        self.bad(body(classes=[{"name": "A", "images": [URI] * 10}, {"name": "a", "images": [URI] * 10}]), "classes")
        self.bad(body(classes=[{"name": "A", "images": [URI] * 10}, {"name": "B", "images": [URI] * 3}]), "images")
        self.bad(body(classes=[{"name": "A", "images": [URI] * 10}, {"name": "B", "images": ["data:image/gif;base64,AAAA"] * 10}]), "images")
        fake = "data:image/jpeg;base64," + base64.b64encode(b"not an image").decode()
        self.bad(body(classes=[{"name": "A", "images": [URI] * 10}, {"name": "B", "images": [fake] * 10}]), "images")
        self.bad(body(settings={"epochs": 0}), "epochs")
        self.bad(body(settings={"batch_size": 7}), "batch_size")
        self.bad(body(settings={"learning_rate": 5}), "learning_rate")

    def test_success_creates_model_and_removes_images(self):
        train_jobs.RUNNER = FAKE_OK
        jid = train_jobs.submit(self.c, self.u, body(settings={"epochs": 20}))
        self.assertEqual(train_jobs.get(self.c, self.u, jid)["status"], "queued")
        self.assertTrue(os.path.isdir(train_jobs._dir(jid)))
        train_jobs._run_one(jid)
        j = train_jobs.get(self.c, self.u, jid)
        self.assertEqual(j["status"], "done")
        m = self.c.execute("SELECT * FROM models WHERE id=?", (j["model_id"],)).fetchone()
        self.assertEqual((m["name"], m["kind"], m["url"], m["owner_id"], m["visibility"]), ("Giơ tay", "image", "https://teachablemachine.withgoogle.com/models/FAKE1234/", 1, "private"))
        self.assertEqual([o["key"] for o in __import__("json").loads(m["outputs"])], ["Tay phai", "Tay trai"])

    def test_failure_has_vietnamese_message_and_no_model(self):
        train_jobs.RUNNER = FAKE_FAIL
        before = self.c.execute("SELECT COUNT(*) FROM models").fetchone()[0]
        jid = train_jobs.submit(self.c, self.u, body())
        train_jobs._run_one(jid)
        j = train_jobs.get(self.c, self.u, jid)
        self.assertEqual((j["status"], j["errorCode"]), ("failed", "trainer_failed"))
        self.assertIn("Teachable Machine", j["error"])
        self.assertEqual(self.c.execute("SELECT COUNT(*) FROM models").fetchone()[0], before)

    def test_one_active_job_per_user_and_cancel(self):
        jid = train_jobs.submit(self.c, self.u, body())
        self.bad(body(), "busy")
        train_jobs.cancel(self.c, self.u, jid)
        self.assertEqual(train_jobs.get(self.c, self.u, jid)["errorCode"], "cancelled")
        self.assertFalse(os.path.exists(train_jobs._dir(jid)))
        train_jobs.submit(self.c, self.u, body())  # huỷ xong thì gửi việc mới được

    def test_other_user_cannot_see_job(self):
        jid = train_jobs.submit(self.c, self.u, body())
        other = {"id": 99, "role": "user", "username": "x"}
        with self.assertRaises(store.Err):
            train_jobs.get(self.c, other, jid)

    def test_restart_marks_running_jobs_failed(self):
        jid = train_jobs.submit(self.c, self.u, body())
        self.c.execute("UPDATE train_jobs SET status='running' WHERE id=?", (jid,))
        self.c.commit()
        from unittest import mock
        with mock.patch.object(train_jobs.threading, "Thread"):  # không để luồng hàng đợi sống sang test khác
            train_jobs.start()
        j = train_jobs.get(self.c, self.u, jid)
        self.assertEqual(j["errorCode"], "server_restarted")


if __name__ == "__main__":
    unittest.main()
