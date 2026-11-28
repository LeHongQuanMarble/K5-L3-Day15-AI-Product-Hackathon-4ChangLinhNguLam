"""N6. Xuất file vào Folder -> MAIN tiếp nhận (ARCHITECTURE §6). (T16)"""

from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.core.models import Session, Version


def slugify(text: str) -> str:
    """Bỏ dấu tiếng Việt (đ->d), chữ thường, '-' nối, ≤ 50 ký tự; rỗng -> 'game'."""
    raise NotImplementedError


def build_manifest(session: Session, version: Version) -> dict:
    """session_id, title, game_type, subject, grade, question_source, num_questions,
    max_score, version, revisions, entry, exported_at."""
    raise NotImplementedError


def export(session: Session, version: Version, settings: Settings) -> Path:
    """version.test_passed is not True -> ValueError. Tạo output/<slug>_<id>/ gồm index.html,
    questions.json, manifest.json, screenshots/, rồi make_zip. Gán session.exported_to."""
    raise NotImplementedError


def make_zip(folder: Path) -> Path:
    """Nén folder thành <folder>/export.zip (không chứa chính file zip)."""
    raise NotImplementedError


async def notify_main(session: Session, folder: Path, settings: Settings) -> list[str]:
    """Ghi main_inbox/<id>.json; có MAIN_WEBHOOK_URL thì POST (httpx, timeout 10s, retry 2).
    Trả list cảnh báo (webhook lỗi KHÔNG raise)."""
    raise NotImplementedError
