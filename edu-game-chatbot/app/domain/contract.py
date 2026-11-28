"""Game contract (docs/GAME_CONTRACT.md). (T04)"""

from __future__ import annotations

REQUIRED_TESTIDS = ("start-button", "question", "score", "result-screen", "final-score", "restart-button")
MAX_HTML_BYTES = 2_000_000
QUESTION_BANK_ID = "question-bank"

# Tóm tắt GAME_CONTRACT §1–4 để chèn vào prompt codegen/fix qua {{CONTRACT}}
CONTRACT_TEXT = "TODO"


def static_check(html: str) -> list[str]:
    """Kiểm C1–C6 + đủ testid + có window.__GAME__. Trả về list lỗi tiếng Việt; [] = đạt."""
    raise NotImplementedError


def find_external_resources(html: str) -> list[str]:
    """Các thẻ script/link/img/iframe/audio/video/source trỏ tới http(s):// hoặc //."""
    raise NotImplementedError


def find_forbidden_calls(html: str) -> list[str]:
    """alert/confirm/prompt/fetch/XMLHttpRequest/WebSocket (không bắt nhầm obj.alert, myalert)."""
    raise NotImplementedError


def inject_bank(html: str, bank: dict) -> str:
    """Thay nội dung thẻ #question-bank bằng JSON bank (escape '</'); chưa có thẻ thì chèn đầu <head>."""
    raise NotImplementedError
