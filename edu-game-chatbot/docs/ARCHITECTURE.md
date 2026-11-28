# ARCHITECTURE

## 1. Stack (đã chốt — không tự đổi)

| Phần | Công nghệ |
|---|---|
| Ngôn ngữ | Python 3.11+ |
| Web/API | FastAPI + Uvicorn, SSE (`sse-starlette`) để đẩy tiến độ |
| Frontend chat | 1 trang HTML + JS thuần (không build step), phục vụ tĩnh từ FastAPI |
| LLM | `openai` SDK (Chat Completions), model cấu hình qua `.env` |
| Đọc tài liệu | `pypdf`, `python-docx` |
| Kiểm thử game | `playwright` (Chromium, sync API chạy trong thread) |
| Model dữ liệu | `pydantic` v2 |
| Test | `pytest`, `pytest-asyncio`, `httpx` (TestClient) |
| Lint/format | `ruff` (lint + format) |

## 2. Cấu trúc thư mục

```
app/
  __init__.py
  config.py              # Settings (pydantic-settings), đọc .env
  main.py                # FastAPI app factory, mount static, routers
  api/
    sessions.py          # REST: tạo phiên, gửi tin nhắn, upload, export
    events.py            # SSE stream tiến độ
    preview.py           # phục vụ HTML game để chơi thử (iframe)
  core/
    models.py            # Pydantic: Session, Message, Version, enums State/Source
    store.py             # SessionStore: lưu/nạp sessions/<id>/memory.json (Session Memory)
    events.py            # EventBus: publish/subscribe theo session_id
    llm.py               # LLMClient protocol, OpenAILLM, parse_json, extract_html
    prompts.py           # load_prompt(name) + render biến {{X}}
  domain/
    questions.py         # schema + validate + load json/csv  (docs/QUESTION_SCHEMA.md)
    contract.py          # CONTRACT_TEXT + static_check     (docs/GAME_CONTRACT.md)
  nodes/
    intake.py            # cổng game học tập + phân loại ý định
    n1_read_docs.py
    n1b_questions.py     # tạo / nạp / sửa bộ câu hỏi
    n2_design.py
    n3_generate.py       # sinh HTML + inject_bank
    n4_test.py           # static_check + Playwright
    fixer.py
    n5_review.py         # chuẩn bị preview URL + nút
    n6_export.py         # xuất folder + zip + bàn giao MAIN
  chatbot/
    engine.py            # ChatEngine: state machine, handle_message/handle_action
    pipeline.py          # chạy N2→N3→N4↔FIX ở background, phát event
    replies.py           # mọi câu chữ tiếng Việt của bot (1 chỗ duy nhất)
  prompts/*.md           # prompt LLM
web/
  index.html  chat.js  chat.css
tests/
  conftest.py            # FakeLLM, tmp dirs, fixtures
  fixtures/reference_game.html   # game mẫu đạt 100% contract
  fixtures/questions_valid.json  questions_valid.csv  questions_invalid.json  sample.docx/pdf/txt
  unit/  integration/  e2e/
sessions/  output/  main_inbox/   # runtime, .gitignore
```

## 3. Mô hình dữ liệu (app/core/models.py)

