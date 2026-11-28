# PARALLEL PLAN — Chia đợt chạy song song cho agent coder

> Người dùng: **agent điều phối** (skill `/orchestrate`). Agent coder không cần đọc file này,
> vì brief giao việc đã chứa đủ thông tin.

## 1. Đồ thị phụ thuộc

Phụ thuộc được xác định theo **phần thân hàm cần gọi** (không theo import). Khung code đã khai báo
mọi class, nên import luôn thành công.

| Task | Phụ thuộc (phải merge trước) | Lý do |
|---|---|---|
| T01 | — | cài đặt, commit baseline |
| T02 config | T01 | |
| T03 questions | T01 | thuần Python |
| T04 contract + reference_game | T01 | thuần Python + HTML |
| T05 models + store | T01 | `utcnow/new_id` cần thân hàm thì mới tạo được model |
| T06 llm + FakeLLM + conftest | T01 | chỉ dùng **khai báo** `Settings` |
| T09 N1 đọc tài liệu | T01 | thuần Python, test dùng `tmp_path` |
| T17 replies | T01 | `Button` không có default factory |
| T20 web UI | T01 | chỉ dựa vào API spec + id cố định trong `index.html` |
| T07 prompts | T06 | test cần `load_prompt` |
| T08 intake | T06 | FakeLLM, `parse_json` |
| T10 N1b | T03, T06 | |
| T11 N2 | T03, T05, T06 | |
| T12 N3 | T04, T05, T06 | `inject_bank`, `SessionStore` |
| T13 N4 | T03, T04, T05 | `reference_game.html`, `static_check`, `max_score` |
| T14 FIX | T04, T05, T06 | |
| T15 N5 | T05, T17 | `review_buttons` |
| T16 N6 | T02, T03, T05 | |
| T18 engine + pipeline | T07, T08, T10–T17 | gọi mọi node |
| T19 API | T18 | |
| T22 smoke LLM thật | T08, T10–T14 | |
| T21 e2e | T19, T20 | |
| T23 README | tất cả | |

Ghi chú: T08, T10, T11, T12, T14 **không** cần chờ T07. Test của chúng dùng FakeLLM, còn tên biến
trong prompt (`{{SCHEMA}}`, `{{CONTRACT}}`, `{{BUTTONS}}`) đã được chốt trong khung, T07 không được đổi.

## 2. Các đợt (wave)

```
W0  T01                                     (điều phối tự làm, tuần tự)
W1  T04 T06 T05 T20 T03 T02 T09 T17         (8 task song song)
W2  T13 T12 T10 T11 T14 T07 T08 T16 T15     (9 task song song)
W3  T18                                     (đường găng, 1 agent mạnh nhất)
W4  T19 T22                                 (2 task song song)
W5  T21
W6  T23
```

Trong mỗi đợt, task được xếp **theo thứ tự ưu tiên giao trước**, tức task dài và rủi ro hơn đứng trước.
Số agent chạy cùng lúc mặc định là `MAX_PARALLEL = 4`. Agent nào xong thì giao task kế tiếp của
**cùng đợt**. Task nào đã đủ phụ thuộc (theo §1) thì được giao sớm, không cần chờ cả đợt trước xong.

Đường găng: T01 → T06 → T12/T13 → T18 → T19 → T21 → T23. Ưu tiên giải phóng T06, T04, T05 sớm nhất.

## 3. Quyền sở hữu file (chống xung đột merge)

Mỗi task **chỉ được sửa** các file của mình. Agent coder sửa file ngoài danh sách thì phiên bản đó bị loại.

| Task | File được sửa |
|---|---|
| T02 | `app/config.py`, `tests/unit/test_config.py` |
| T03 | `app/domain/questions.py`, `tests/unit/test_questions.py`, `tests/fixtures/questions_*` |
| T04 | `app/domain/contract.py`, `tests/unit/test_contract.py`, `tests/fixtures/reference_game.html` |
| T05 | `app/core/models.py`, `app/core/store.py`, `tests/unit/test_store.py` |
| T06 | `app/core/llm.py`, `app/core/prompts.py`, **`tests/conftest.py`**, `tests/unit/test_llm.py` |
| T07 | `app/prompts/*.md`, `tests/unit/test_prompts.py` |
| T08 | `app/nodes/intake.py`, `tests/unit/test_intake.py` |
| T09 | `app/nodes/n1_read_docs.py`, `tests/unit/test_n1.py`, `tests/fixtures/make_fixtures.py`, `tests/fixtures/sample.*` |
| T10 | `app/nodes/n1b_questions.py`, `tests/unit/test_n1b.py` |
| T11 | `app/nodes/n2_design.py`, `tests/unit/test_n2.py` |
| T12 | `app/nodes/n3_generate.py`, `tests/unit/test_n3.py` |
| T13 | `app/nodes/n4_test.py`, `tests/integration/test_n4.py`, `tests/fixtures/broken_*.html` |
| T14 | `app/nodes/fixer.py`, `tests/unit/test_fixer.py` |
| T15 | `app/nodes/n5_review.py`, `tests/unit/test_n5.py` |
| T16 | `app/nodes/n6_export.py`, `tests/unit/test_n6.py` |
| T17 | `app/chatbot/replies.py` |
| T18 | `app/chatbot/engine.py`, `app/chatbot/pipeline.py`, `app/core/events.py`, `tests/integration/test_engine.py` |
| T19 | `app/main.py`, `app/api/*.py`, `tests/integration/test_api.py` |
| T20 | `web/*` |
| T21 | `tests/e2e/*` |
| T22 | `scripts/smoke_real_llm.py` |
| T23 | `README.md` |

**File dùng chung, chỉ điều phối được sửa:** `TASKS.md`, `PROGRESS.md`, `CLAUDE.md`, `pyproject.toml`,
`docs/*`, `.claude/*`, `.gitignore`.

- Fixture riêng của task: khai báo **ngay trong file test của task**. Không sửa `tests/conftest.py`
  (trừ T06).
- Cần sửa file của task khác (ví dụ phát hiện bug ở `contract.py` khi làm T13): **không sửa**. Ghi vào
  mục `BLOCKERS` trong báo cáo, điều phối sẽ quyết định.
- Cần thư viện mới hoặc cần đổi chữ ký hàm: không làm. Ghi vào `PROPOSALS` trong báo cáo.

## 4. Cổng kiểm tra khi merge

Sau **mỗi** lần merge một nhánh task vào nhánh tích hợp:
```
ruff check . && ruff format --check . && pytest -q -x -m "not browser"
```
Sau mỗi đợt có T04, T13, T20 hoặc T21: chạy thêm `pytest -q -x -m browser`.
Cổng fail thì huỷ merge, gửi lỗi về đúng agent đã làm task đó để sửa trên nhánh của nó.
