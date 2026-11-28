"""Kiểm phòng chơi: cd ailab && python -m unittest test_rooms"""
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["AILAB_DB"] = os.path.join(tempfile.mkdtemp(), "r.db")

import rooms  # noqa: E402
import store  # noqa: E402
from store import Err  # noqa: E402


class Rooms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._old_db = store.DB_PATH
        store.DB_PATH = os.path.join(tempfile.mkdtemp(), "rooms.db")  # DB riêng: không đụng khoá của các test khác
        store.init("pw-admin-1")
        cls.c = store.connect()
        now = time.time()
        pid = cls.c.execute("SELECT id FROM players LIMIT 1").fetchone()[0]
        cls.c.execute("INSERT INTO users(username,pw,role,created) VALUES('gv','x','user',?)", (now,))
        cls.c.execute("INSERT INTO users(username,pw,role,created) VALUES('khac','x','user',?)", (now,))
        cls.host = {"id": cls.c.execute("SELECT id FROM users WHERE username='gv'").fetchone()[0], "role": "user"}
        cls.other = {"id": cls.c.execute("SELECT id FROM users WHERE username='khac'").fetchone()[0], "role": "user"}
        cur = cls.c.execute("INSERT INTO apps(owner_id,name,player_id,share,created) VALUES(?,?,?,0,?)", (cls.host["id"], "Quiz riêng tư", pid, now))
        cls.app = cur.lastrowid
        cls.c.commit()

    @classmethod
    def tearDownClass(cls):
        cls.c.close()
        store.DB_PATH = cls._old_db

    def expect(self, code, fn, *a):
        with self.assertRaises(Err) as e:
            fn(*a)
        self.assertEqual(e.exception.code, code)

    def test_full_flow(self):
        c = self.c
        code = rooms.create(c, self.host, self.app)
        self.assertEqual(len(code), 6)
        a = rooms.join(c, code.lower(), "  An  ")
        b = rooms.join(c, code, "Bình")
        self.expect("name_taken", rooms.join, c, code, "an")
        st = rooms.state(c, code, None, a["token"])
        self.assertEqual((st["status"], st["role"], st["host"], len(st["members"])), ("lobby", "member", False, 2))
        self.assertNotIn("token", str(st["members"]))
        self.assertTrue(rooms.state(c, code, self.host, None)["host"])
        self.expect("not_playing", rooms.play_data, c, code, None, a["token"])
        self.assertIn("srcdoc", rooms.play_data(c, code, self.host, None))
        self.expect("not_member", rooms.play_data, c, code, None, "sai")
        self.expect("forbidden", rooms.start, c, code, self.other)
        self.expect("not_playing", rooms.submit, c, code, a["token"], 1, 2)
        rooms.start(c, code, self.host)
        self.assertIn("srcdoc", rooms.play_data(c, code, None, a["token"]))  # app không Chia sẻ vẫn chơi được trong phòng
        self.expect("score", rooms.submit, c, code, a["token"], 5, 3)
        self.expect("score", rooms.submit, c, code, a["token"], True, 3)
        self.expect("not_member", rooms.submit, c, code, "sai", 1, 2)
        rooms.submit(c, code, b["token"], 3, 5)
        rooms.submit(c, code, a["token"], 4, 5)
        rooms.submit(c, code, a["token"], 5, 5)  # lần hai bị bỏ qua
        ms = rooms.state(c, code, self.host, None)["members"]
        self.assertEqual([(m["name"], m["correct"], m["rank"]) for m in ms], [("An", 4, 1), ("Bình", 3, 2)])
        rooms.kick(c, code, self.host, b["member"]["id"])
        self.assertEqual(len(rooms.state(c, code, self.host, None)["members"]), 1)
        rooms.end(c, code, self.host)
        self.expect("ended", rooms.join, c, code, "Chi")

    def test_guards(self):
        self.expect("not_found", rooms.create, self.c, self.other, self.app)
        self.expect("no_room", rooms.state, self.c, "ABCDEF", None, None)
        self.expect("no_room", rooms.state, self.c, "abc", None, None)
        code = rooms.create(self.c, self.host, self.app)
        self.expect("name", rooms.join, self.c, code, "")
        self.expect("name", rooms.join, self.c, code, "x" * 21)

    def test_expiry(self):
        code = rooms.create(self.c, self.host, self.app)
        self.c.execute("UPDATE rooms SET created=? WHERE code=?", (time.time() - rooms.TTL - 5, code))
        self.c.commit()
        self.assertEqual(rooms.state(self.c, code, None, None)["status"], "ended")


if __name__ == "__main__":
    unittest.main()
