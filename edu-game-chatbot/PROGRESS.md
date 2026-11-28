# PROGRESS

Định dạng: `T<nn> | <ngày> | <tóm tắt ≤ 15 từ> | <lưu ý>`

## Nhật ký
T01 | 2026-11-28 | Cài deps + chromium, import OK, ruff sạch, 143 test skipped | Python 3.13; repo = team repo nhánh integration
T05 | 2026-11-28 | Models Pydantic + SessionStore ghi nguyên tử, safe_path, lock | 15 test pass
T20 | 2026-11-28 | Chat UI thuần JS: quick-reply, upload, SSE, iframe preview, zip | Chưa test browser; giả định API: POST /api/sessions→{id,messages,state?}, field upload "files"; testid mới msg-bot/msg-user/btn-<id>/download-zip
T06 | 2026-11-28 | LLMClient/OpenAILLM retry, parse_json, extract_html, load_prompt, FakeLLM, conftest | fixture lazy; calls có key "prompt"
T04 | 2026-11-28 | CONTRACT_TEXT, static_check, inject_bank, reference_game.html 3 loại câu | 24 test; chưa chạy browser
T02 | 2026-11-28 | Settings đủ biến .env.example, get_settings lru_cache + ensure_dirs | 4 test
T03 | 2026-11-28 | validate_bank, normalize_bank, max_score, load_bank_file json/csv, BankFileError | 25 test
T17 | 2026-11-28 | Mọi câu chữ/nút tiếng Việt, reject(), progress(), review_buttons | giữ nguyên button id
T12 | 2026-11-28 | N3 generate: codegen prompt, extract_html, inject_bank, ghi v<n>/index.html | không save session (theo docstring)
T09 | 2026-11-28 | read_documents pdf/docx(bảng)/txt/md, giới hạn 10MB, cắt max_chars | sample.pdf lưu dạng text, bị CRLF khi checkout (vẫn đọc được)
T11 | 2026-11-28 | N2 design: thống kê bank + 3 câu mẫu, revision ưu tiên, design_history | ngữ cảnh truyền qua user message
T10 | 2026-11-28 | N1b: from_user_file, generate retry ≤2, edit giữ câu không nhắc tới, preview | "nhắc tới" = id hoặc "câu N"
T07 | 2026-11-28 | 7 prompt đầy đủ, dòng đầu # prompt: <name>, giữ đúng biến | intent trả {"button_id": ...}
T08 | 2026-11-28 | check_educational, classify_intent (khớp nút trực tiếp không gọi LLM) | json_mode, intake_model
T14 | 2026-11-28 | fix(): ≤20 lỗi, extract_html, inject_bank lại, ghi đè cùng version, fix_attempts++ | 
T13 | 2026-11-28 | N4: static rồi Playwright 7 bước × 2 viewport, chặn mạng, 4 ảnh chụp | 6 browser test; reference_game pass §5
T16 | 2026-11-28 | N6: slug, copy html/questions/screenshots/manifest, zip, notify_main inbox + webhook retry | thêm kw-only transport=None
T15 | 2026-11-28 | N5: preview_url, nút theo test_passed, ≤8 lỗi gọn | lỗi kỹ thuật chưa dịch sang tiếng Việt

## Câu hỏi cần người dùng trả lời

## Đề xuất (thư viện / thay đổi spec)
- (điều phối) Thêm `.gitattributes` với `*.pdf binary` để sample.pdf không bị đổi CRLF khi checkout trên Windows. Chờ người dùng duyệt.
