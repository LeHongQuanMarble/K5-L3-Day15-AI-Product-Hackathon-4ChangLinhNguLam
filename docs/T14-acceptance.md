# T14 — Product Acceptance Checklist (Web/Backend Integration, HITL & Persistence)

> **Owner nghiệm thu:** TV1 (PM & Product Lead) · **Owner triển khai:** TV3 (Software & Integration Engineer; TV4 hỗ trợ Backend `573df0e`).  
> **Cơ sở đối chiếu:** `origin/main @ 3227932` (cập nhật 28/11/2026 02:30 UTC+7), `docs/T14-integration.md`, `ailab/server.py`, `ailab/agent_bridge.py`, `ailab/web/js/views-assistant.js`.  
> **Nguyên tắc:** Không đánh dấu T14 `DONE` chỉ vì Backend API hoặc Unit Test đã PASS. Mọi tiêu chí phải xác minh thực tế từ UI → Backend → SQLite → Game Runtime.

## Tổng quan trạng thái nghiệm thu T14

- **Backend Shared Core & HITL API (`ailab/agent_bridge.py`, `ailab/server.py`, `ailab/llm.py`):** `INTEGRATION_VERIFIED` (10/10 unit tests `test_agent_bridge.py`, HTTP Real AI test trong `docs/T14-integration.md`).
- **Frontend Integration (`ailab/web/js/views-assistant.js`) & Application Persistence (SQLite `apps`):** `NOT_READY / FAIL` — `git grep "/api/agent" origin/main -- ailab/web/` trả **0 kết quả**; chế độ Real trên UI vẫn gọi legacy `POST /api/chat`, `hitlBar()` chỉ render chip tĩnh `HITL 1 — chờ nối API duyệt (T08/T14)` (chưa có nút duyệt thật), và `POST /api/agent/publish` chưa lưu bản App `approved` vào SQLite (`apps`) để mở `/play/<app_id>`.
- **Kết luận nghiệm thu hiện tại:** **CHƯA ĐẠT (`IN_PROGRESS`)** — chặn luồng E2E Web thật và Video 30s Real AI (`T15`).

---

## 1. Frontend Integration

| ID | Acceptance Criteria | Expected Result | Verification Method | Evidence Required | Actual Result (28/11 02:30) | Status |
|---|---|---|---|---|---|---|
| T14-FE-01 | Real Mode gọi đúng Backend API (`/api/agent`, `/api/agent/publish`, `/api/agent/review`) | Gửi prompt ở Real Mode gọi `POST /api/agent` (không phải chỉ legacy `/api/chat`) | Inspect `ailab/web/js/views-assistant.js` + DevTools Network | Screenshot Network `POST /api/agent` HTTP 200 | `views-assistant.js` có **0 lệnh gọi `/api/agent`**; chỉ gọi `POST /api/chat` | **FAIL** |
| T14-FE-02 | Hiển thị `ApplicationPlan` thật từ Backend | Render badge quyết định (`REUSE`/`GENERATE`/`ASK_CLARIFY`/`REFUSE`), tên ứng dụng, Model, Player, Question Set & cảnh báo `knowledge_review_required` | Chạy `python ailab/server.py` (`.env` thật) + gửi prompt `B01`/`B16` | Ảnh chụp thẻ `ApplicationPlan` từ dữ liệu thật (`simulated=false`) | Chưa nối `/api/agent` vào UI card; mới hiển thị ở chế độ Mock | **FAIL** |
| T14-FE-03 | `REUSE` hoạt động không phụ thuộc HTML do LLM sinh | Backend trả `player.mode="reuse_existing"`, `html_omitted=true`; UI vẫn render thẻ duyệt + nút mở game | Gửi `B16` ở Real Mode | Network JSON (`html_omitted: true`) + UI hiển thị thẻ REUSE | Qua `/api/chat` legacy, `REUSE` trả `html=None` nên UI chỉ hiện text, không có thẻ duyệt | **FAIL** |
| T14-FE-04 | `GENERATE` hiển thị Draft phù hợp trong sandbox | Render thẻ `DRAFT`, cờ `check_game`, khung xem thử `iframe sandbox="allow-scripts"` | Gửi `B13` ở Real Mode | Ảnh chụp Preview sandbox + 0 lỗi console | Chưa xác minh qua `/api/agent` trên UI | **PENDING** |
| T14-FE-05 | `ASK_CLARIFY` và `REFUSE` hiển thị đúng | `ASK_CLARIFY` hiện đúng 1 câu hỏi không có thẻ duyệt; `REFUSE` hiện lý do từ chối + nút publish bị khóa | Gửi `B05` và `B17` ở Real Mode | Ảnh chụp 2 màn hình phản hồi | Chưa xác minh qua `/api/agent` trên UI | **PENDING** |
| T14-FE-06 | Không dùng Mock Adapter ngầm trong Real Mode | Ở Real Mode không gọi `runMockComposer` / `MOCK_PRESETS`; nếu có chế độ Mock phải tách rõ bằng banner cảnh báo | Kiểm tra `views-assistant.js` + thử ngắt API | Kết quả review code + screenshot lỗi khi tắt server | Đã tách chế độ `'real'` mặc định và `'mock'` có banner `.ail-banner-mock` | **PASS (Static)** |
| T14-FE-07 | Trạng thái loading và error phù hợp | Khóa nút gửi khi đang gọi AI; lỗi 502/503 hiển thị thông báo thân thiện, giữ nguyên nội dung user đã nhập, có nút Thử lại | Ngắt mạng / cấu hình lỗi provider + gửi prompt | Screenshot trạng thái loading & error | Cơ chế loading/error đã có cho `/api/chat`; cần xác minh lại sau khi nối `/api/agent` | **PENDING** |

