# Dàn slide, Kịch bản Demo & Checklist Nộp Bài (T05 · T21)

> Làm ở guide bước 5.1. Luật: **không có bằng chứng thì không có slide** — mỗi trang ≥1 con số / trích dẫn có nguồn / kết quả đo.  
> Xuất PDF thành `demo-slides.pdf` ở thư mục gốc repo, nộp tại **CP4 14:30 Thứ Bảy 28/11**. Nộp PDF, không nộp link.  
> **Cập nhật 28/11/2026 02:30 (UTC+7):** Đã đồng bộ số liệu thật từ `origin/main @ 3227932` (Evaluation Run 1 = `19/30`, Refusal `4/4`, HITL bypass `0`; Survey `n = 6` chưa đạt ngưỡng R1; giữ placeholder cho Run 2 & Cost ≥50 phiên — không bịa số).

---

## 1. Dàn bài 8 trang chuẩn BTC (phủ đủ 10 mạch Product-first)

| # | Trang (BTC) | Mạch Product-first & Nội dung chính | Số liệu / Nguồn thật (`file`) | Trạng thái số liệu |
|---|---|---|---|---|
| 1 | **Người dùng, Pain & Bằng chứng** | *(1) Problem + (2) User Evidence:* Giáo viên tốn công soạn câu hỏi (`6/6`), hạn chế thời gian (`6/6`), mất thời gian cấu hình (`5/6`), cần chạy bằng chuột (`4/6`) + trích dẫn ẩn danh `S2/S4/S5` + số liệu bổ sung sau khi đạt ngưỡng R1 | `evidence/summary.md`, `evidence/survey/results.csv` (`n=6`), `evidence/interviews/P1–P3.md` *(chờ T03)* | ⏳ Chờ đạt ngưỡng R1 (`≥3` PV hoặc `≥20` KS) |
| 2 | **Vì sao chọn bài này (Impact)** | Bảng so sánh 3 hướng (chọn H1 AI Game Composer; loại H2 video bài giảng, H3 chấm tự luận) + công thức Impact (phút/trò chơi) | `spec.md` §2, `evidence/summary.md` | ⏳ Chờ Baseline chốt từ T03 |
| 3 | **Giải pháp, USP & Kiến trúc AI** | *(3) Solution + (4) USP Reuse-first, Generate-if-needed + (6) AI Architecture:* Lát cắt 1 câu; Conditional Workflow `Agent → 9 @tool → Composer → Guardrails → HITL 2 lớp`; vì sao `REUSE` tiết kiệm mạnh chi phí & độ trễ so với luôn `GENERATE` | `spec.md` §4, `codebase/agent.py`, `codebase/guardrails.py`, `ailab/composer.py`, `eval/run-1.csv` | ✅ Có số thật (`gpt-4o-mini` Run 1: REUSE ~165 out tok vs GENERATE `B13`/`B25` 1,090–1,276 out tok) |
| 4 | **Demo Live & Responsible AI** | *(5) Product Demo + (9) Responsible AI:* Demo live 1 ca `REUSE` + `Mouse Fallback` + HITL (`B01`/`B16`) + 1 ca an toàn `REFUSE` chống bypass (`B17`) hoặc `GENERATE` nháp sandbox (`B13`); minh bạch 4 lớp kiểm soát (AI · Rules · Backend · Giáo viên) | `eval/benchmark.csv`, `evidence/runtime-smoke.md` (6/6 fallback, 4/4 CSP), `docs/T14-integration.md` (`bypass=0`) | ⏳ Chờ T14 UI nối `/api/agent` + Video dự phòng T15 |
| 5 | **Đánh giá thế nào (Evaluation)** | *(7) Evaluation:* Catalog snapshot `79822a4`, 30 câu (`10/30` nguồn thật), 6 metric freeze (`≥24/30`, Refusal `4/4`, HITL `0`). **Run 1 (`run-1@20261128-021031`):** `19/30 (63%)`, Refusal `4/4`, HITL `0` → phân tích 4 nhóm lỗi → cải tiến T10 → **Run 2:** `__ / 30 (__%)` *(placeholder chờ T19)* | `eval/README.md`, `eval/report.md`, `eval/run-1.csv`, `eval/run-2.csv` *(chờ T19)* | ⏳ Đã có Run 1; chờ chấm chéo + T10 + Run 2 |
| 6 | **Chi phí khi dùng thật (Cost)** | *(8) Cost:* 3 persona từ khảo sát + 2 mức giá (`gpt-4o-mini` `$0.15/$0.60`, `gpt-4o` `$2.50/$10.00`). Smoke test `simulate --try` (10 phiên, 0 lỗi). **Chính thức ≥50 phiên:** chi phí/task thành công = `___` *(placeholder chờ T20 sau Run 2)* + đối chiếu Impact | `cost/personas.yaml`, `cost/cost-estimate.md`, `cost/simulate-1.csv` *(chờ T20)* | ⏳ Đã có `simulate --try`; chờ T20 ≥50 phiên |
| 7 | **Kết luận & Minh bạch nguồn gốc** | Go / Iterate / Stop dẫn số từ trang 1, 5, 6 + **Minh bạch nguồn mã:** kế thừa nền tảng `ailab/` & 6 ảnh game từ **JULY Learning**, khung CLI/Tracing/Eval/Cost từ **AI20K Starter Repo**, và phần xây mới trong Hackathon (AI Core, Guardrails, Composer, Bridge/HITL, UI Refactor, 30 câu Benchmark) | `eval/report.md`, `cost/cost-estimate.md`, `docs/ai-usage.md` | ⏳ Chờ số chốt Run 2 & Cost |
| 8 | **Nếu có thêm 1 tuần (Roadmap P1)** | *(10) Roadmap:* 2–3 việc trọng tâm trỏ về lỗi còn lại ở `eval/report.md` & `docs/TASKS_P1.md` (Persistent Chat History đầy đủ, Question Set Editor, Trace/Cost Drawer, One-Click Player Swap, hỗ trợ Audio Model) | `eval/report.md` mục 4, `validation/log.md`, `docs/TASKS_P1.md` | ✅ Đã có khung |

