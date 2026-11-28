"""Xuất models / players / apps / exams từ DB ra JSON để đưa lên git (data/ bị .gitignore vì DB chứa tài khoản).

Chạy: python3 ailab/export_data.py [file_json]      (mặc định ailab/seed_data.json)
Không xuất: users, mật khẩu, phiên đăng nhập, phòng, motion, job train. Bỏ cột chủ sở hữu và thời gian.
"""
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("AILAB_DB") or os.path.join(HERE, "data", "ailab.db")
TABLES = {"models": "id", "players": "id", "exams": "id", "apps": "id"}
DROP = {"owner_id", "created", "updated", "note"}


def main(path=None):
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    out = {}
    for t, key in TABLES.items():
        rows = []
        for r in c.execute("SELECT * FROM %s ORDER BY %s" % (t, key)):
            d = {k: r[k] for k in r.keys() if k not in DROP}
            for k in ("outputs", "manifest", "mapping"):  # JSON lưu dạng chuỗi → xuất dạng đối tượng cho dễ đọc
                if k in d and isinstance(d[k], str):
                    try:
                        d[k] = json.loads(d[k])
                    except ValueError:
                        pass
            rows.append(d)
        out[t] = rows
    target = path or os.path.join(HERE, "seed_data.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print("Xuất %s: %s" % (target, ", ".join("%d %s" % (len(v), k) for k, v in out.items())))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