---

## 2. Human-in-the-Loop (HITL)

| ID | Acceptance Criteria | Expected Result | Verification Method | Evidence Required | Actual Result (28/11 02:30) | Status |
|---|---|---|---|---|---|---|
| T14-HITL-01 | Giáo viên xem và phê duyệt Application Draft trên UI | Nút Phê duyệt / Từ chối / Chỉnh sửa hoạt động ở Real Mode, gọi `POST /api/agent/publish` hoặc `/api/agent/review` | Thao tác duyệt trên trình duyệt thật | Video/ảnh bấm Phê duyệt → HTTP 200 | `hitlBar()` ở Real Mode chỉ render chip trạng thái tĩnh (`HITL 1 — chờ nối API duyệt`), chưa có nút gọi `/api/agent/publish` | **FAIL** |
| T14-HITL-02 | Không cho phép bypass HITL (`HITL Bypass Count = 0`) | Gửi `status=APPROVED` từ AI/client → HTTP 400; gọi publish không có `approved=true` hoặc khi `draft`/`rejected`/`REFUSE` → HTTP 403 | Unit test `test_agent_bridge.py` + HTTP test thực tế | Log HTTP 400/403 (`docs/T14-integration.md` mục 3) | Backend đã xác minh 400/403, `bypass_count=0`, 10/10 `test_agent_bridge.py` PASS | **PASS (Backend)** |
| T14-HITL-03 | Backend kiểm tra lại Contract & sửa sau duyệt quay về `DRAFT` | `POST /api/agent/publish` chạy lại `validate_application_plan()`; đổi `name`/bộ đề sau duyệt (`POST /api/agent/review`) → `status="draft"`, `can_publish=false` | Unit test + HTTP test `plan_hash` | Log `docs/T14-integration.md` mục 3 | Đã xác minh ở Backend API (`plan_hash`) | **PASS (Backend)** |
| T14-HITL-04 | Cảnh báo kiểm duyệt kiến thức bắt buộc cho bộ đề AI sinh | Mọi bộ đề AI sinh hiển thị rõ cảnh báo `knowledge_review_required` trước khi cho bấm duyệt | Gửi `B14` ở Real Mode | Screenshot UI hiển thị cảnh báo kiểm duyệt | Backend trả `knowledge_review_required`; cần xác minh hiển thị trên Real UI | **PENDING** |

---

## 3. Application Persistence

| ID | Acceptance Criteria | Expected Result | Verification Method | Evidence Required | Actual Result (28/11 02:30) | Status |
|---|---|---|---|---|---|---|
| T14-DB-01 | Application đã duyệt được lưu vào SQLite (`apps` table) | `POST /api/agent/publish` (khi `approved=true` và hợp lệ) ghi bản ghi vào bảng `apps` (và `exams`/`players` nháp nếu cần) | Kiểm tra SQLite DB + response JSON | Response chứa `app_id` (số nguyên > 0) | `docs/T14-integration.md` mục 7 xác nhận server **chưa lưu vào DB**, chỉ trả `plan_hash` | **FAIL** |
| T14-DB-02 | Backend trả `app_id` hợp lệ & xuất hiện trong danh sách quản lý | Sau duyệt, App hiện trong tab "Ứng dụng" (`GET /api/apps`) | Chuyển sang tab Ứng dụng sau khi duyệt | Screenshot App mới trong danh sách | Chưa có do T14-DB-01 chưa triển khai | **FAIL** |
| T14-DB-03 | Reload trang không làm mất Application đã lưu | F5 / mở lại trình duyệt vẫn thấy App trong danh sách | Reload trình duyệt + kiểm `GET /api/apps` | Screenshot sau F5 | Chưa có do T14-DB-01 chưa triển khai | **FAIL** |
| T14-DB-04 | Mở `/play/<app_id>` thành công từ luồng duyệt | Bấm *"Mở chơi ngay"* mở trang `/play/<app_id>` không lỗi 404/500 | Bấm nút chơi sau khi duyệt | Screenshot trang `/play/<app_id>` đang chạy | Chưa nối 1-click từ `/api/agent/publish` | **FAIL** |

