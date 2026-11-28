# TASKS — Kế hoạch triển khai chatbot tạo game học tập

> **Cách dùng (cho agent code):** làm **đúng một task mỗi lần**, theo thứ tự. Chỉ đọc các mục `docs/`
> được ghi ở dòng **Đọc** của task. Xong task thì đánh `[x]`, ghi một dòng vào `PROGRESS.md`, rồi
> commit `T<nn>: <tên task>`. Một task chỉ được tính là xong khi **mọi lệnh ở dòng Kiểm tra đều pass**.
>
> **Khung code có sẵn:** khi làm một task, viết phần thân cho các hàm đã khai báo trong file của task, rồi
> **xoá dòng `pytestmark = ...skip...`** trong file test tương ứng và viết nội dung cho các test có sẵn.
> Thêm test mới thì được. **Không đổi tên hàm, tham số, kiểu trả về hay button id** khi chưa hỏi.
> Được thêm hàm private (`_ten`) nếu cần.
>
> Quy ước: `FakeLLM` = LLM giả trong `tests/conftest.py`, trả lời theo kịch bản. **Test không bao giờ
> gọi API thật.**

Trạng thái: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong

---

## Giai đoạn 0 — Nền móng

### [x] T01. Khởi tạo dự án
- **Đọc:** ARCHITECTURE §1–2
- **Hiện trạng:** **khung code đã có sẵn.** Mọi file, hàm, tham số, kiểu trả về và docstring đã được khai báo. Thân hàm là `raise NotImplementedError`. Các file test đã có tên test case và đang bị `skip`.
- **Làm:**
  1. `git init` (nếu chưa có), cài đặt: `pip install -e ".[dev]"` và `python -m playwright install chromium`.
  2. Xác nhận mọi module import được và khung đúng cấu trúc ARCHITECTURE §2.
- **Kiểm tra:** `python -c "import app.main, app.chatbot.engine, app.chatbot.pipeline, app.api.sessions"` · `ruff check .` · `pytest -q` (mọi test ở trạng thái skipped)
- **Bẫy:** không thêm thư viện ngoài danh sách stack. Muốn thêm thì ghi vào `PROGRESS.md` mục "Đề xuất" và dừng lại hỏi.

### [x] T02. Config
- **Đọc:** `.env.example`
- **File:** `app/config.py`, `tests/unit/test_config.py`
- **Làm:** `Settings(BaseSettings)` với mọi biến trong `.env.example` và đúng giá trị mặc định. Hàm `get_settings()` có `lru_cache`. Các path dùng kiểu `Path`, khởi tạo thì `mkdir(parents=True, exist_ok=True)`.
- **Test:** giá trị mặc định đúng; ghi đè được bằng `monkeypatch.setenv`; `MAX_FIX_ATTEMPTS` mặc định = 2.
- **Kiểm tra:** `pytest tests/unit/test_config.py -q`
- **Bẫy:** test phải gọi `get_settings.cache_clear()` sau khi đổi env.

---

## Giai đoạn 1 — Lõi domain (thuần Python, không mạng)

### [x] T03. Bộ câu hỏi: schema, validate, nạp file
- **Đọc:** QUESTION_SCHEMA (toàn bộ)
- **File:** `app/domain/questions.py`, `tests/fixtures/questions_valid.json`, `questions_valid.csv`, `questions_invalid.json`, `tests/unit/test_questions.py`
- **Làm:** `QUESTION_SCHEMA_TEXT`, `validate_bank(bank)->list[str]`, `normalize_bank`, `max_score`, `load_bank_file(path)` (json/csv), `BankFileError(errors: list[str])`.
- **Test (bắt buộc đủ):** file hợp lệ → `[]`; mỗi quy tắc ở §2 có ít nhất 1 case sai; `answer=True` cho mcq bị bắt; id trùng; CSV chữ cái `B` thành 1; CSV có BOM; CSV lỗi báo đúng số dòng; JSON dạng list.
- **Kiểm tra:** `pytest tests/unit/test_questions.py -q`
- **Bẫy:** bool là con của int; `csv` phải mở với `newline=""`, `encoding="utf-8-sig"`.

