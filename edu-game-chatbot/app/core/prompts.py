"""Nạp prompt từ app/prompts/<name>.md và thay biến {{VAR}}. (T06)"""

from __future__ import annotations

import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
PROMPT_NAMES = ("intake", "intent", "question_gen", "question_edit", "design", "codegen", "fix", "game_ideas")

_VAR_RE = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}")


class PromptVarMissingError(KeyError):
    """Prompt còn biến {{VAR}} chưa được truyền."""


def load_prompt(name: str, **variables: str) -> str:
    """Đọc prompt (utf-8), thay {{KEY}} bằng variables[KEY]; còn {{...}} -> PromptVarMissingError."""
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    missing = sorted({k for k in _VAR_RE.findall(text) if k not in variables})
    if missing:
        raise PromptVarMissingError(f"Prompt '{name}' thiếu biến: {', '.join(missing)}")
    return _VAR_RE.sub(lambda m: str(variables[m.group(1)]), text)


def prompt_name_of(system: str) -> str | None:
    """Đọc tên prompt từ dòng đầu '# prompt: <name>' (FakeLLM dùng để chọn kịch bản)."""
    first = system.lstrip().split("\n", 1)[0]
    m = re.match(r"#\s*prompt:\s*(\S+)", first)
    return m.group(1) if m else None
