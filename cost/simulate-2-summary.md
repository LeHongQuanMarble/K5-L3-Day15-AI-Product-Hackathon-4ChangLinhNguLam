# Tóm tắt mô phỏng simulate-2@20261128-080557

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| dung_it | 31 | 1 | 2640 | 242 | 1.1 | 11.2 |
| dung_vua | 12 | 2 | 5258 | 395 | 2.1 | 22.6 |
| dung_nhieu | 7 | 4 | 9619 | 754 | 3.9 | 40.7 |

Tỉ lệ đạt dùng để tính: 25/30 (83%) — lượt run-3@20261128-080345

- Tỉ lệ đạt lấy từ lượt nhóm chọn: eval/run-3.csv (--rate-from).

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (100 người) | Chi phí / tháng — cơ sở (300 người) | Chi phí / tháng — cao (1.000 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini (vào 0.15 · ra 0.6 $/1M) | $0.00085 | $0.0010 | $0.00061 | $0.4578 | $1.37 | $4.58 | $0.0046 |
| gpt-4o (vào 2.5 · ra 10 $/1M) | $0.0141 | $0.0169 | $0.0102 | $7.63 | $22.89 | $76.29 | $0.0763 |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (1.7) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: gpt-4o-mini. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 0/50.