### [x] T04. Game contract: kiểm tra tĩnh + game mẫu chuẩn
- **Đọc:** GAME_CONTRACT §1–4, §6
- **File:** `app/domain/contract.py`, `tests/fixtures/reference_game.html`, `tests/unit/test_contract.py`
- **Làm:**
  1. `CONTRACT_TEXT` (tóm tắt §1–4 cho prompt), `REQUIRED_TESTIDS`, `static_check(html)->list[str]`.
  2. `inject_bank(html, bank)->str`: thay hoặc chèn thẻ `#question-bank` (escape `</`). Đặt hàm này ở `contract.py` để N3 và FIX dùng chung.
  3. **Viết tay `reference_game.html`**: game quiz SVG đơn giản, đạt 100% contract, hỗ trợ cả 3 loại câu, có màn hình kết quả đầy đủ §3. Đây là "golden file" cho N4 và FakeLLM.
- **Test:** reference game → `static_check == []`; mỗi lỗi C1–C6 và mỗi testid thiếu đều bị bắt (dùng các bản biến thể tạo bằng `str.replace` từ reference); `inject_bank` thay đúng 1 thẻ, chèn khi chưa có, escape `</script>` trong câu hỏi.
- **Kiểm tra:** `pytest tests/unit/test_contract.py -q`
- **Bẫy:** regex cho `alert(` không được bắt nhầm `obj.alert(`/`myalert(`. Dùng lookbehind `(?<![\w.$])`.

### [x] T05. Models + Session Memory (store)
- **Đọc:** ARCHITECTURE §3
- **File:** `app/core/models.py`, `app/core/store.py`, `tests/unit/test_store.py`
- **Làm:** các model Pydantic như §3. `SessionStore(root)` gồm: `create()`, `get(id)` (không có thì `KeyError`), `save(session)` (ghi nguyên tử), `lock(id)` (`asyncio.Lock`), `session_dir(id)`, `safe_path(id, filename)` (chống `..`, đường dẫn tuyệt đối, ký tự lạ). Thêm helper `add_message`, `add_event`.
- **Test:** vòng tròn save→get bằng nhau; `safe_path("../x")` raise `ValueError`; ghi nguyên tử (không còn file `.tmp`); `updated_at` tăng.
- **Kiểm tra:** `pytest tests/unit/test_store.py -q`

### [x] T06. LLM client + FakeLLM + prompts loader
- **Đọc:** ARCHITECTURE §5 (đoạn cuối), SPEC §5
- **File:** `app/core/llm.py`, `app/core/prompts.py`, `tests/conftest.py`, `tests/unit/test_llm.py`
- **Làm:**
  - `class LLMClient(Protocol): async def complete(self, *, system, user, model, json_mode=False) -> str`
  - `OpenAILLM` dùng `AsyncOpenAI`, timeout 120 s, retry 2 lần (2 s, 5 s) khi lỗi mạng/5xx/timeout. Không retry lỗi 4xx.
  - `parse_json(text)`: chịu được ```` ```json ```` và chữ thừa trước/sau. Lỗi thì `LLMFormatError`.
  - `extract_html(text)`: lấy từ khối ```` ```html ```` hoặc từ `<!DOCTYPE` tới `</html>`. Lỗi thì `LLMFormatError`.
  - `load_prompt(name, **vars)`: thay `{{VAR}}`. Thiếu biến thì raise.
  - `FakeLLM(script: dict[str, list[str] | Callable])`: chọn câu trả lời theo **tên prompt** (gửi kèm system dưới dạng dòng đầu `# prompt: <name>`). Ghi lại mọi lời gọi vào `.calls`.
- **Test:** parse_json với 4 kiểu bọc; extract_html; retry (mock để lần 1 lỗi, lần 2 thành công); FakeLLM hết kịch bản thì raise rõ ràng.
- **Kiểm tra:** `pytest tests/unit/test_llm.py -q`
- **Bẫy:** không đọc `OPENAI_API_KEY` lúc import module. Chỉ đọc khi khởi tạo `OpenAILLM`.

