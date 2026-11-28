"""Ứng dụng chưa có ảnh riêng thì mặc định lấy ảnh của mô hình nó dùng."""
import os
import secrets
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["AILAB_DB"] = os.path.join(tempfile.mkdtemp(), "i.db")

import store  # noqa: E402

IMG_A = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
IMG_B = "data:image/jpeg;base64,/9j/4AAQSkZJRg=="


class AppImage(unittest.TestCase):
    def test_default_from_model_and_own_image_wins(self):
        store.init("pw-test-12345")
        c = store.connect()
        name = "gv_" + secrets.token_hex(3)
        store.register(c, name, "matkhau123")
        u = dict(c.execute("SELECT * FROM users WHERE username=?", (name,)).fetchone())
        now = time.time()
        mid = c.execute("INSERT INTO models(owner_id,name,description,kind,url,outputs,visibility,image,created) VALUES(?,?,?,?,?,?,?,?,?)",
                        (u["id"], "M", "", "pose", "https://teachablemachine.withgoogle.com/models/x/", "[]", "private", IMG_A, now)).lastrowid
        pid = c.execute("SELECT id FROM players ORDER BY id LIMIT 1").fetchone()[0]

        def mk(image, model_id):
            return c.execute("INSERT INTO apps(owner_id,name,description,player_id,model_id,mapping,content,image,created) VALUES(?,?,?,?,?,?,?,?,?)",
                             (u["id"], "A", "", pid, model_id, "{}", "", image, now)).lastrowid
        mid2 = c.execute("INSERT INTO models(owner_id,name,description,kind,url,outputs,visibility,created) VALUES(?,?,?,?,?,?,?,?)",
                         (u["id"], "M2", "", "audio", "https://teachablemachine.withgoogle.com/models/y/", "[]", "private", now)).lastrowid
        for aid, want, flag in ((mk("", mid), IMG_A, True), (mk(IMG_B, mid), IMG_B, False), (mk("", None), "", False),
                                (mk("", mid2), "/kindart/audio-spectrogram.png", True)):
            d = store.app_row(c.execute("SELECT * FROM apps WHERE id=?", (aid,)).fetchone(), u, c)
            self.assertEqual((d["image"], d["image_from_model"]), (want, flag))
        c.close()


if __name__ == "__main__":
    unittest.main()
