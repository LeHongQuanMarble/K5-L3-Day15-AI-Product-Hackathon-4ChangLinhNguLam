# Chi phí khi dùng thật

> Điền ở guide bước 4.2, nộp ở CP4 14:30 Thứ Bảy 28/11. Ôn lại: ngày 13, ngày 1, ngày 14 · lab ngày 13, lab ngày 14. Chấm ở rubric R6.
> Số **không điền tay**: điền `cost/personas.yaml` → `python run.py simulate` → chép bảng trong `cost/simulate-N-summary.md` vào đây.
> Lúc build dùng gói miễn phí vẫn tính theo **giá gói trả phí** — đây là chi phí cho lúc đưa vào dùng thật.

## 1. Đầu vào

- **Persona** (`cost/personas.yaml`): 3 kiểu — `dung_it` 0.67 · 1.5 lần/tháng · 1 lượt/phiên; `dung_vua` 0.17 · 4 lần/tháng · 2 lượt/phiên; `dung_nhieu` 0.16 · 11 lần/tháng · 4 lượt/phiên. Nguồn: tỉ lệ từ khảo sát S1–S6 (`evidence/summary.md` §2), số lượt/phiên và mốc `>10` ghi rõ *(tự ước tính)* trong `personas.yaml`.
- **Số người dùng thật** 3 kịch bản: thấp **100** · cơ sở **300** · cao **1000**. Nguồn: *(tự ước tính)* — repo chưa có số công khai (xem `personas.yaml` dòng `source`); chờ T03 bổ sung thì cập nhật.
- **Giá** ≥2 mức model: `gpt-4o-mini` vào 0.15 / ra 0.60 USD mỗi 1M token; `gpt-4o` vào 2.50 / ra 10.00 USD mỗi 1M token. Nguồn: https://platform.openai.com/docs/pricing · xem 28/11/2026 (ghi trong `personas.yaml`).
- **Tỉ lệ đạt** dùng để tính: __/__ (__%) — lượt `run-2` **(chưa có; chạy sau T10/T19 — không dùng tỉ lệ Run 1 thay thế)**.
- Đo token trên model `gpt-4o-mini`, tính giá model `gpt-4o-mini` và `gpt-4o` (xem mục 5: `simulate --try` đã chạy Real AI, 10 phiên, token > 0).

## 2. Kết quả mô phỏng

Lượt mô phỏng: `cost/simulate-__.csv` · run ID __ · __ phiên · seed __

*(dán bảng từ `cost/simulate-N-summary.md`)*

| Model | Chi phí / phiên | Chi phí / task thành công | / tháng — thấp | / tháng — cơ sở | / tháng — cao | / người / tháng (cơ sở) |
|---|---|---|---|---|---|---|
| | | | | | | |
| | | | | | | |

Chi phí / task thành công = chi phí trung bình mỗi phiên ÷ tỉ lệ đạt — **không coi như đạt 100%**.

## 3. So với impact

- Impact / người / tháng (`spec.md` §2): **chưa tính được** — mới có Baseline 10–20 phút/trò chơi (S1), chưa có `With Agent` và số giáo viên/tần suất đo được. Không bịa số để so sánh.
- Chi phí / người / tháng (cơ sở, model `gpt-4o-mini`): __ *(chờ bảng mục 2 sau Run 2)*
- **Kết luận một dòng — đáng làm không:** __ *(chờ chi phí / task thành công từ tỉ lệ Run 2)*

## 4. *(Muốn sâu hơn, không bắt buộc)*

- Bảng độ nhạy: model rẻ hơn · cache · cắt ngữ cảnh · giới hạn bước — mỗi cần gạt đổi chi phí bao nhiêu
- Chi phí ngoài model: hosting, lưu trữ, giờ công người duyệt
- Quy mô nào thì bài toán còn đáng làm

## 5. Kiểm chứng lượt chạy thử CP3 — chờ TV1 xác nhận

| Mục | Giá trị kiểm chứng được |
|---|---|
| Lệnh | `python run.py simulate --try` — 10 phiên, `seed: 42` |
| Run ID | `simulate-try@20261128-004848` (28/11/2026 00:48:48) |
| Model / token | `gpt-4o-mini`, token vào/ra > 0 ở mọi phiên; **0/10 phiên lỗi** (không phải model `fake`) |
| Cấu hình | `simulate.load_config()` chạy xong, **0 warning**; 3 persona (0.67 / 0.17 / 0.16), 2 mức giá |
| File đầu ra | `cost/simulate-try.csv` (11 dòng gồm header, sha256 `7c944fa18413`) · `traces/simulate-try.jsonl` (27 dòng sự kiện, sha256 `cf7e93fb7553`) · `cost/simulate-try-summary.md` (20 dòng, sha256 `4580b5b02924`) |
| Bảo mật | Đã quét 5 file sinh ra (2 CSV/trace của `eval --try` + 3 file ở trên): `API_KEY` trong `.env` **không xuất hiện** ở bất kỳ file nào |
| Phạm vi | **Lượt thử — KHÔNG tính vào bản nộp CP4.** Chưa có lượt eval đã chấm nên chưa tính được chi phí / task thành công; bảng mục 2 vẫn để trống chờ `python run.py simulate` ≥50 phiên sau Run 2 |

> Các file `*-try.*` nằm trong `.gitignore` (bị ghi đè mỗi lần chạy lại). Nếu chạy lại, cập nhật Run ID và sha256 ở bảng trên trước khi ký.

**TV1 xác nhận đã chạy:** Nguyễn Hoàng Việt *(ngày 28/11/2026 02:48 · Xác nhận Smoke Test CP3 `simulate-try@20261128-004848` hợp lệ: 10 phiên, seed 42, `gpt-4o-mini`, 0/10 lỗi, token > 0, không lộ API key; chỉ xác nhận lượt thử CP3, không đánh đồng với Cost Simulation chính thức ≥50 phiên CP4.)*
