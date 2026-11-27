# Bàn giao AI Core T08 & T09 cho TV3 (T14 Web/Backend) và TV4 (T18 Evaluation Run 1)

> **Branch:** `feat/t08-t09-ai-core-takeover` (Emergency Takeover tạm thời — Owner chính thức vẫn là TV2 Hồ Quốc Toản).  
> **Trạng thái hiện tại:** `Implemented` · `Tested` (**262/262** unit/acceptance tests) · `Mock Verified` · `Integration Ready (AI Core)` · **Chưa `Real AI Verified`** (blocker: máy hiện chưa có `.env` / `API_KEY` để chạy Real LLM `gpt-4o-mini`; chưa tích hợp Web/Backend T14 nên chưa tuyên bố Real AI E2E).

---

## 1. Entry Points (Shared Core Web/CLI)

| Người dùng | Entry Point | Input | Output |
|---|---|---|---|
| **TV3 (Backend Web T14 — `ailab/server.py`)** | `codebase.agent.run_agent(request, registry=None)` | `str` hoặc Spec request `dict` (`session_id`, `message`, `history`, `document_ids`, `selected_player_id`, `selected_model_id`, `selected_exam_id`, `generation_mode`) | Envelope **ApplicationPlan Contract v1.0** (`schema_version`, `simulated`, `decision`, `status`, `message`, `application_plan`, `errors`, `warnings`) |
| **TV4 (Evaluation / CLI — `run.py`, `eval`, `simulate`)** | `codebase.agent.answer(text)` | `text: str` | `{"output": str}` (khung `tracing.py` tự ghi `@model_call` & `@tool`) |
| **UI Projection an toàn (TV3)** | `codebase.application_contract.to_ui_response(envelope)` | Envelope từ `run_agent()` | JSON sạch cho UI (`html_omitted: true`, không trả HTML thô vào chat text) |

---

## 2. Thay đổi Contract & Bàn giao Contract Issue B cho TV3

### Contract Issue A — ĐÃ SỬA (PM TV1 phê duyệt, bản sửa lỗi nhất quán Contract)
- **File:** `codebase/application_contract.py` (dòng 157–166).
- **Thay đổi:** Cho phép `model=None` đối với Player có `inputs` (vd `Quiz ABCD bằng cử chỉ`) **CHỈ KHI** `interaction.primary == "mouse"`, `interaction.fallback == "mouse"` và `interaction.mouse_always_enabled is True` — đồng bộ với `spec.md` §4 (Mouse Fallback), `ailab/composer.py` (`mouse_only`) và Benchmark `B01, B16, B21, B27, B28`.
- **Giữ nguyên kiểm tra nghiêm ngặt:** Mọi chế độ yêu cầu camera (`primary != "mouse"`), tắt `mouse_always_enabled`, hoặc gắn `model != None` vào Player không nhận Model (`Vòng quay chọn tên`) vẫn bị từ chối tuyệt đối.
- **Workaround đã gỡ:** Đã xóa toàn bộ đoạn lọc lỗi tạm trong `codebase/agent.py`; cả `REUSE` và `GENERATE` đều đi qua `guardrails.validate_output_envelope(env, registry=...)` nghiêm ngặt 100%.

### Contract Issue B — BÀN GIAO TV3 XỬ LÝ (T12/T14, chưa tự sửa `ailab/composer.py`)
- **Nguyên nhân lỗi:** Contract v1.0 (`application_contract.py:155-156`) bắt buộc `exam=None` đối với Player dạng `texts` (`Vòng quay chọn tên` hoặc game `GENERATE` không câu hỏi), nhưng `ailab/composer.py:294-314` hiện ép `ed = raw.get("exam") or {}` → `exam_mode = "generate_new"` → báo lỗi `"exam.mode=generate_new cần nội dung bộ đề trong exam.content."`.
- **File & vị trí:** `ailab/composer.py` dòng 292–331 (`compose_app`).
- **Phương án tối thiểu cho TV3:**
  - Nếu `raw.get("exam") is None` và `app_player` không khai `questions == "exam"` / `content.kind == "questions"` (tức là player `texts`), gán `app_exam = None` và truyền `None` cho `validate_compatibility(...)`.
  - Nếu `app_player` yêu cầu `questions`/`exam` mà `raw.get("exam") is None`, báo lỗi rõ `"Player yêu cầu bộ đề câu hỏi (exam)."`.
- **Acceptance Criteria (cho TV3):**
  - `composer.compose_app()` trả `ok=True, status="draft", catalog_written=False` cho `ApplicationPlan` hợp lệ có `player_id=2` (`Vòng quay chọn tên`), `model=None`, `exam=None`.
  - Vẫn từ chối (`ok=False`) nếu `player_id=1` (`Quiz ABCD`) mà `exam=None`.
- **Regression Test cần thiết (TV3 thêm trong `ailab/test_composer.py`):**
  - Test `compose_app` cho `Vòng quay chọn tên` với `exam=None` (PASS) và `Quiz ABCD` với `exam=None` (FAIL).
