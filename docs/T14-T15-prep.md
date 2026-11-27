# Chuẩn bị T14 / T15 (TV3) — trước khi T08/T09 xong

> Tài liệu **chuẩn bị**, không phải báo cáo hoàn thành. Cập nhật ngày 28/11/2026 từ `main @ f6e44cd`. Các ô `[ ]` vẫn chưa làm; không tự tick khi chưa có bằng chứng chạy thật. Không sửa `spec.md` §7 hay `eval/metric_spec.yaml`.

## 1. Trạng thái hiện tại

| Task | Trạng thái | Chặn bởi |
|---|---|---|
| T11 Repository foundation | DONE | — |
| T12 Catalog, Tools & Composition | DONE | — |
| T13 Game Runtime (`evidence/runtime-smoke.md`) | DONE | — |
| **T14 Web/Backend Integration & HITL** | TODO — deadline 08:30 | T06 ✅ · T12 ✅ · T13 ✅ · **T08 ❌ (TV2)** |
| **T15 E2E Testing & Demo Recording** | TODO — video 09:30 / backup 12:00 | T07 ✅ · **T08 ❌** · **T14 ❌** · CP4 thêm **T09 ❌** |

`codebase/agent.py` hiện vẫn luồng cũ (chỉ có nhánh thử `AGENT_MODE=t06_mock`), chưa có Shared Core Web/CLI. `docs/TASKS_P1.md` xếp toàn bộ P1 vào trạng thái `BLOCKED` cho tới khi T14 xong — không làm P1 trước P0.

## 2. Việc làm ngay được (không cần T08)

### 2.1 Merge nhánh UI — cẩn thận docs freeze

- [ ] Merge `origin/feat/ui-ux-refactor` (`e399a66`). Nhánh này chỉ refactor frontend (`ailab/web/app.js`, `js/*.js`, `style.css`, `play.html/js`) nhưng **diff có kèm bản cũ** của `cost/cost-estimate.md`, `cost/personas.yaml`, `data/DATA_CARD.md`, `docs/TASKS.md`, `evidence/summary.md`, `evidence/survey/*`, `spec.md`.
- [ ] Khi resolve conflict: **giữ bản `main`** cho toàn bộ file docs/`spec.md` (có freeze TV1 `8be7d5f`, kiểm chứng simulate `b4b288b`, survey `2ab8bd3`, `TASKS_P1.md` `f6e44cd`). Chỉ lấy code frontend từ nhánh UI.
- [ ] Sau merge: `python run.py check` vẫn pass (30 câu, 6 metric) và `git diff` không cho thấy `spec.md` §7 / `eval/metric_spec.yaml` thay đổi.

### 2.2 Backend HITL — phần còn thiếu (đã rõ trong code)

Điểm mạnh có sẵn, **không làm lại**:
- `ailab/store.py:76`: DB đã có `status IN ('draft','pending','approved','refused','hidden')`.
- `ailab/server.py:354-361`: `submit` chỉ từ `draft`/`refused` → `pending`; `withdraw` → `draft`.
- `ailab/server.py:366-367`: chỉ player `approved` mới đổi `visibility=public`.
- `ailab/server.py:369-379`: `approve`/`refuse`/`hide`/`restore` đã có `_need_admin(user)`; `refuse` bắt buộc note 1–300 ký tự.
- `ailab/store.py:314-317`: sửa nội dung sau `approved`/`refused` tự quay về `pending`.
- `codebase/application_contract.py:72`: `validate_application_plan(plan, registry)` trả danh sách issue; đường sinh HTML đã gọi `check_game()` (`:105`).