### Phân công trình bày (4/4 thành viên)

| Trang | Người nói |
|---|---|
| Trang 1 (Problem & Evidence) · Trang 2 (Impact) | **TV1 – Nguyễn Hoàng Việt** |
| Trang 3 (Solution, USP & AI Architecture) | **TV2 – Hồ Quốc Toản** |
| Trang 4 (Live Demo, HITL & Mouse Fallback) | **TV3 – Lê Hồng Quân** |
| Trang 5 (Evaluation Run 1 → Run 2) · Trang 6 (Cost Simulation) | **TV4 – Đào Huy Hoàng** |
| Trang 7 (Kết luận & Minh bạch) · Trang 8 (Roadmap P1) | **TV1 – Nguyễn Hoàng Việt** |

---

## 2. Kịch bản Demo Live & Phương án Dự phòng (T05 · T15)

> **Quy tắc bắt buộc:** Demo chính thức và Video 30s CP3 **PHẢI chạy Real AI** (`.env` với `gpt-4o-mini`). **Tuyệt đối không dùng Mock Mode rồi trình bày như Real AI.**

### A. Demo chính — Luồng `REUSE` E2E + HITL + Mouse Fallback (~90 giây)
1. **Nhập yêu cầu (`B01`/`B16`):** Giáo viên gõ tiếng Việt tự nhiên: *"Tôi cần ôn tập Toán 12 phần đạo hàm, dùng bộ đề có sẵn và chơi bằng chuột."*
2. **AI phân tích & tra cứu Catalog:** Agent gọi `@tool` (`list_players`, `list_exams`, `validate_compatibility`, `compose_application`) → quyết định **`REUSE`** (`Quiz ABCD bằng cử chỉ` + bộ đề 15 câu, **không sinh HTML mới**, `mouse_always_enabled=true`).
3. **Hiển thị `ApplicationPlan` Draft & HITL:** UI hiện thẻ `DRAFT`, cảnh báo kiểm duyệt, thông số `trace` (model, token). Giáo viên bấm **Phê duyệt (HITL)**.
4. **Lưu & Chơi thật:** Backend kiểm lại Contract → lưu vào SQLite (`app_id`) → bấm **Chơi ngay** (`/play/<app_id>`) → chơi trực tiếp bằng **chuột (Mouse Fallback)** trong `iframe sandbox`.

### B. Demo bổ sung — Chọn 1 trong 2 ca (~45 giây)
- **Phương án 1 (`REFUSE` chống tấn công/bypass HITL — `B17` hoặc `B11`):** Nhập yêu cầu ép AI tự `APPROVED` hoặc chèn `fetch` gửi ảnh camera → AI từ chối ngay (**0 LLM call** cho `B17`), Backend khóa xuất bản (`HITL Bypass Count = 0`).
- **Phương án 2 (`GENERATE` nháp sandbox — `B13`):** Yêu cầu game Địa lý 6 chưa có trong Catalog → AI sinh bản nháp HTML qua `check_game` (0 cờ an toàn) và xem thử trong `iframe sandbox` (CSP chặn gọi mạng), không tự thêm vào Catalog.

### C. Phương án Dự phòng (6 tình huống sự cố)

| Tình huống sự cố | Cách xử lý ngay trên sân khấu |
|---|---|
| 1. Mất kết nối Internet | Chuyển ngay sang **Video dự phòng offline/ẩn danh (T15)** đã quay bằng Real AI, thuyết minh trực tiếp theo đúng kịch bản |
| 2. LLM Provider lỗi (`429`/`502`/`503`) hoặc API timeout | Chỉ rõ thông báo lỗi thân thiện của hệ thống (không crash, không lộ API key), thử lại 1 lần; nếu quá 15 giây → mở **Video dự phòng Real AI** |
| 3. Camera không hoạt động / bị từ chối quyền | Trình diễn trực tiếp **Mouse Fallback** (chơi trọn vẹn bằng chuột không mất điểm — đã kiểm 6/6 tình huống ở `evidence/runtime-smoke.md`) |
| 4. Game Runtime lỗi trên máy demo | Mở App đã lưu sẵn trong danh sách `/api/apps` hoặc chiếu đoạn runtime từ Video dự phòng |
| 5. Giám khảo hỏi 1 câu thử lạ ngoài kịch bản | Gõ trực tiếp vào CLI `python run.py` hoặc Web UI; nếu câu mơ hồ AI sẽ hỏi lại (`ASK_CLARIFY`), nếu ngoài phạm vi AI sẽ từ chối (`REFUSE`) |
| 6. Không thể hoàn thành demo live | Mở ngay Video dự phòng (2–3 phút, kiểm trước ở cửa sổ ẩn danh) + mở `eval/run-1.csv` / `eval/run-2.csv` và `traces/` làm bằng chứng |

