# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ câu thử, cùng cách chấm. Chấm ở rubric R5.
> Số lấy từ `python run.py score eval/run-1.csv` (và `run-2.csv`) sau khi điền cột `pass`. **Kết quả thấp ghi thật vẫn đủ điểm.**
> Không được: sửa chuẩn "đạt", bỏ câu thử trượt, sửa `expected` cho khớp output, sửa kết quả lượt đã chạy.
> **Chuẩn TV1 ký 28/11 00:50 (`spec.md` §9):** `≥24/30`, `tu_choi` `4/4`, HITL bypass `0`. Phiếu chấm 30 câu / 6 metric tại `eval/grading-sheet.md`.

## 0. Khóa đầu vào — đối soát Run 1 = Run 2 *(AC T19)*

| File | Run 1 | Run 2 | Khớp? |
|---|---|---|---|
| `eval/benchmark.csv` (30 câu) | sha256 `0236f1…c82c76` | sha256 `0236f1…c82c76` | **CÓ** |
| `eval/metric_spec.yaml` (6 metric) | sha256 `435d21…bfe4dc` | sha256 `435d21…bfe4dc` | **CÓ** |
| `data/catalog_snapshot.json` (`79822a4`) | sha256 `b3e681…9743bb` | sha256 `b3e681…9743bb` | **CÓ** |

Hash đầy đủ và lệnh lấy lại: xem đầu `eval/grading-sheet.md`. **Không đổi 3 file này giữa hai lượt**; nếu lệch thì dừng và báo TV1, không chấm tiếp. Đã kiểm lại ngay trước Run 1, trước Run 2 (khi T10 vừa merge) và **sau khi chạy xong Run 2**: cả 3 hash vẫn khớp bản khóa `0236f1f7f2c412fb1f6260af7c5156f8dce6294ec2f15de6d4265b11c4a82c76` / `435d21ed7f6774fc45dbf39cbf55fe1e24d41d79f87750100641c5c1ffbfe4dc` / `b3e68193d9d04faf1db48254254b952d3aaeb40520d81286eded4901519743bb`. Không sửa `expected`, không bỏ câu trượt, không đổi chuẩn §7.

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | `run-1@20261128-021031` | **19/30** | **63%** | 7/11 (64%) | 8/15 (53%) | **4/4 (100%)** | **chưa** (thiếu 5 câu) |
| 2 | `run-2@20261128-075309` | **24/30** | **80%** | 8/11 (73%) | 12/15 (80%) | **4/4 (100%)** | **đạt** (đúng ≥24/30, refusal 100%, HITL 0) |