### [x] T07. Prompts
- **Đọc:** SPEC §2, GAME_CONTRACT §4 và §6, QUESTION_SCHEMA §1
- **File:** `app/prompts/{intake,intent,question_gen,question_edit,design,codegen,fix}.md`, `tests/unit/test_prompts.py`
- **Làm:** dòng 1 của mỗi file là `# prompt: <name>`. Nội dung:
  - `intake`: phân loại game học tập, trả JSON `{is_educational, reason, subject, grade, suggested_game_type}`. Liệt kê rõ các trường hợp từ chối (thuần giải trí, cờ bạc, bạo lực, người lớn, không phải game, sao chép game thương mại).
  - `intent`: map câu chữ tự do thành `button_id` trong danh sách được truyền vào, hoặc `null`.
  - `question_gen`: đúng số câu; nguồn tài liệu thì **chỉ** dùng tài liệu; 40/40/20 nhận biết/thông hiểu/vận dụng; mcq có đúng 1 đáp án, phương án nhiễu hợp lý, không dùng "tất cả đều đúng"; có explanation; biến `{{SCHEMA}}`.
  - `question_edit`: chỉ sửa phần được yêu cầu, giữ id cũ.
  - `design`: JSON gồm `title, game_type, target, learning_goals, mechanics, screens, visual_style, feedback, scoring, result_screen, accessibility, question_edit`. Ràng buộc: mỗi câu dùng 1 lần theo thứ tự; điểm = Σ points; bắt buộc có màn kết quả; không sao chép game thương mại.
  - `codegen` và `fix`: chèn `{{CONTRACT}}`; dặn để trống `#question-bank`; hiệu ứng ≤ 600 ms; reset khi chơi lại; chỉ trả 1 khối ```` ```html ````.
- **Test:** mọi prompt load được; render đủ biến; dòng đầu đúng tên.
- **Kiểm tra:** `pytest tests/unit/test_prompts.py -q`

---

## Giai đoạn 2 — Các node (mỗi node một hàm async, nhận dependency qua tham số)

### [x] T08. INPUT: cổng game học tập + phân loại ý định
- **Đọc:** SPEC §2 (bổ sung 1–2), §4 (câu từ chối)
- **File:** `app/nodes/intake.py`, `tests/unit/test_intake.py`
- **Làm:** `check_educational(llm, request) -> IntakeResult`; `classify_intent(llm, text, buttons) -> str | None`. Nếu đầu vào là chuỗi trùng (không phân biệt hoa/thường) với label hoặc id của nút thì trả luôn, **không gọi LLM**.
- **Test:** FakeLLM trả true/false; JSON sai định dạng thì raise `LLMFormatError`; khớp label trực tiếp thì `llm.calls == []`.
- **Kiểm tra:** `pytest tests/unit/test_intake.py -q`

### [x] T09. N1 — Đọc tài liệu
- **Đọc:** SPEC §5 (giới hạn tài liệu)
- **File:** `app/nodes/n1_read_docs.py`, `tests/fixtures/sample.{txt,md,docx,pdf}`, `tests/unit/test_n1.py`
- **Làm:** `read_documents(paths, max_chars) -> DocResult(text, docs, warnings)`. Hỗ trợ `.pdf .docx (cả bảng) .txt .md`. File > 10 MB hoặc sai đuôi thì báo lỗi. PDF không trích được chữ thì cảnh báo "có thể là file scan". Cắt tổng còn `max_chars`.
- **Test:** đủ 4 định dạng (tạo fixture docx/pdf bằng script `tests/fixtures/make_fixtures.py`, commit cả file sinh ra); sai đuôi; cắt độ dài.
- **Kiểm tra:** `pytest tests/unit/test_n1.py -q`
- **Bẫy:** `.txt` đọc bằng `utf-8`, lỗi thì thử lại với `cp1258`/`latin-1`.

### [x] T10. N1b — Bộ câu hỏi (tạo / nạp / sửa)
- **Đọc:** QUESTION_SCHEMA §2–4, SPEC §3 (`BUILDING_QUESTIONS`, `AWAIT_QUESTION_APPROVAL`)
- **File:** `app/nodes/n1b_questions.py`, `tests/unit/test_n1b.py`
- **Làm:**
  - `from_user_file(path) -> bank` (raise `BankFileError`).
  - `generate(llm, *, source, request, n, doc_text="", topic="", feedback="") -> bank`: gọi `question_gen`. Bank không hợp lệ thì gửi lại kèm danh sách lỗi, **tối đa 2 lần**, sau đó raise. Kiểm thêm `len == n`.
  - `edit(llm, bank, instruction, source) -> bank`: kết quả phải hợp lệ. Nếu `source == "user"` thì các câu không được nhắc tới phải giữ nguyên (so theo id).
  - `preview_text(bank, limit=5)`.
- **Test:** sinh hợp lệ ngay lần 1; lần 1 sai, lần 2 đúng (kiểm prompt lần 2 có chứa lỗi); sai 3 lần thì raise; edit giữ id.
- **Kiểm tra:** `pytest tests/unit/test_n1b.py -q`

### [x] T11. N2 — Thiết kế game
- **Đọc:** ARCHITECTURE §5, prompt `design`
- **File:** `app/nodes/n2_design.py`, `tests/unit/test_n2.py`
- **Làm:** `design(llm, session, revision=None) -> dict`. Prompt gồm: ngữ cảnh phiên (yêu cầu, chủ đề, môn/lớp, các lần chỉnh sửa trước), thống kê bộ câu hỏi (số câu, loại, maxScore, 3 câu mẫu), thiết kế hiện tại nếu có, `revision` được đánh dấu **ưu tiên cao nhất**. Thiếu key bắt buộc thì raise. Đọc và ghi `session.design` / `design_history` (Session Memory).
- **Test:** thiếu key thì raise; có revision thì prompt chứa revision; design cũ được đẩy vào history.
- **Kiểm tra:** `pytest tests/unit/test_n2.py -q`
- **Bẫy:** **không** đưa toàn bộ bộ câu hỏi vào prompt N2 (tốn token). Chỉ đưa thống kê và 3 câu mẫu.

### [x] T12. N3 — Sinh HTML
- **Đọc:** GAME_CONTRACT §6
- **File:** `app/nodes/n3_generate.py`, `tests/unit/test_n3.py`
- **Làm:** `generate(llm, store, session) -> Version`: gọi prompt `codegen` (gồm design + 2 câu mẫu), `extract_html`, `inject_bank` với bộ câu hỏi thật, ghi `sessions/<id>/v<n>/index.html`, thêm `Version`.
- **Test:** FakeLLM trả reference_game có `#question-bank` rỗng, file ghi ra chứa đủ id câu hỏi; số phiên bản tăng dần.
- **Kiểm tra:** `pytest tests/unit/test_n3.py -q`

