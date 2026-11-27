# Hồ sơ đánh giá — một trang

> Điền ở guide bước 2.4 (mục 1–4, trước CP2) và 4.1 (mục 5–6, trước CP4). Ôn lại: ngày 9, ngày 14 · lab ngày 9. Chấm ở rubric R4, R5.
> Người ngoài nhóm đọc trang này phải hiểu được: nhóm đo cái gì, bằng gì, ra số nào. Trang slide "Đánh giá thế nào" lấy từ đây.

## 1. Dataset → xử lý

- Dataset 1 (Catalog AI Lab): 1 model + 2 player + 6 bộ đề/90 câu, snapshot cố định `79822a4` (`data/catalog_snapshot.json`, PR #7 chờ merge). Dùng tra cứu tên/ID thật và kiểm tương thích `Model + Player + Question Set`.
- Dataset 2/3: 90 câu + 8 ảnh `synthetic` từ `ailab/seed_exams.json`, `ailab/seed_images/`; không chia train/val/test, không dùng làm bằng chứng pain.
- Dataset 4: `eval/benchmark.csv` 20 câu tự soạn (mục 2); xử lý bằng `run.py check` → `run.py eval` → `run.py score`.

## 2. Bộ câu thử dựng ra sao

- `eval/benchmark.csv`: 20 câu (thuong 6 · kho 10 · tu_choi 4, trong đó 4 câu `tu_choi` tấn công an toàn/HITL)
- Nguồn (`python run.py check` in sẵn): nguoi_dung 0 · data_that 0 · tu_viet 20 · sinh_seed 0 → từ người dùng / data thật 0/20 (cần ≥1/3; chờ T03/TV1)
- Độ phủ — lưới input 3–5 chiều (guide 2.4 bước 5): môn học/cấp học · thiết bị/camera · nguồn đề (có sẵn/tự soạn) · chế độ (`REUSE`/`GENERATE`) · quyền (giáo viên/Admin). Đủ 8 kịch bản: `ASK_CLARIFY`, `REUSE`, `GENERATE`, `REFUSE`, Question Quality, Compatibility, HTML Safety, HITL.
- Câu `kho` trỏ về 4 lớp chỗ khó (`spec.md` §5): lớp 1: B07/B13/B15 (không có module phù hợp hoặc bịa/ghép sai) · lớp 2: B05/B06/B19 (thiếu thông tin) · lớp 3: B10/B11/B12/B17/B18/B20 (tấn công/tự duyệt) · lớp 4: B02/B04/B08/B09 (tương thích, định dạng đề, fallback).

## 3. Metric và cách chấm

| Metric (`eval/metric_spec.yaml`) | Cách chấm | Ngưỡng |
|---|---|---|
| | code / llm / nguoi | |
| | | |
| | | |

- **Người thứ hai chấm thử:** __ (không phải người viết spec) chấm độc lập 5 output → khớp __/5 *(cần ≥4/5; lệch thì viết lại định nghĩa)*
- LLM chấm (nếu có): đã kiểm tay __ câu, khớp __/__
- **Chuẩn "đạt"** (chép nguyên từ `spec.md` §7, chốt trước 19:30 Thứ Sáu 27/11): "__"

## 4. Lệnh

`python run.py eval` → `eval/run-N.csv` + `traces/run-N.jsonl` · điền cột `pass` · `python run.py score eval/run-N.csv`

## 5. Đã chạy gì

| Lượt | Run ID | Model | Cấu hình (prompt / công cụ / thay đổi) | Đạt / tổng | % | Đạt chuẩn? |
|---|---|---|---|---|---|---|
| 1 | | | | __/__ | | |
| 2 | | | | __/__ | | |

Lượt chạy lại vì lỗi kỹ thuật, lượt sau CP4: ghi thêm dòng, không sửa dòng cũ.

## 6. Lỗi chính

Tóm 2–3 dòng từ `eval/report.md`: nhóm lỗi lớn nhất · đã sửa gì · còn lại gì.
