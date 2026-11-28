# PROGRESS

Định dạng: `T<nn> | <ngày> | <tóm tắt ≤ 15 từ> | <lưu ý>`

## Nhật ký
T01 | 2026-11-28 | Cài deps + chromium, import OK, ruff sạch, 143 test skipped | Python 3.13; repo = team repo nhánh integration
T05 | 2026-11-28 | Models Pydantic + SessionStore ghi nguyên tử, safe_path, lock | 15 test pass
T20 | 2026-11-28 | Chat UI thuần JS: quick-reply, upload, SSE, iframe preview, zip | Chưa test browser; giả định API: POST /api/sessions→{id,messages,state?}, field upload "files"; testid mới msg-bot/msg-user/btn-<id>/download-zip
T06 | 2026-11-28 | LLMClient/OpenAILLM retry, parse_json, extract_html, load_prompt, FakeLLM, conftest | fixture lazy; calls có key "prompt"
T04 | 2026-11-28 | CONTRACT_TEXT, static_check, inject_bank, reference_game.html 3 loại câu | 24 test; chưa chạy browser

## Câu hỏi cần người dùng trả lời

## Đề xuất (thư viện / thay đổi spec)