### [x] T13. N4 — Kiểm tra tự động (Contract + Playwright)
- **Đọc:** GAME_CONTRACT §5 (toàn bộ)
- **File:** `app/nodes/n4_test.py`, `tests/integration/test_n4.py`, các fixture lỗi `tests/fixtures/broken_*.html`
- **Làm:** `async def run_tests(session, version, settings) -> TestReport(passed, errors, screenshots)`. Static check trước, **chỉ chạy Playwright khi static pass**. Playwright sync chạy trong `asyncio.to_thread`. Thực hiện đúng 7 bước §5 cho 2 viewport. Mỗi viewport dùng một page riêng; một bước lỗi thì ghi lỗi và chuyển sang viewport tiếp theo. Chặn mạng bằng `page.route("**/*", ...)`, chỉ cho `file://`.
- **Test (integration, đánh dấu `@pytest.mark.browser`):**
  - reference_game: `passed` và đủ 4 ảnh chụp.
  - `broken_no_result.html` (không hiện result-screen): bắt được lỗi.
  - `broken_score.html` (cộng sai điểm): bắt được lỗi.
  - `broken_jserror.html` (throw khi start): có `pageerror`.
  - `broken_overflow.html` (rộng 500px cố định): báo tràn ở `[375px]`.
- **Kiểm tra:** `pytest tests/integration/test_n4.py -q -m browser`
- **Bẫy:** listener `console`/`pageerror` phải đăng ký **trước** `goto`. Dialog phải `dismiss()`, nếu không page sẽ treo. Timeout lấy từ settings, không hard-code.

