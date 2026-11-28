"""Tiến trình con: đọc job.json trong thư mục việc, train qua Teachable Machine, ghi result.json ({"url"} hoặc {"error"}).
Chạy: python -m train_worker.runner <thư mục việc>. Không in tên lớp hay đường dẫn ra log."""
import json
import os
import sys
from pathlib import Path


def main(argv):
    base = Path(argv[1])
    out = base / "result.json"
    try:
        job = json.loads((base / "job.json").read_text(encoding="utf-8"))
        classes = {name: [Path(p) for p in paths] for name, paths in job["classes"].items()}
        try:
            from .tm_trainer import TmBrowserTrainer
        except ImportError:  # chưa cài Playwright
            out.write_text(json.dumps({"error": "trainer_unavailable"}), encoding="utf-8")
            return 3
        url = TmBrowserTrainer().train(job["name"], classes, settings=job.get("settings") or None, kind=job["kind"])
        out.write_text(json.dumps({"url": url}), encoding="utf-8")
        return 0
    except Exception as e:  # noqa: BLE001
        code = getattr(e, "code", "trainer_failed")
        out.write_text(json.dumps({"error": code if code in ("trainer_failed", "trainer_unavailable") else "trainer_failed"}), encoding="utf-8")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
