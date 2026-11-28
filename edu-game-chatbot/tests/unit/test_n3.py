import json
import re
from pathlib import Path

import pytest

from app.nodes.n3_generate import build_codegen_prompt, generate


def _read(p):
    return Path(p).read_text(encoding="utf-8")


BANK = {
    "title": "T",
    "questions": [
        {"id": "q1", "type": "true_false", "question": "a", "answer": True, "points": 10},
        {"id": "q2", "type": "true_false", "question": "b", "answer": False, "points": 10},
    ],
}


@pytest.mark.asyncio
async def test_generate_injects_bank_and_increments(settings, store, fake_llm, reference_html):
    empty = re.sub(
        r'(<script[^>]*id="question-bank"[^>]*>).*?(</script>)', r"\1{}\2", reference_html, flags=re.S
    )
    fake_llm.add("codegen", f"```html\n{empty}\n```", f"```html\n{empty}\n```")
    s = store.create()
    s.question_bank = BANK
    s.design = {"theme": "x"}
    v1 = await generate(fake_llm, settings, store, s)
    v2 = await generate(fake_llm, settings, store, s)
    assert (v1.number, v2.number) == (1, 2)
    assert len(s.versions) == 2
    text = _read(v1.html_path)
    assert "q1" in text and "q2" in text
    assert v1.html_path.replace("\\", "/").endswith(f"{s.id}/v1/index.html")
    user = fake_llm.calls_for("codegen")[0]["user"]
    assert "theme" in user and "q1" in user


def test_build_prompt_limits_samples(store):
    s = store.create()
    s.question_bank = {"questions": [{"id": f"q{i}"} for i in range(5)]}
    p = build_codegen_prompt(s)
    assert "q1" in p and "q2" not in p
    assert json.dumps({}) in p or "{}" in p