### [x] T14. FIX — AI sửa lỗi (≤ 2 lần)
- **Đọc:** SPEC §2 (bổ sung 4)
- **File:** `app/nodes/fixer.py`, `tests/unit/test_fixer.py`
- **Làm:** `fix(llm, session, version, errors)`: prompt `fix` gồm tối đa 20 lỗi và HTML hiện tại. Kết quả đi qua `extract_html` rồi `inject_bank`, ghi đè file của **cùng version**, tăng `fix_attempts`. Không tự kiểm tra giới hạn (pipeline kiểm).
- **Test:** `fix_attempts` tăng; bộ câu hỏi luôn được nhúng lại kể cả khi model xoá thẻ.
- **Kiểm tra:** `pytest tests/unit/test_fixer.py -q`

### [x] T15. N5 — Chơi thử
- **Đọc:** SPEC §3 (`AWAIT_REVIEW`), §4
- **File:** `app/nodes/n5_review.py`, `tests/unit/test_n5.py`
- **Làm:** `build_review_message(session, version) -> Message`, gồm `preview_url=/preview/{id}/v{n}` và các nút: test pass thì `[approve, revise, cancel]`; fail thì `[revise, cancel]` kèm tối đa 8 lỗi bằng lời dễ hiểu.
- **Test:** đúng bộ nút cho cả 2 trường hợp.
- **Kiểm tra:** `pytest tests/unit/test_n5.py -q`

### [x] T16. N6 — Xuất file + MAIN tiếp nhận
- **Đọc:** ARCHITECTURE §6
- **File:** `app/nodes/n6_export.py`, `tests/unit/test_n6.py`
- **Làm:** `export(session, version, settings) -> Path` (slug tiếng Việt bỏ dấu, `đ` thành `d`; copy html, questions.json, screenshots, manifest; tạo `export.zip`). `notify_main(...)`: ghi inbox và POST webhook (httpx, retry 2). Webhook lỗi thì trả cảnh báo, không raise.
- **Test:** cấu trúc thư mục và manifest đúng các trường; slug `"Ôn tập Đại số"` thành `"on-tap-dai-so"`; webhook giả dùng `httpx.MockTransport` trả 500, vẫn có inbox và cảnh báo.
- **Kiểm tra:** `pytest tests/unit/test_n6.py -q`
- **Bẫy:** **chặn xuất** nếu `version.test_passed is not True` (raise `ValueError`).

---

## Giai đoạn 3 — Chatbot

### [x] T17. Replies tiếng Việt
- **Đọc:** SPEC §4
- **File:** `app/chatbot/replies.py`
- **Làm:** mọi câu chữ và nút của bot là hằng/hàm ở đây (`GREETING`, `ASK_SOURCE`, `BTN_SOURCE_USER`…, `reject(reason)`, `progress(node, detail)`). Code khác **không** được hard-code chuỗi hiển thị.
- **Kiểm tra:** `ruff check app/chatbot/replies.py`

### [x] T18. ChatEngine — state machine
- **Đọc:** SPEC §3 (toàn bộ), ARCHITECTURE §5
- **File:** `app/chatbot/engine.py`, `app/chatbot/pipeline.py`, `app/core/events.py`, `tests/integration/test_engine.py`
- **Làm:**
  - `EventBus`: `publish(session_id, event)`, `subscribe(session_id) -> AsyncIterator`.
  - `ChatEngine(store, llm, bus, settings, tester=n4.run_tests)`: `async handle(session_id, text=None, action=None)`. Dispatch bằng **bảng** `{State: handler}`, không dùng if/elif dài. Mỗi handler trả về state mới và danh sách message.
  - Đầu vào không hợp lệ với state hiện tại thì trả câu hướng dẫn, giữ nguyên state.
  - Đang ở `*_RUNNING`/`BUILDING_QUESTIONS`/`EXPORTING` mà có tin nhắn thì trả "đang xử lý".
  - `pipeline.run_design_cycle` và `run_export` theo ARCHITECTURE §5. Phát `progress` trước mỗi node. Exception thì state `FAILED`, ghi `error`, gửi message có nút `retry`.
  - Đếm vòng chỉnh sửa: vượt `MAX_REVISION_ROUNDS` thì `FAILED`.
  - `tester` được inject để test engine không cần trình duyệt.
