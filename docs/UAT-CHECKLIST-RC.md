# HUMAN UAT CHECKLIST — RC 28/11 (PM trực tiếp kiểm)

> Server: http://127.0.0.1:8800 — **đăng nhập nút demo "Admin"** (AILAB_DEMO=1, tài khoản `demo_admin`).
> Mức đã kiểm tự động: protocol / publish / play / reload / mapping / số câu / security static. Phần dưới là phần CHỈ con người xác nhận được.

## A. 4 game Premium (Player mới do AI gpt-4.1 sinh, gắn Model thật)

| # | Link | Model | Kiểm tra bắt buộc | Đạt? |
|---|---|---|---|---|
| 1 | `/play/13` — Đua xe chọn làn | **Lái Xe** (pose) | [ ] Camera mở tự động, [ ] nghiêng người trái/phải → xe chuyển làn, [ ] đáp án đúng → +điểm, [ ] chuột vẫn chơi trọn vẹn, [ ] Reset sạch, [ ] kết thúc gửi điểm, [ ] chỉ 1 ô camera, [ ] không lỗi console (F12) | ⬜ |
| 2 | `/play/14` — Quiz Hệ Mặt Trời | **Âm thanh A B C D** (audio) | [ ] Micro mở (icon quyền), [ ] phát âm A/B/C/D → chọn đúng đáp án, [ ] giữ đủ ~0.8s mới tính (không chọn lặp), [ ] phổ tần số hiện trong ô nhỏ, [ ] chuột fallback, [ ] micro tắt khi rời trang, [ ] Reset sạch | ⬜ |
| 3 | `/play/15` — Thu hoạch táo | Bàn tay MediaPipe | [ ] Cursor tay theo ngón trỏ, [ ] nắm tay = hái/chọn, [ ] điểm + chuyển câu đúng, [ ] chuột fallback, [ ] Reset sạch *(đã biết: thiếu ô camera pip — cosmetic)* | ⬜ |
| 4 | `/play/16` — Phân loại động vật | mouse-only | [ ] Kéo thả trượt mượt, [ ] phản hồi đúng/sai trực quan, [ ] điểm + màn kết thúc + Chơi lại | ⬜ |

## B. Luồng AI Composer end-to-end (1 ca là đủ)

- [ ] Vào **Trợ lý AI** → gõ: *"Tạo một trò chơi mới đua xe chọn làn dùng Model Lái Xe, phép nhân lớp 3, 4 câu hỏi mới, có chuột dự phòng."*
- [ ] Nhánh hiện **GENERATE** (không REUSE, không mouse-only), Model đúng **Lái Xe**
- [ ] Preview chạy trong iframe (1 camera), bấm **Duyệt** (HITL) → Publish → **Play** mở được
- [ ] Thử 1 ca audio: *"Tạo game mới dùng Âm thanh A B C D..."* → GENERATE audio
- [ ] Gọi App đã publish bằng URL `/play/<id>` sau khi reload trang (persistence)

## C. 7 game mẫu của team (không regression)

- [ ] **Kho mẫu game** hiện đủ 7 game (Quiz ABCD, Vòng quay, Cầu Lông 3D, Sút Penalty 3D, Giải cứu thế giới, Tết 2027, Chim Bay Nói)
- [ ] Chạy thử 1 game showcase có camera (vd Tết 2027 với Bàn tay) vẫn chơi được

## D. Catalog Model

- [ ] Kho mô hình hiện đúng **3 model thật** (Bàn tay MediaPipe / Lái Xe / Âm thanh A B C D), không còn model "M" placeholder
- [ ] Tạo thử 1 model với URL sai → trạng thái **Chưa kết nối (broken)**, không thể ghép vào game (lỗi tiếng Việt dễ hiểu)

## Lưu ý phân loại kiểm chứng (không gộp chỉ số)

- **Benchmark Run 1/2/3** (19/30 → 24/30 → 25/30): đo trên frozen registry, CLI — *không thay đổi bởi RC này*
- **Regression offline**: 353/353 PASS (229 ailab + 124 codebase)
- **Premium Smoke**: 4 game Real AI vừa liệt kê — kiểm protocol + publish/play tự động, thẩm mỹ bằng screenshot
- **Human UAT**: chính checklist này — chưa PASS cho tới khi PM đánh dấu

Blocker biết trước: game /play/15 thiếu ô camera pip (cosmetic); micro/camera cần Chrome/Edge + https hoặc localhost.
