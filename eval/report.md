# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ câu thử, cùng cách chấm. Chấm ở rubric R5.
> Số lấy từ `python run.py score eval/run-1.csv` (và `run-2.csv`) sau khi điền cột `pass`. **Kết quả thấp ghi thật vẫn đủ điểm.**
> Không được: sửa chuẩn "đạt", bỏ câu thử trượt, sửa `expected` cho khớp output, sửa kết quả lượt đã chạy.
> **Chuẩn TV1 ký 28/11 00:50 (`spec.md` §9):** `≥24/30`, `tu_choi` `4/4`, HITL bypass `0`. Phiếu chấm 30 câu / 6 metric tại `eval/grading-sheet.md`.

## 0. Khóa đầu vào — đối soát Run 1 = Run 2 *(AC T19)*

| File | Run 1 | Run 2 | Khớp? |
|---|---|---|---|
| `eval/benchmark.csv` (30 câu) | sha256 `0236f1…c82c76` | __ | __ |
| `eval/metric_spec.yaml` (6 metric) | sha256 `435d21…bfe4dc` | __ | __ |
| `data/catalog_snapshot.json` (`79822a4`) | sha256 `b3e681…9743bb` | __ | __ |

Hash đầy đủ và lệnh lấy lại: xem đầu `eval/grading-sheet.md`. **Không đổi 3 file này giữa hai lượt**; nếu lệch thì dừng và báo TV1, không chấm tiếp. Đã kiểm lại ngay trước Run 1: cả 3 hash khớp bản khóa. **Kiểm lại lần nữa 28/11 khi chờ T10** (trước khi chạy Run 2): `0236f1…c82c76` / `435d21…bfe4dc` / `b3e681…9743bb` — vẫn khớp; cột Run 2 sẽ điền khi có `run-2.csv`.

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | `run-1@20261128-021031` | **19/30** | **63%** | 7/11 (64%) | 8/15 (53%) | **4/4 (100%)** | **chưa** (thiếu 5 câu) |
| 2 | __ | __/__ | | __/__ | __/__ | __/__ | __ |

Kết quả từng câu: `eval/run-1.csv` (cột `pass`/`ghi_chu` đã điền theo `pass_criterion`, không sửa `expected`). Trace: `traces/run-1.jsonl`. Bản đồ 30 câu → 6 metric: `eval/grading-sheet.md`.
Cấu hình Run 1: `gpt-4o-mini` · AI Core T08/T09 + PR #13 (`2a7c024`, `474a5a3`) · T14 đã merge (`573df0e`) nhưng `run.py` đi qua `agent.answer()` nên không đổi luồng eval. Trung bình: gọi model 0.9 lần/câu · công cụ 9.2 lần/câu · token vào 1583 · ra 190 · **lỗi 0**.

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

## 3. Một lần cải tiến *(chờ TV2 — T10)*

- Nhắm vào nhóm lỗi: **"Hỏi lại dù input đã đủ thông tin" (4 câu)** — vì sao là nhóm **đau nhất với người dùng**: giáo viên đã mô tả rõ cấp học/thiết bị/nguồn đề nhưng bị bắt nhập lại, kéo theo mất cả `DRAFT`, grounding và fallback → 4/11 lỗi.
- Đã sửa gì: __ *(TV2 điền sau khi đọc bảng lỗi dưới đây; đề xuất: siết điều kiện ASK_CLARIFY — chỉ hỏi khi thực sự thiếu biến bắt buộc, và luôn append cụm `DRAFT`/chờ duyệt cho mọi nhánh trả lời không phải REFUSE)*
- Kết quả: nhóm lỗi đó __/__ → __/__ · tổng 63% → __%
- Câu nào **tệ đi** sau khi sửa: __

**Bàn giao lỗi cho TV2 (T10):** nội dung đầy đủ 11 câu trượt nằm ở cột `ghi_chu` của `eval/run-1.csv`; trace từng lượt (model/tool/token) ở `traces/run-1.jsonl`. Ưu tiên sửa theo thứ tự: (1) ASK_CLARIFY quá aggressive B24/B26/B27/B28; (2) thiếu `DRAFT`/chờ duyệt B08/B30; (3) grounding B02/B07; (4) HITL B04/B22/B23. **Không sửa benchmark, metric hay `expected`.**

## 4. Còn lại

- Lỗi chưa sửa + nguy hiểm thế nào: sau T10 vẫn có thể sót grounding tên Catalog (giáo viên có thể tưởng model giọng nói tồn tại) và cụm duyệt bị rụng ở câu hỏi thuần thông tin — không gây tự xuất bản (Backend đã chặn ở T14) nhưng làm giảm độ tin cậy của câu trả lời.
- Nếu có thêm 1 tuần: đưa Catalog snapshot vào retrieval bắt buộc trước khi sinh câu trả lời, và thêm validator đảm bảo mọi envelope không-REFUSE đều có `status=pending_approval` + cảnh báo kiến thức khi có bộ đề mới.

## 5. Biên bản chấm chéo *(chờ TV1 ký)*

| Mục | Giá trị |
|---|---|
| Người chấm thứ hai | TV1 *(đề xuất; không phải người viết spec)* — chờ xác nhận |
| Nguồn output | 5 output lấy từ `eval/run-1.csv`: **B01, B10, B13, B24, B30** (đã chọn, chưa có người chấm) |
| Độ khớp | __/5 *(cần ≥4/5; lệch thì viết lại định nghĩa metric)* |
| Lệch ở câu nào / cách xử lý | __ |
| TV1 ký | __ *(ngày __)* |

> Lượt `python run.py eval --try 3` (B01–B03, `gpt-4o-mini`) chỉ để kiểm nối model — **không tính lượt eval và không dùng làm mẫu chấm chéo chính thức**.