- **Test (FakeLLM + tester giả):** đi trọn 3 nguồn câu hỏi; từ chối yêu cầu không phải học tập; tester fail 3 lần thì fixer được gọi đúng 2 lần, sau đó review chỉ có nút revise/cancel; vòng chỉnh sửa quay lại N2 với revision; revision có `question_edit` thì bank được sửa; nhắn tin khi đang chạy thì nhận "đang xử lý".
- **Kiểm tra:** `pytest tests/integration/test_engine.py -q`
- **Bẫy:** `asyncio.create_task` phải giữ reference (lưu vào set) để task không bị GC. Mọi thay đổi session phải nằm trong `store.lock(id)`.

### [ ] T19. API FastAPI + SSE + preview + upload
- **Đọc:** ARCHITECTURE §4
- **File:** `app/main.py`, `app/api/{sessions,events,preview}.py`, `tests/integration/test_api.py`
- **Làm:** đủ endpoint §4. Upload: kiểm đuôi và kích thước, lưu qua `store.safe_path`, gọi `engine.handle(..., action="file_uploaded")`. Preview trả HTML với header `Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:`. Export zip chỉ khi `DONE`, nếu không thì 409.
- **Test:** `httpx.AsyncClient` + `ASGITransport`, đi luồng topic tới AWAIT_REVIEW; upload file `.exe` bị 400; path traversal bị 400; export trước DONE bị 409.
- **Kiểm tra:** `pytest tests/integration/test_api.py -q`

### [x] T20. Giao diện chat web
- **Đọc:** SPEC §4, ARCHITECTURE §4
- **File:** `web/index.html`, `web/chat.js`, `web/chat.css`
- **Làm:** khung chat (bong bóng bot/người dùng), nút quick-reply từ `message.buttons`, ô nhập + nút gửi, nút đính kèm file (chỉ hiện ở `AWAIT_SOURCE_INPUT`), thanh tiến độ từ SSE, `iframe sandbox="allow-scripts"` cho `preview_url` kèm nút "Mở toàn màn hình", link tải zip khi `DONE`. Khôi phục phiên qua `?session=<id>` (lưu id vào `localStorage`). Responsive tới 375px. Không framework, không CDN.
- **Kiểm tra:** `tests/e2e/test_chat_ui.py` (T21).

---

## Giai đoạn 4 — Chất lượng & bàn giao

### [ ] T21. E2E toàn luồng (FakeLLM + Playwright thật)
- **File:** `tests/e2e/test_chat_ui.py`
- **Làm:** chạy uvicorn trên cổng ngẫu nhiên với FakeLLM (inject qua `app.dependency_overrides` hoặc factory `create_app(llm=...)`). Playwright mở `/` và đi đúng kịch bản SPEC §4: chủ đề → duyệt câu hỏi → chơi thử (iframe hiển thị) → chỉnh sửa → v2 → hài lòng → thấy link zip; kiểm `main_inbox/<id>.json` tồn tại.
- **Kiểm tra:** `pytest tests/e2e -q -m browser`

### [x] T22. Smoke test với LLM thật (thủ công)
- **File:** `scripts/smoke_real_llm.py`
- **Làm:** chạy pipeline không giao diện với `OPENAI_API_KEY` thật, chủ đề cố định, 5 câu. In ra số lần sửa, kết quả N4, đường dẫn output. **Không** chạy trong `pytest` mặc định.
- **Kiểm tra:** người dùng tự chạy `python scripts/smoke_real_llm.py`

### [ ] T23. README + dọn dẹp
- **File:** `README.md`
- **Làm:** cài đặt, chạy (`uvicorn app.main:create_app --factory --reload`), biến môi trường, cấu trúc, cách chạy test, sơ đồ luồng (copy từ SPEC §2).
- **Kiểm tra:** `ruff check . && ruff format --check . && pytest -q -m "not browser" && pytest -q -m browser`

---

## Definition of Done cho toàn dự án
- [ ] Mọi task `[x]`, toàn bộ test pass, ruff sạch.
- [ ] Yêu cầu không phải game học tập luôn bị từ chối (test T08, T18).
- [ ] Không có đường nào tới N2 khi chưa có bộ câu hỏi hợp lệ (test T18).
- [ ] Game xuất ra luôn có màn hình kết quả cuối game và chấm điểm đúng (N4 bắt buộc pass mới xuất được, test T16).
- [ ] FIX chạy tối đa 2 lần mỗi phiên bản (test T18).
