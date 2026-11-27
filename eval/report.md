# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ câu thử, cùng cách chấm. Chấm ở rubric R5.
> Số lấy từ `python run.py score eval/run-1.csv` (và `run-2.csv`) sau khi điền cột `pass`. **Kết quả thấp ghi thật vẫn đủ điểm.**
> Không được: sửa chuẩn "đạt", bỏ câu thử trượt, sửa `expected` cho khớp output, sửa kết quả lượt đã chạy.
> **Khung chuẩn bị (chưa có số):** TV1 ký freeze 28/11 00:50 (`spec.md` §9) — `≥24/30`, `tu_choi` 4/4, HITL bypass 0. Phiếu chấm 30 câu / 6 metric tại `eval/grading-sheet.md`. Chưa có Run 1/2 vì T08/T09/T10 của TV2 chưa xong.

## 0. Khóa đầu vào — đối soát Run 1 = Run 2 *(AC T19)*

| File | Run 1 | Run 2 | Khớp? |
|---|---|---|---|
| `eval/benchmark.csv` (30 câu) | sha256 `0236f1…c82c76` | __ | __ |
| `eval/metric_spec.yaml` (6 metric) | sha256 `435d21…bfe4dc` | __ | __ |
| `data/catalog_snapshot.json` (`79822a4`) | sha256 `b3e681…9743bb` | __ | __ |

Hash đầy đủ và lệnh lấy lại: xem đầu `eval/grading-sheet.md`. **Không đổi 3 file này giữa hai lượt**; nếu lệch thì dừng và báo TV1, không chấm tiếp.

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | | __/__ | | __/__ | __/__ | __/__ | đạt / chưa |
| 2 | | __/__ | | __/__ | __/__ | __/__ | đạt / chưa |

Kết quả từng câu: `eval/run-1.csv`, `eval/run-2.csv`. Trace: `traces/run-1.jsonl`, `traces/run-2.jsonl`. Bản đồ 30 câu → 6 metric và cột `pass`/`ghi_chu`: `eval/grading-sheet.md`.

## 2. Lỗi lượt 1 — gom thành nhóm có tên

| Nhóm lỗi | Số câu | Câu |
|---|---|---|
| vd: bịa nguồn *(ví dụ)* | | |
| vd: đoán khi thiếu thông tin *(ví dụ)* | | |
| | | |

**≥3 lỗi cụ thể:**

| Câu | Input | Output | Vì sao sai |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

## 3. Một lần cải tiến

- Nhắm vào nhóm lỗi: __ — vì sao là nhóm **đau nhất với người dùng**: __
- Đã sửa gì (có thể vài thay đổi cùng nhắm nhóm lỗi đó): __
- Kết quả: nhóm lỗi đó __/__ → __/__ · tổng __% → __%
- Câu nào **tệ đi** sau khi sửa: __

## 4. Còn lại

- Lỗi chưa sửa + nguy hiểm thế nào: __
- Nếu có thêm 1 tuần: __

## 5. Biên bản chấm chéo *(chuẩn bị — chờ Run 1)*

| Mục | Giá trị |
|---|---|
| Người chấm thứ hai | TV1 *(đề xuất; không phải người viết spec)* — chờ xác nhận |
| Nguồn output | 5 output lấy từ `eval/run-1.csv` (sau T18): __ |
| Độ khớp | __/5 *(cần ≥4/5; lệch thì viết lại định nghĩa metric)* |
| Lệch ở câu nào / cách xử lý | __ |
| TV1 ký | __ *(ngày __)* |

> Lượt `python run.py eval --try 3` (B01–B03, `gpt-4o-mini`, token vào/ra 1521/55 · 1517/58 · 1525/40) chỉ để kiểm nối model — **không tính lượt eval và không dùng làm mẫu chấm chéo chính thức**.
