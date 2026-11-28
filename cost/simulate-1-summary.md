# Tóm tắt mô phỏng simulate-1@20261128-075539

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| dung_it | 31 | 1 | 2263 | 250 | 1.1 | 22.1 |
| dung_vua | 12 | 2 | 4478 | 399 | 2.1 | 44.5 |
| dung_nhieu | 7 | 4 | 8231 | 821 | 3.9 | 84.4 |

Tỉ lệ đạt dùng để tính: 24/30 (80%) — lượt run-2@20261128-075309

- Tỉ lệ đạt lấy từ lượt nhóm chọn: eval/run-2.csv (--rate-from).

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (100 người) | Chi phí / tháng — cơ sở (300 người) | Chi phí / tháng — cao (1.000 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini (vào 0.15 · ra 0.6 $/1M) | $0.00076 | $0.00096 | $0.00058 | $0.4152 | $1.25 | $4.15 | $0.0042 |
| gpt-4o (vào 2.5 · ra 10 $/1M) | $0.0127 | $0.0159 | $0.0096 | $6.92 | $20.76 | $69.20 | $0.0692 |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (1.7) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: gpt-4o-mini. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 0/50.
