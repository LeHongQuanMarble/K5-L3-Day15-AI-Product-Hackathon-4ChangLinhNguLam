"""Smoke test với LLM THẬT (T22). Không chạy trong pytest. Chạy: python scripts/smoke_real_llm.py"""

from __future__ import annotations

TOPIC = "Phân số - Toán lớp 4"
NUM_QUESTIONS = 5


async def run_smoke(topic: str, num_questions: int) -> dict:
    """Chạy pipeline không giao diện: intake -> N1b(topic) -> N2 -> N3 -> N4 <-> FIX.
    Trả {passed, fix_attempts, errors, html_path}."""
    raise NotImplementedError


def main() -> int:
    """In kết quả gọn; exit 0 nếu N4 pass."""
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
