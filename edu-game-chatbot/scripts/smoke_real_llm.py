"""Smoke test với LLM THẬT (T22). Không chạy trong pytest. Chạy: python scripts/smoke_real_llm.py"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TOPIC = "Phân số - Toán lớp 4"
NUM_QUESTIONS = 5


async def run_smoke(topic: str, num_questions: int) -> dict:
    """Chạy pipeline không giao diện: intake -> N1b(topic) -> 3 bước yêu cầu game -> N2 -> N3 -> N4 <-> FIX.
    Trả {passed, fix_attempts, errors, html_path}."""
    from app.chatbot import replies
    from app.chatbot.engine import ChatEngine
    from app.config import get_settings
    from app.core.events import EventBus
    from app.core.llm import OpenAILLM
    from app.core.models import State
    from app.core.store import SessionStore

    settings = get_settings()
    store = SessionStore(settings.sessions_dir)
    engine = ChatEngine(store, OpenAILLM(settings), EventBus(), settings)

    async def step(sid: str, text: str | None = None, action: str | None = None):
        await engine.handle(sid, text=text, action=action)
        await engine.wait_idle(sid)
        return store.get(sid)

    s = await engine.start_session()
    s = await step(s.id, text=f"Tạo game ôn tập {topic}")
    if s.state == State.AWAIT_SOURCE:
        s = await step(s.id, action=replies.BTN_SOURCE_TOPIC)
    if s.state == State.AWAIT_SOURCE_INPUT:
        s = await step(s.id, text=f"{topic}, {num_questions} câu")
    if s.state == State.AWAIT_QUESTION_APPROVAL:
        s = await step(s.id, action=replies.BTN_QB_APPROVE)
    if s.state == State.AWAIT_GAMEPLAY:
        s = await step(s.id, action=replies.BTN_GP_QUIZ)
    if s.state == State.AWAIT_CONTROLS:
        s = await step(s.id, action=replies.BTN_CTL_KEYBOARD)
    if s.state == State.AWAIT_VISUAL:
        s = await step(s.id, action=replies.BTN_VIS_CARTOON)
    if s.state != State.AWAIT_REVIEW or not s.versions:
        return {
            "passed": False,
            "fix_attempts": 0,
            "errors": [f"Dừng ở state {s.state}: {s.error or 'không có version'}"],
            "html_path": None,
        }
    v = s.versions[-1]
    result = {
        "passed": bool(v.test_passed),
        "fix_attempts": v.fix_attempts,
        "errors": list(v.test_errors),
        "html_path": str(Path(v.html_path)),
    }
    if v.test_passed:
        s = await step(s.id, action=replies.BTN_APPROVE)
        result["exported_to"] = s.exported_to
    return result


def main() -> int:
    """In kết quả gọn; exit 0 nếu N4 pass."""
    from app.config import get_settings

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not get_settings().openai_api_key:
        print(
            "Thiếu OPENAI_API_KEY. Đặt biến môi trường hoặc điền vào file .env, ví dụ:\n"
            "  OPENAI_API_KEY=sk-...\n"
            "rồi chạy lại: python scripts/smoke_real_llm.py"
        )
        return 2
    result = asyncio.run(run_smoke(TOPIC, NUM_QUESTIONS))
    print(f"Chủ đề: {TOPIC} ({NUM_QUESTIONS} câu)")
    print(f"Số lần sửa (FIX): {result['fix_attempts']}")
    print(f"N4: {'PASS' if result['passed'] else 'FAIL'}")
    for err in result["errors"]:
        print(f"  - {err}")
    print(f"HTML: {result['html_path']}")
    if result.get("exported_to"):
        print(f"Output: {result['exported_to']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
