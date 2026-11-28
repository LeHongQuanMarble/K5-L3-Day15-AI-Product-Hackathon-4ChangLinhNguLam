"""Nạp prompt từ app/prompts/<name>.md và thay biến {{VAR}}. (T06)"""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
PROMPT_NAMES = ("intake", "intent", "question_gen", "question_edit", "design", "codegen", "fix")


class PromptVarMissingError(KeyError):
    """Prompt còn biến {{VAR}} chưa được truyền."""


def load_prompt(name: str, **variables: str) -> str:
    """Đọc prompt (utf-8), thay {{KEY}} bằng variables[KEY]; còn {{...}} -> PromptVarMissingError."""
    raise NotImplementedError


def prompt_name_of(system: str) -> str | None:
    """Đọc tên prompt từ dòng đầu '# prompt: <name>' (FakeLLM dùng để chọn kịch bản)."""
    raise NotImplementedError
