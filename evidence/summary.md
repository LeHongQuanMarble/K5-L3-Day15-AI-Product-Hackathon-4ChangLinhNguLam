# Tổng hợp bằng chứng pain

> Cập nhật CP3 27/11/2026: đã nhận **6 tình huống thật S1–S6 do TV1 cung cấp** (tóm tắt theo vai, không tên, không trích nguyên văn). Chúng đủ để giải quyết yêu cầu cột `source` của `run.py check`, **chưa đủ để đạt rubric R1 / AC T03** (cần ≥3 phỏng vấn ngoài nhóm hoặc ≥20 phiếu khảo sát, ≥5 trích dẫn nguyên văn). Không ghi T03 là `DONE` khi chưa có phỏng vấn.

## 1. Nguồn đã dùng

| Nguồn | Đạt ngưỡng? | File |
|---|---|---|
| Đào data (x/N, %, cách đếm chạy lại được, ≥5 ví dụ) | ☐ | `evidence/data-mining.md` |
| Phỏng vấn (≥3 người ngoài nhóm, đúng người dùng) | ☐ | `evidence/interviews/` — mới có `TEMPLATE.md`, 0 phỏng vấn |
| Khảo sát (≥20 người ngoài nhóm, đúng người dùng) | ☐ | `evidence/survey/` — chưa có phiếu |
| Tình huống thật S1–S6 do TV1 cung cấp (tóm tắt) | ⚠️ **không tính ngưỡng R1** | `eval/benchmark.csv` B21–B30 · `docs/HANDOFF-TV4-nguon-nguoi-dung.md` |

## 2. Số chính

- Tình huống thật: **6/6** (S1–S6) — 5 vai giáo viên (Tiểu học, CĐ/ĐH, Mầm non, THCS) và 1 Lab Coach AI20k. Nguồn: TV1 cung cấp 27/11/2026; đã tóm tắt, không có tên người, không có trích nguyên văn.
- Baseline có nguồn duy nhất: **10–20 phút** chuẩn bị một game ôn tập (S1). Đây là con số do TV1 cung cấp, **không phải trung vị khảo sát**; chưa có With Agent để so sánh.
- Phỏng vấn: **0/3** người · số lần / tháng: chưa đo · mỗi lần mất: chỉ có S1 (10–20 phút).
- Khảo sát: n = **0** .
- Số lần / tháng và tỉ lệ người gặp pain: **chưa đo** — không suy từ 6 tình huống.

Bảng phỏng vấn để trống có chủ đích; không điền P1–P3 giả.

| | Vai | Gặp pain? | Số lần / 1 tháng qua | Lần gần nhất mất | Đang xoay xở bằng |
|---|---|---|---|---|---|
| P1 | *(chưa phỏng vấn)* | | | | |
| P2 | *(chưa phỏng vấn)* | | | | |
| P3 | *(chưa phỏng vấn)* | | | | |

## 3. ≥5 trích dẫn hoặc ví dụ nguyên văn (có nguồn, bỏ tên)

> **Chưa có trích dẫn nguyên văn.** 6 dòng dưới là *tóm tắt tình huống thật* (S1–S6), **không tính vào ≥5 trích dẫn** của AC T03.

1. S1 — Giáo viên Tiểu học: cần game ôn tập chơi bằng chuột/bàn phím, chuẩn bị 10–20 phút, thay cho Slide/Quizizz. *(tóm tắt S1)*
2. S2 — Giáo viên CĐ/ĐH: có sẵn bộ câu hỏi, muốn đưa vào trò chơi mà không cấu hình lại. *(tóm tắt S2)*
3. S3 — Giáo viên Tiểu học: cần rà soát sai sót câu hỏi/đáp án trước khi dùng với học sinh. *(tóm tắt S3)*
4. S4 — Giáo viên Mầm non: muốn game vận động bằng cử chỉ/giọng nói cho trẻ hiếu động, có Mouse Fallback khi không có camera. *(tóm tắt S4)*
5. S5 — Lab Coach AI20k: quiz lặp gây nhàm chán, muốn GENERATE bản nháp trong sandbox kèm cảnh báo kiểm duyệt kiến thức. *(tóm tắt S5)*
6. S6 — Giáo viên THCS: thiết bị không tương thích, cần chơi bằng chuột/bàn phím/cảm ứng không camera. *(tóm tắt S6)*

## 4. Các nguồn có khớp nhau không

Chưa đối chiếu được: hiện chỉ có **một nguồn** (TV1 tóm tắt S1–S6), chưa có phỏng vấn/khảo sát/đào data để tam giác hóa. S1–S6 nhất quán ở nhu cầu "đưa bộ đề có sẵn vào game, rà soát rồi mới dùng, vẫn chơi được khi thiếu camera", nhưng **chưa có bằng chứng độc lập**.

## 5. Kết luận

Giả thuyết ở `evidence/hypothesis.md`: **chưa đủ dữ liệu để kết luận đúng/sai** — S1–S6 ủng hộ hướng H1 (chọn/tạo game + kiểm duyệt + fallback), nhưng chưa có trích nguyên văn, chưa đo tần suất và chưa đo With Agent. Điều vẫn chưa biết: số giáo viên gặp pain, số game/tháng, thời gian với agent. Cần TV1 hoàn tất ≥3 phỏng vấn hoặc ≥20 phiếu khảo sát trước khi ký AC T03.

## Lịch hẹn (dùng cho CP2 — chỉ ghi vai và giờ, không tên)

| Vai | Giờ hẹn | Đã xong? |
|---|---|---|
| *(chưa cập nhật — TV1 điền)* | | |