Chỗ trống cần làm ở T14:
- [ ] Gọi `validate_application_plan()` ở ranh giới `ailab/server.py` trước khi lưu/duyệt bất kỳ `ApplicationPlan` nào; từ chối HTTP 400 nếu có issue, 403 nếu client gửi `status`/`approval` tự đặt.
- [ ] Ánh xạ rõ hai hệ trạng thái: contract dùng `pending_approval` / `needs_clarification` / `error` (`application_contract.py:22-23`), DB dùng `draft/pending/approved/refused`. Quy ước đề xuất: AI chỉ được sinh `DRAFT` (+ `pending_approval`); `APPROVED` và `REJECTED` chỉ do Admin/giáo viên qua endpoint có `_need_admin`. Không cho phép payload từ AI nhảy thẳng `APPROVED`.
- [ ] Thêm test API chống bypass: AI/ user thường gửi `status=approved`, `visibility=public`, hoặc cố publish khi `draft`/`refused` → phải bị từ chối; sửa nội dung sau duyệt → quay `pending`. Mục tiêu `HITL Bypass Count = 0` (chuẩn đã ký).
- [ ] Hiển thị cảnh báo bắt buộc kiểm duyệt kiến thức cho bộ đề AI sinh (`M5` trong `eval/grading-sheet.md`) ngay trên UI, không chỉ trong output chat.

### 2.3 UI & adapter (dùng Mock Plan T06 trước)

- [ ] Hiển thị quyết định `REUSE` / `GENERATE` / `ASK_CLARIFY` / `REFUSE`, nội dung `ApplicationPlan`, danh sách câu hỏi kèm cảnh báo kiểm duyệt, khung Preview `iframe sandbox` — dùng Mock Plan v1.0 của nhánh UI + `AGENT_MODE=t06_mock`.
- [ ] Dựng sẵn adapter `ailab/server.py` → `codebase/agent.py` (`answer(text) -> {"output": str}`) nhưng **chưa bật**; chỉ đổi nguồn sang Shared Core sau T08.
- [ ] Đảm bảo một đường tích hợp duy nhất qua `ailab/server.py` (không chạy song song `chatbot_server.py`) — đúng gate G2 trong `docs/TASKS_P1.md:59`.

### 2.4 T15 — phần không cần output AI

- [ ] Chạy `python -m unittest discover -s ailab -p "test_*.py"` (đang 37/37) và `ailab/smoke.sh`; ghi kết quả thật.
- [ ] Test cài đặt từ thư mục sạch theo `README.md` (mục tiêu ≤3 phút).
- [ ] Soạn test case E2E: `REUSE` E2E · `GENERATE` nháp + `check_game` · HITL chống bypass · `Mouse Fallback` (tắt camera) · 1 ca `ASK_CLARIFY`/`REFUSE`.
- [ ] Tách bằng chứng **static** (`check_game`, `validate_application_plan`, `parse_questions`) với **runtime** (mở trình duyệt chơi được, tắt camera vẫn chơi). Static đã có; runtime có `evidence/runtime-smoke.md` cho T13.
- [ ] Chuẩn bị script quay + chỗ đăng video YouTube "Không công khai" / Drive "Bất kỳ ai có đường liên kết"; checklist mở cửa sổ ẩn danh. **Chưa quay video 30s Real AI** — phải đợi T08 + T14.

## 3. Chờ task khác (không làm trước)

| Việc | Chờ |
|---|---|
| Nối lõi thật `codebase/agent.py` → Web/CLI | **T08** |
| Video 30s Real AI hợp lệ (trước 09:30) | **T08 + T14** |
| Video dự phòng CP4 (trước 12:00) | **T09** (+ T14) |

## 4. Liên kết kiểm chứng

- Phiếu chấm / hash đầu vào (giữ nguyên qua Run 1 → Run 2): `eval/grading-sheet.md`.
- Freeze đã ký TV1 28/11 00:50: `spec.md` §9 nhật ký, đồng bộ tại `eval/README.md` mục 3 (`≥24/30`, Refusal 100%, HITL 0).
- Bằng chứng runtime T13: `evidence/runtime-smoke.md`.
- Cập nhật khung này với số/Run ID thật sau khi T08/T09/T14 xong — không viết kết quả giả vào đây.