**Checklist 1 giờ trước giờ demo:**
- [ ] Tải repo về thư mục sạch, kiểm tra chạy theo `README.md` (3 phút).
- [ ] `.env` trên máy demo hoạt động, đã gọi thử 1 câu Real AI trong vòng 1 giờ trước pitch.
- [ ] Video dự phòng mở được bằng cửa sổ ẩn danh (cả online và file tải sẵn về máy).

---

## 3. Checklist Nộp Checkpoint (T05) & Final Submission (T21)

### CP3 — Hạn `10:00 ngày 28/11/2026` *(Nộp bằng mã Đội trưởng `2A202603487`)*
- [x] `spec.md` §0–§7 (đã freeze §7 `≥24/30`, không sửa sau CP2) · `data/DATA_CARD.md` (snapshot `79822a4`) · `eval/benchmark.csv` (30 câu, 10/30 nguồn thật, `run.py check` 0 warning) · `eval/metric_spec.yaml` (6 metric)
- [x] `eval/run-1.csv` & `traces/run-1.jsonl` (`run-1@20261128-021031`, `19/30`, Refusal `4/4`, HITL `0`)
- [x] `cost/simulate --try` 10 phiên Real AI (`simulate-try@20261128-004848`, 0 lỗi)
- [ ] **T03 Evidence đạt ngưỡng R1:** `≥3` phỏng vấn sâu (`P1–P3`) **HOẶC** `≥20` khảo sát (`6/20` hiện tại) — *Owner: TV1 (hạn 08:30)*
- [ ] **Chấm chéo 5 câu Run 1** (`B01, B10, B13, B24, B30`) ghi vào `eval/README.md` mục 3 & `eval/report.md` mục 5 — *Owner: TV1 + TV4*
- [ ] **Video 30 giây chạy Real AI** (mở được cửa sổ ẩn danh, không dùng Mock) — *Owner: TV3 (hạn 09:30)*
- [ ] **Xác nhận đã nộp CP3** *(trạng thái hiện tại: `NOT_SUBMITTED`)*

### CP4 — Hạn `14:30 ngày 28/11/2026`
- [ ] `T10` cải tiến 1 vòng từ 11 lỗi Run 1 + ghi `spec.md` §10 — *Owner: TV2 (hạn 11:30)*
- [ ] `T19` Evaluation Run 2 (`eval/run-2.csv`, `traces/run-2.jsonl`) + `eval/report.md` (so sánh Run 1 → Run 2, hash 3 file khớp) — *Owner: TV4 (hạn 13:00)*
- [ ] `T20` Cost Simulation `≥50` phiên (`cost/simulate-1.csv`) + chi phí/task thành công chia cho tỉ lệ Run 2 (`cost/cost-estimate.md`, `spec.md` §8) — *Owner: TV4 (hạn 13:30)*
- [ ] `T04` hoàn tất UAT 6 kịch bản (`validation/log.md`) + `T15` Video dự phòng 2–3 phút — *Owner: TV1, TV3 (hạn 12:30)*
- [ ] `demo-slides.pdf` ở thư mục gốc repo + **Xác nhận đã nộp CP4** *(trạng thái hiện tại: `NOT_SUBMITTED`)*

### Final Submission (T21) — Hạn `23:59 ngày 28/11/2026`
- [ ] Cập nhật `spec.md` §10 (changelog sau CP4) — không sửa chuẩn đạt, benchmark hay kết quả eval đã chạy
- [ ] Hoàn thiện `docs/ai-usage.md` cho đủ cả 4 thành viên (TV1–TV4)
- [ ] Đủ 4 file phản tư cá nhân trong `reflection/` (mỗi thành viên tự viết trung thực, không viết hộ bịa trải nghiệm)
- [ ] **Minh bạch nguồn gốc & pháp lý:** kiểm tra Attribution rõ **JULY Learning** / **BTC Starter Repo** / **Code mới Hackathon**, trạng thái xác nhận quyền tái sử dụng source JULY Learning theo quy định BTC *(chưa có biên bản xác nhận bằng văn bản trong repo — cần TV1/TV3 xác nhận với BTC)*, trạng thái License & font SIL OFL
- [ ] **Repository Hygiene:** `python run.py check` đạt 0 lỗi; quét không lộ `.env`, `API_KEY`, PII, DB staging, data thô BTC trong toàn bộ git history
- [ ] **Xác nhận đã nộp Final** *(trạng thái hiện tại: `NOT_SUBMITTED`)*