```python
class State(StrEnum): AWAIT_REQUEST, AWAIT_SOURCE, AWAIT_SOURCE_INPUT, BUILDING_QUESTIONS,
    AWAIT_QUESTION_APPROVAL, AWAIT_GAMEPLAY, AWAIT_CONTROLS, AWAIT_VISUAL, READY_TO_DESIGN, PIPELINE_RUNNING, AWAIT_REVIEW,
    AWAIT_REVISION_TEXT, EXPORTING, DONE, REJECTED, CANCELLED, FAILED
class Source(StrEnum): USER="user", DOCUMENT="document", TOPIC="topic"

class Button(BaseModel): id: str; label: str
class Message(BaseModel):
    id: str; role: Literal["user","bot","system"]; text: str
    buttons: list[Button] = []; attachments: list[str] = []; preview_url: str | None = None
    created_at: datetime
class Version(BaseModel):
    number: int; html_path: str; design: dict
    test_passed: bool | None = None; test_errors: list[str] = []; fix_attempts: int = 0
    screenshots: list[str] = []
class Session(BaseModel):
    id: str; state: State; created_at: datetime; updated_at: datetime
    request: str = ""; subject: str | None = None; grade: str | None = None
    source: Source | None = None; topic: str = ""; num_questions: int = 10
    documents: list[dict] = []          # {name, path, chars}
    question_bank: dict = {}; question_feedback: list[str] = []
    gameplay: str = ""; controls: str = ""; visual: str = ""   # nhãn nút hoặc mô tả tự do (F01)
    controls_code: str = ""             # mouse | keyboard | motion | voice | custom
    design: dict = {}; design_history: list[dict] = []
    revisions: list[str] = []; versions: list[Version] = []
    messages: list[Message] = []; events: list[dict] = []
    exported_to: str | None = None; error: str | None = None
```

`SessionStore` là **Session Memory** trong sơ đồ: ghi file nguyên tử (ghi `.tmp` rồi `os.replace`),
có `asyncio.Lock` theo session_id.

## 4. API

| Method | Path | Mô tả |
|---|---|---|
| POST | `/api/sessions` | tạo phiên → `{id, messages}` (lời chào) |
| GET | `/api/sessions/{id}` | trạng thái + toàn bộ messages |
| POST | `/api/sessions/{id}/messages` | body `{text}` hoặc `{action: button_id}` → `202 {accepted: true}` |
| POST | `/api/sessions/{id}/files` | multipart upload (tài liệu / file câu hỏi) |
| GET | `/api/sessions/{id}/events` | SSE: `message`, `progress`, `state` |
| GET | `/preview/{id}/v{n}` | HTML game phiên bản n (header CSP chặn mạng) |
| GET | `/api/sessions/{id}/export.zip` | tải gói đã xuất (chỉ khi `DONE`) |
| GET | `/` | giao diện chat (`web/index.html`) |

Event SSE (JSON):
`{"type":"progress","node":"N4","text":"Kiểm thử… (sửa lỗi 1/2)"}`,
`{"type":"message","message":{...}}`, `{"type":"state","state":"AWAIT_REVIEW"}`.

## 5. Luồng xử lý trong code

```
POST /messages ─► ChatEngine.handle(session, input)        (giữ lock phiên)
                   ├─ state chờ người dùng → xử lý nhanh, trả message
                   └─ cần chạy dài → đổi state *_RUNNING, asyncio.create_task(pipeline.run_*)
pipeline.run_design_cycle(session, revision):
   N2 design → (question_edit? → n1b.edit) → N3 generate → N4 test
   → while fail and fix_attempts < MAX_FIX: fixer → N4
   → N5 review message (+preview_url, nút theo kết quả) → state AWAIT_REVIEW
pipeline.run_export(session): N6 export → notify MAIN → state DONE
```

- Playwright (sync) chạy qua `await asyncio.to_thread(...)`. Không dùng sync API trong event loop.
- LLM gọi qua `asyncio.to_thread` hoặc `AsyncOpenAI`; chọn **AsyncOpenAI**.
- Mọi node là hàm thuần có `llm`/`store` truyền vào, **không** import singleton để test được.

## 6. Bàn giao MAIN (N6)

Sau khi xuất `output/<slug>_<session_id>/` (gồm `index.html`, `questions.json`, `manifest.json`, `screenshots/`):
1. Ghi `main_inbox/<session_id>.json` (= manifest + `folder` tuyệt đối).
2. Nếu có `MAIN_WEBHOOK_URL` thì POST manifest JSON, timeout 10 s, retry 2 lần. Webhook lỗi thì
   vẫn coi là xuất thành công nhưng thêm cảnh báo vào message.

`manifest.json`: `session_id, title, game_type, subject, grade, question_source, num_questions,
max_score, version, revisions[], entry:"index.html", exported_at`.
