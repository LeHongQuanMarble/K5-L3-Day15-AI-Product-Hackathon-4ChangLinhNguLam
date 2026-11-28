"""Game mẫu có sẵn (ailab/seed_players): đủ 5 game, không nhân đôi khi khởi động lại."""
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import store  # noqa: E402

NAMES = {"Cầu Lông 3D", "Sút Penalty 3D", "Giải cứu thế giới", "Chim Bay Nói", "Tết 2027: Dê Vàng và cổng băng"}


class TestSeedPlayers(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = store.DB_PATH
        store.DB_PATH = os.path.join(self._tmp.name, "s.db")

    def tearDown(self):
        store.DB_PATH = self._orig
        self._tmp.cleanup()

    def rows(self):
        c = store.connect()
        r = c.execute("SELECT name,status,visibility,owner_id,image FROM players").fetchall()
        c.close()
        return r

    def test_all_samples_seeded_approved_public_with_image(self):
        store.init(admin_password="test-admin-pw")
        rows = {r["name"]: r for r in self.rows()}
        self.assertTrue(NAMES <= set(rows), NAMES - set(rows))
        self.assertEqual(len(rows), 7)  # 2 mẫu gốc + 5 game
        for n in NAMES:
            self.assertEqual((rows[n]["status"], rows[n]["visibility"], rows[n]["owner_id"]), ("approved", "public", None))
            self.assertTrue(rows[n]["image"].startswith("data:image/"), n)

    def test_showcase_games_not_in_ai_catalog(self):
        import composer
        store.init(admin_password="test-admin-pw")
        names = {p["name"] for p in composer.catalog_snapshot()["players"]}
        self.assertEqual(names, {"Quiz ABCD bằng cử chỉ", "Vòng quay chọn tên"})

    def test_legacy_game_image_on_exam_is_replaced_but_user_image_kept(self):
        store.init(admin_password="test-admin-pw")
        c = store.connect()
        n1, n2 = "Toán 12: Đạo hàm và khảo sát hàm số", "Toán 12: Nguyên hàm và tích phân"
        c.execute("UPDATE exams SET image=? WHERE name=?", (store._data_uri("penalty.jpg"), n1))
        c.execute("UPDATE exams SET image=? WHERE name=?", ("data:image/png;base64,AAAA", n2))
        c.commit(); c.close()
        store.init()
        c = store.connect()
        img = {r["name"]: r["image"] for r in c.execute("SELECT name,image FROM exams")}
        c.close()
        self.assertEqual(img[n1], store._data_uri("exam-1.jpg"))
        self.assertEqual(img[n2], "data:image/png;base64,AAAA")

    def test_restart_does_not_duplicate(self):
        store.init(admin_password="test-admin-pw")
        store.init()
        self.assertEqual(len(self.rows()), 7)


if __name__ == "__main__":
    unittest.main()