---

## 4. Game Runtime

| ID | Acceptance Criteria | Expected Result | Verification Method | Evidence Required | Actual Result (28/11 02:30) | Status |
|---|---|---|---|---|---|---|
| T14-RT-01 | Trò chơi hiển thị đúng nội dung & Question Set động | Player nhận đúng bộ câu hỏi đã chọn/sinh, không hardcode | Chơi thử trên trình duyệt thật | `evidence/runtime-smoke.md` + ảnh chơi thật từ App mới duyệt | Độc lập đã PASS (`evidence/runtime-smoke.md`: 2/2 Player động); cần xác minh E2E từ App tạo qua AI | **PARTIAL** |
| T14-RT-02 | `Mouse Fallback` hoạt động trọn vẹn | Chơi hết lượt bằng chuột không mất điểm trong 6 tình huống lỗi/tắt camera | Edge headless smoke + test tay trình duyệt | `evidence/runtime-smoke.md` (6/6 PASS `2/2`) | Đã xác minh ở T13 (`evidence/runtime-smoke.md`) | **PASS (Runtime)** |
| T14-RT-03 | Camera/Gesture Interaction tương thích (nếu phù hợp P0) | Khi chọn Model tương thích + có camera thì nhận tín hiệu; khi không tương thích (`Quiz ABCD` thiếu `kinds: hands`) Rules báo rõ | Kiểm tra `validate_compatibility` + trình duyệt | Test `B02`/`B15` + kiểm tra thực tế | Rules chặn không tương thích đã PASS; chưa kiểm webcam vật lý (ghi rõ giới hạn) | **PARTIAL** |
| T14-RT-04 | `iframe sandbox` & CSP hoạt động theo thiết kế | Chặn `fetch`, `parent.document`, `window.top.location`, `cookie` | Edge headless smoke | `evidence/runtime-smoke.md` (4/4 blocked) | Đã xác minh ở T13 (`evidence/runtime-smoke.md`) | **PASS (Runtime)** |

---

## 5. Observability

| ID | Acceptance Criteria | Expected Result | Verification Method | Evidence Required | Actual Result (28/11 02:30) | Status |
|---|---|---|---|---|---|---|
| T14-OBS-01 | Trace & Token usage được ghi nhận đầy đủ | Response `/api/agent` và `traces/` ghi `model_calls`, `tool_calls`, `tokens_in > 0`, `tokens_out > 0`, `models` | Gọi `POST /api/agent` với Real AI | `docs/T14-integration.md` (`tokens_in=1777`, `tokens_out=152`, `gpt-4o-mini`) | Đã xác minh ở Backend API | **PASS (Backend)** |
| T14-OBS-02 | Provider & Error handling an toàn (0 lộ key) | `ProviderError` ánh xạ HTTP 502/503; không lộ `API_KEY` hay raw body | `ailab/test_agent_bridge.py` | 10/10 unit tests PASS | Đã xác minh ở Backend API | **PASS (Backend)** |

---

## Điều kiện đóng T14 sang `DONE`

TV3 cần hoàn tất và bàn giao bằng chứng cho **4 nhóm việc khắc phục 8 tiêu chí đang `FAIL` (`T14-FE-01..03`, `T14-HITL-01`, `T14-DB-01..04`)**:
1. Nối `ailab/web/js/views-assistant.js` (Real Mode) gọi `POST /api/agent`, hiển thị thẻ `ApplicationPlan` thật (kể cả nhánh `REUSE` có `html_omitted=true`) và cảnh báo kiểm duyệt kiến thức.
2. Nối nút Phê duyệt / Từ chối / Chỉnh sửa trên Real UI tới `POST /api/agent/publish` và `POST /api/agent/review`.
3. Cho `POST /api/agent/publish` lưu bản App `approved` vào bảng SQLite `apps` và trả `app_id` để reload không mất và mở thẳng `/play/<app_id>`.
4. TV3 ký review chéo `573df0e` + gửi ảnh/video chạy E2E thật qua TV1 nghiệm thu.
