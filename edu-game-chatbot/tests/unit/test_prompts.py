"""Prompts (T07)"""

import re

import pytest

from app.core.prompts import PROMPT_NAMES, PROMPTS_DIR, PromptVarMissingError, load_prompt, prompt_name_of

VARS = {
    "codegen": {"CONTRACT": "CONTRACT_X"},
    "fix": {"CONTRACT": "CONTRACT_X"},
    "intent": {"BUTTONS": "BUTTONS_X"},
    "question_gen": {"SCHEMA": "SCHEMA_X"},
    "question_edit": {"SCHEMA": "SCHEMA_X"},
}


@pytest.mark.parametrize("name", PROMPT_NAMES)
def test_all_prompts_load(name: str) -> None:
    text = load_prompt(name, **VARS.get(name, {}))
    assert "TODO" not in text and not re.search(r"\{\{", text)


@pytest.mark.parametrize("name", PROMPT_NAMES)
def test_first_line_is_prompt_name(name: str) -> None:
    raw = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    assert raw.split("\n", 1)[0] == f"# prompt: {name}"
    assert prompt_name_of(raw) == name


@pytest.mark.parametrize("name", sorted(VARS))
def test_render_variables(name: str) -> None:
    text = load_prompt(name, **VARS[name])
    for value in VARS[name].values():
        assert value in text


@pytest.mark.parametrize("name", sorted(VARS))
def test_missing_variable_raises(name: str) -> None:
    with pytest.raises(PromptVarMissingError):
        load_prompt(name)


@pytest.mark.parametrize("name", ["codegen", "fix"])
def test_code_prompts_rules(name: str) -> None:
    text = load_prompt(name, CONTRACT="C")
    assert "#question-bank" in text and "600 ms" in text and "```html" in text