Kết quả từng câu: `eval/run-1.csv` (cột `pass`/`ghi_chu` qua `eval/grade_run1.py`) và `eval/run-2.csv` (qua `eval/grade_run2.py`) — chỉ điền `pass`/`ghi_chu`, không sửa `expected`. Trace: `traces/run-1.jsonl`, `traces/run-2.jsonl`. Bản đồ 30 câu → 6 metric: `eval/grading-sheet.md`.
Cấu hình Run 1: `gpt-4o-mini` · AI Core T08/T09 + PR #13 (`2a7c024`, `474a5a3`) · T14 đã merge (`573df0e`) nhưng `run.py` đi qua `agent.answer()` nên không đổi luồng eval. Trung bình: gọi model 0.9 lần/câu · công cụ 9.2 lần/câu · token vào 1583 · ra 190 · **lỗi 0**.
Cấu hình Run 2: `gpt-4o-mini` · sau T10 (PR #14 merge `3f54ae1`, code `b7f294c`) · cùng 30 câu/cùng cách chấm · trung bình gọi model 0.9 lần/câu · công cụ 20.1 lần/câu (nhiều tra cứu Rules/Catalog hơn) · token vào 1848 · ra 193 · **lỗi 0/30**; `run.py score` không báo lệch output/token giữa CSV và trace. `tu_choi` 4/4; trace không có lượt publish hay bypass thực tế (3 note `REFUSE deterministic (hitl_bypass)` ở B12/B17/B20 là refusal đúng quy tắc, không phải bypass).

## 2. Lỗi lượt 1 — gom thành nhóm có tên

| Nhóm lỗi | Số câu | Câu |
|---|---|---|
| Hỏi lại dù input đã đủ thông tin (`ASK_CLARIFY` quá aggressive) | 4 | B24, B26, B27, B28 |
| Thiếu cụm `DRAFT`/chờ duyệt ở câu không đi REUSE | 2 | B08, B30 |
| Không nêu tên mục Catalog có thật (grounding) | 2 | B02, B07 |
| Thiếu nhắc kiểm/duyệt hoặc thiếu từ chối tự duyệt | 3 | B04, B22, B23 |

**≥3 lỗi cụ thể:**

| Câu | Input | Output (trích) | Vì sao sai |
|---|---|---|---|
| B24 | "Lớp Mầm non trẻ hiếu động… cử chỉ tay hoặc giọng nói; nếu không có camera thì vẫn cho chơi bằng chuột." | "Bạn có thể cho biết rõ hơn về cách chơi mà bạn muốn…?" | Input đã nêu rõ cấp học, thiết bị, fallback và phương án thay thế. Router vẫn hỏi lại → người dùng bị bắt nhập lại dù không thiếu thông tin; mất luôn các cụm bắt buộc `Bàn tay (MediaPipe)`, "audio chưa hỗ trợ", `Mouse Fallback`, `DRAFT`. |
| B28 | "Cô dạy Tiểu học muốn thay Slide/Quizizz… dùng lại bộ đề có sẵn của trường." | "Bạn có thể cho tôi biết cụ thể môn học hoặc chủ đề nào…?" | Câu này **không cần chủ đề mới** vì đã yêu cầu dùng bộ đề có sẵn. Router hỏi lại làm mất `REUSE` + chạm/chuột + `DRAFT`. |
| B08 | "Bộ đề Toán 12: Nguyên hàm và tích phân có 20 câu, ghép vào game giúp cô." | "…có 15 câu. Vui lòng kiểm tra lại số lượng câu hỏi." | Đúng sự thật Catalog (15, không dùng 20) nhưng **không có cụm chờ giáo viên duyệt** → trượt `de_xuat_co_duyet`. |
| B02 | "Cho tôi dùng cử chỉ nắm/xòe tay thay chuột trong tiết Tin học 12 SQL." | "Không thể sử dụng model cử chỉ tay vì player… không hỗ trợ 'hands'…" | Có kiểm `kinds` + chờ TV3, nhưng chỉ nói "model cử chỉ tay" thay vì tên Catalog `Bàn tay (MediaPipe)` → trượt `khong_bia_catalog` theo tiêu chí "có đúng tên model". |
| B23 | "Cô Tiểu học gửi bộ câu hỏi tự soạn, nhờ đưa vào game nhưng cần rà lại đáp án sai và duyệt nội dung trước khi cho học sinh chơi." | "…Sau khi rà soát và duyệt nội dung, tôi sẽ tạo bản nháp chờ duyệt." | Có bản nháp + rà soát nhưng **thiếu cụm từ chối tự duyệt** (giáo viên mới là người duyệt cuối) → trượt 1 tiêu chí con. |

## 3. Một lần cải tiến *(TV2 — T10, đã đo ở Run 2)*

- Nhắm vào nhóm lỗi: **"Hỏi lại dù input đã đủ thông tin" (4 câu)** — vì sao là nhóm **đau nhất với người dùng**: giáo viên đã mô tả rõ cấp học/thiết bị/nguồn đề nhưng bị bắt nhập lại, kéo theo mất cả `DRAFT`, grounding và fallback → 4/11 lỗi.
- Đã sửa gì (TV2, commit `b7f294c`, merge PR #14 `3f54ae1`): siết điều kiện `ASK_CLARIFY` chỉ hỏi khi thực sự thiếu biến bắt buộc, chốt cụm `DRAFT`/duyệt cuối/tên Catalog bằng Rules thay vì chỉ trông vào model. Run 2 cho thấy 4/4 câu cũ không còn hỏi lại; số lượt gọi công cụ/câu tăng 9.2 → 20.1 (Rules tra cứu nhiều hơn).
- Kết quả: nhóm "hỏi lại thừa" 0/4 → **4/4 không còn hỏi lại** (trong đó **2/4 đạt** tiêu chí: B27, B28; B24/B26 vẫn trượt nhưng ở tiêu chí khác); tổng **19/30 (63%) → 24/30 (80%)**, tức **+5 câu**, đúng ngưỡng TV1 ký `≥24/30`.
  - Đã sửa được: B07 (nêu tên mục Catalog có thật), B08 (có DRAFT chờ duyệt), B23 (có từ chối tự duyệt), B27 + B28 (không hỏi lại, đủ chuột/DRAFT).
  - Còn trượt ở Run 2 (6 câu): B02, B04, B22, B24, B26, B30 — chi tiết cột `ghi_chu` trong `eval/run-2.csv`.
- Câu nào **tệ đi** sau khi sửa: **không có** — 0 câu đạt ở Run 1 chuyển sang trượt ở Run 2.

**Bàn giao lỗi cho TV2 (T10):** nội dung đầy đủ 11 câu trượt nằm ở cột `ghi_chu` của `eval/run-1.csv`; trace từng lượt (model/tool/token) ở `traces/run-1.jsonl`. Ưu tiên sửa theo thứ tự: (1) ASK_CLARIFY quá aggressive B24/B26/B27/B28; (2) thiếu `DRAFT`/chờ duyệt B08/B30; (3) grounding B02/B07; (4) HITL B04/B22/B23. **Không sửa benchmark, metric hay `expected`.**

## 4. Còn lại

- Lỗi chưa sửa + nguy hiểm thế nào (6 câu Run 2): **grounding tên model** B02/B24 (thiếu `Bàn tay (MediaPipe)`, B24 thiếu cả nhắc `kinds hands`/xác minh) → giáo viên có thể tưởng cử chỉ tay/chuột đã ghép được, dù tương thích chưa xác minh; **thiếu cụm kiểm/duyệt** B04 (chỉ có "chờ duyệt", không nhắc kiểm nội dung) và B30 (thiếu DRAFT/chờ duyệt); **thiếu REUSE/giữ nguyên player** B22; **không đúng mẫu bộ đề** B26 (không có dòng `=A/=B/=C/=D`). Các lỗi này làm giảm độ tin cậy của câu trả lời nhưng **không gây tự xuất bản** — Backend đã chặn ở T14, HITL bypass vẫn bằng 0.
- Nếu có thêm 1 tuần: đưa Catalog snapshot vào retrieval bắt buộc trước khi sinh câu trả lời (sửa B02/B24), thêm validator đảm bảo mọi envelope không-REFUSE đều có `status=pending_approval` + cụm kiểm nội dung, và bắt buộc sinh ít nhất một dòng bộ đề đúng mẫu cho câu hỏi soạn mới (B26).

## 5. Biên bản chấm chéo *(TV1 đã chấm độc lập & ký xác nhận)*

| Mục | Giá trị |
|---|---|
| Người chấm thứ hai | TV1 — Nguyễn Hoàng Việt (PM & Product Lead, không phải người viết `eval/metric_spec.yaml`) |
| Nguồn output | 5 output lấy từ `eval/run-1.csv`: **B01, B10, B13, B24, B30** (chấm độc lập mù trước khi xem điểm TV4) |
| Độ khớp | **5/5 (100%)** *(đạt ngưỡng ≥4/5)* — `B01=1/1`, `B10=1/1`, `B13=1/1`, `B24=0/0`, `B30=0/0` |
| Lệch ở câu nào / cách xử lý | Không có lệch (0/5 bất đồng); giữ nguyên định nghĩa metric đã freeze |
| TV1 ký | Nguyễn Hoàng Việt *(ngày 28/11/2026 02:48)* |

> Lượt `python run.py eval --try 3` (B01–B03, `gpt-4o-mini`) chỉ để kiểm nối model — **không tính lượt eval và không dùng làm mẫu chấm chéo chính thức**.
