"""N6. Xuất file vào Folder -> MAIN tiếp nhận (ARCHITECTURE §6). (T16)"""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
import zipfile
from pathlib import Path

import httpx

from app.config import Settings
from app.core.models import Session, Version, utcnow
from app.domain.questions import max_score


def slugify(text: str) -> str:
    """Bỏ dấu tiếng Việt (đ->d), chữ thường, '-' nối, ≤ 50 ký tự; rỗng -> 'game'."""
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:50].strip("-")
    return text or "game"


def build_manifest(session: Session, version: Version) -> dict:
    """session_id, title, game_type, subject, grade, question_source, num_questions,
    max_score, version, revisions, entry, exported_at."""
    design = version.design or session.design or {}
    bank = session.question_bank or {}
    return {
        "session_id": session.id,
        "title": design.get("title") or session.topic or session.request or "game",
        "game_type": design.get("game_type"),
        "subject": session.subject,
        "grade": session.grade,
        "question_source": session.source.value if session.source else None,
        "num_questions": len(bank.get("questions", [])) or session.num_questions,
        "max_score": max_score(bank),
        "version": version.number,
        "revisions": list(session.revisions),
        "entry": "index.html",
        "exported_at": utcnow().isoformat(),
    }


def export(session: Session, version: Version, settings: Settings) -> Path:
    """version.test_passed is not True -> ValueError. Tạo output/<slug>_<id>/ gồm index.html,
    questions.json, manifest.json, screenshots/, rồi make_zip. Gán session.exported_to."""
    if version.test_passed is not True:
        raise ValueError("Phiên bản chưa qua kiểm thử, không thể xuất.")
    manifest = build_manifest(session, version)
    folder = Path(settings.output_dir) / f"{slugify(manifest['title'])}_{session.id}"
    if folder.exists():
        shutil.rmtree(folder)
    shots = folder / "screenshots"
    shots.mkdir(parents=True)
    shutil.copyfile(version.html_path, folder / "index.html")
    (folder / "questions.json").write_text(
        json.dumps(session.question_bank, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for shot in version.screenshots:
        src = Path(shot)
        if src.is_file():
            shutil.copyfile(src, shots / src.name)
    (folder / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    make_zip(folder)
    session.exported_to = str(folder.resolve())
    return folder


def make_zip(folder: Path) -> Path:
    """Nén folder thành <folder>/export.zip (không chứa chính file zip)."""
    folder = Path(folder)
    target = folder / "export.zip"
    target.unlink(missing_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path != target:
                zf.write(path, path.relative_to(folder).as_posix())
    return target


def _write_inbox(session: Session, folder: Path, settings: Settings) -> dict:
    manifest = json.loads((Path(folder) / "manifest.json").read_text(encoding="utf-8"))
    payload = {**manifest, "folder": str(Path(folder).resolve())}
    inbox = Path(settings.main_inbox_dir)
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / f"{session.id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


async def notify_main(
    session: Session,
    folder: Path,
    settings: Settings,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[str]:
    """Ghi main_inbox/<id>.json; có MAIN_WEBHOOK_URL thì POST (httpx, timeout 10s, retry 2).
    Trả list cảnh báo (webhook lỗi KHÔNG raise)."""
    warnings: list[str] = []
    payload = _write_inbox(session, folder, settings)
    if not settings.main_webhook_url:
        return warnings
    last = ""
    async with httpx.AsyncClient(timeout=10, transport=transport) as client:
        for _ in range(3):  # 1 lần + retry 2
            try:
                resp = await client.post(settings.main_webhook_url, json=payload)
                resp.raise_for_status()
                return warnings
            except Exception as exc:  # noqa: BLE001
                last = str(exc) or type(exc).__name__
    warnings.append(f"Không gửi được webhook tới MAIN: {last}")
    return warnings