- **Điều kiện gỡ bỏ nhánh bỏ qua trong `codebase/agent.py`:** Ngay sau khi TV3 hoàn tất & merge sửa lỗi `ailab/composer.py`, xóa điều kiện `and plan_exam is not None` tại `codebase/agent.py` (nhánh `REUSE` và `GENERATE`) để mọi plan đều chạy qua `tools.compose_application(plan)`. *(Lưu ý: luồng compose cho Player dạng `texts` với `exam=None` chưa được đánh dấu hoàn thành cho tới khi TV3 xử lý dependency này.)*

---

## 3. Kích hoạt Real AI Mode vs Mock Mode

### Real AI Mode (nhất quán với TV4 — `cost/personas.yaml`)
Tạo file `.env` cục bộ ở thư mục gốc repo (`.env` đã nằm trong `.gitignore:2`, **không bao giờ commit**):

```env
MODEL_PROVIDER=openai
MODEL_NAME=gpt-4o-mini
API_KEY=<dien-openai-api-key-cua-ban>
```

### Mock Mode (không cần API key, 0 chi phí)
- **T06 Deterministic Mock Contract:** `AGENT_MODE=t06_mock` + `MODEL_PROVIDER=fake` → `python run.py` trả JSON Contract giả (`simulated=true`).
- **Default Fake Mode:** không có `.env` (hoặc `MODEL_PROVIDER=fake`) → trả phản hồi giả, 0 token, không tạo DB.

---

## 4. Xử lý lỗi & Truy xuất Trace / Token Usage

- **Lỗi LLM (`ProviderError`):** `agent.py` không nuốt `ProviderError` (`auth/rate_limit/timeout/network/http/bad_response/usage_missing/config`) để `tracing.py` và `run.py eval` ghi trung thực vào cột `error`. Ở `ailab/server.py`, TV3 bắt `ProviderError` và trả HTTP 502/503 thân thiện.
- **Trace & Usage:**
  ```python
  import tracing
  from agent import run_agent

  tracing.begin("web-req-1")
  env = run_agent(payload)
  summary, events = tracing.end()
  # summary = {"model_calls", "tool_calls", "tokens_in", "tokens_out", "models", "errors"}
  ```
- **Các `@tool` chỉ-đọc đã đăng ký (không có tool tự `APPROVED` hay ghi Catalog):**
  `check_game`, `list_players`, `get_player`, `list_models`, `list_exams`, `get_exam`, `validate_exam`, `validate_compatibility`, `compose_application`.

---

## 5. Kết quả kiểm thử & Trạng thái Real AI Verification

| Kiểm tra | Kết quả |
|---|---|
| `python -m unittest discover -s codebase -p "test_*.py"` | **113/113 PASS** (25 T06 + 67 T07 + 21 T08/T09) |
| `python -m unittest discover -s ailab -p "test_*.py"` | **147/147 PASS** (0 regression) |
| `python codebase/accept_t06_entrypoint.py` | **2/2 PASS** |
| `python run.py check` | **PASS (0 cảnh báo)** — 30 câu, 6 metric |
| `python run.py eval --try` (Real AI `gpt-4o-mini`) | **CHƯA CHẠY (BLOCKED: chưa có `.env` cục bộ)** |

---

## 6. Việc TV3 & TV4 có thể làm ngay

- **TV3 (T14 — Web/Backend Integration):**
  1. Kéo nhánh `feat/t08-t09-ai-core-takeover` (hoặc review Draft PR).
  2. Nối `ailab/server.py` gọi `codebase.agent.run_agent(...)` và kiểm `validate_application_plan()` ở ranh giới Backend (nay đã đồng bộ hoàn toàn cho `model=None` Mouse Only).
  3. Xử lý Contract Issue B (`exam=None` cho Player `texts`) trong `ailab/composer.py` theo mục 2 ở trên.
  4. Bắt `ProviderError` trả HTTP 502/503, hiển thị cảnh báo `knowledge_review_required` trên UI, khóa cổng HITL (`HITL Bypass Count = 0`).
- **TV4 (T18 — Evaluation Run 1):**
  1. Đặt `.env` với `MODEL_PROVIDER=openai`, `MODEL_NAME=gpt-4o-mini`, `API_KEY=...`.
  2. Chạy `python run.py eval --try` (3 câu, `< $0.01`) để xác minh kết nối & trace token > 0.
  3. Sau khi PM xác nhận `eval --try` đạt, chạy `python run.py eval` (30 câu → `eval/run-1.csv` + `traces/run-1.jsonl`) và chấm điểm theo `eval/grading-sheet.md`.
- **Giới hạn đã biết:**
  - Guardrails là tập Rules deterministic đã qua unit/security tests (không tuyên bố an toàn tuyệt đối với mọi biến thể tấn công ngoài mẫu).
  - Chưa `Real AI Verified` trên LLM thật và chưa xác minh Web/Backend E2E (phụ thuộc `.env` và T14).
