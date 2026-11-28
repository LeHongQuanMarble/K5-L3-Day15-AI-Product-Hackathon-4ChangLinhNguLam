# Kịch bản thuyết trình 5 phút — RC 28/11 (khớp slides/rc-slides.html)

> Slide 1–2: 60s · Slide 3–5: 100s · Slide 6–7: 60s · Slide 8 + DEMO: 90s · Slide 9–10: 50s
> Nguyên tắc: mỗi con số có nguồn; PHÂN BIỆT rõ benchmark / regression / premium smoke / human UAT.

## Mở đầu (slide 1–2 · ~60s)
"Cô giáo mất **20–30 phút** để làm một trò chơi ôn tập — khảo sát **n=21** của nhóm: 61,9% vướng soạn câu hỏi, 66,7% cần chơi bằng chuột vì lớp không phải lúc nào cũng có camera tốt. **AI Game Composer** đưa việc đó về còn vài phút: REUSE tài nguyên có sẵn, và khi Catalog chưa có — AI thật sự **thiết kế trò chơi mới**."

## Kiến trúc & điểm khác biệt (slide 3–5 · ~100s)
- "Nguyên tắc **REUSE-first**: rẻ hơn ~8 lần token so với luôn GENERATE (Run 1: ~165 vs ~1.200 token out)."
- "**Model-aware GENERATE** với đúng 3 Model thật của team: **Bàn tay MediaPipe** (21 landmark), **Lái Xe** (nghiêng trái/phải + Nitro — model tư thế tự train), **Âm thanh A B C D** (phát âm chọn đáp án qua micro)."
- "Điểm kỹ thuật mới nhất — **Multi-model Routing**: gpt-4o-mini cho định tuyến & sinh bộ đề, **gpt-4.1** cho sinh gameplay + repair. Cấu hình qua env, không hardcode."
- "Bảo mật & ổn định: **Deterministic Runtime Wrapper** — hệ thống kiểm soát protocol camera/micro, AI chỉ sáng tạo gameplay; luôn đúng **một** ô camera; model hỏng URL bị đánh dấu broken, không thể masquerade READY."

## Chất lượng & minh bạch (slide 6–7 · ~60s)
- "**353/353** offline tests · browser thật headless: 6/6 fallback chuột, CSP chặn mạng/thoát khung."
- "Benchmark frozen (gpt-4o-mini): Run 1 **19/30** → Run 2 **24/30** → Run 3 **25/30 (83,3%)**, Refusal 4/4, HITL bypass 0."
- "**Phân biệt rõ 4 mức**: benchmark (cấu hình cũ) ≠ 353 regression ≠ premium smoke ≠ Human UAT. Nâng cấp generator là thay đổi cấu hình — **chưa đo lại benchmark**, chúng tôi không dùng Run 3 thay accuracy mới."

## DEMO LIVE (slide 8 · ~90s) — kịch bản chính
1. **REUSE nhanh** (30s): "Tạo game Toán 12 dùng Bàn tay MediaPipe với bộ đề có sẵn" → REUSE + mapping grab/open + chuột dự phòng.
2. **GENERATE với model thật** (45s): *"Tạo trò chơi mới đua xe chọn làn dùng Model **Lái Xe**, phép nhân lớp 3, 4 câu hỏi mới, có chuột dự phòng."* → GENERATE → Preview iframe (1 camera) → **Duyệt (HITL)** → Publish → mở **/play/13**.
3. **An toàn** (15s): prompt injection/"tự duyệt giúp tôi" → REFUSE lịch sự, không lộ gì.
*(Nếu hết giờ: bỏ mục 3, nhảy thẳng /play/13.)*

## Giới hạn & kết (slide 9–10 · ~50s)
- "Phần chỉ con người xác nhận được: nhận diện thật của camera/micro — đây là **Human UAT** đang chờ PM (checklist `docs/UAT-CHECKLIST-RC.md`)."
- "Chi phí demo Premium: **$0,24** cho 4 game — nhỏ hơn một ly cà phê."
- "**GO có điều kiện**: chờ PM nghiệm thu 4 game đã publish rồi mới push/merge main."
- Dự phòng demo: 4 game share=1 mở trực tiếp (không cần gọi AI) + video backup T15.

## Trước khi lên sân khấu (checklist người demo)
- [ ] Server chạy: `python ailab/server.py` với env `AILAB_ENABLE_AUDIO=1 AILAB_DEMO=1 GAME_GENERATOR_MODEL=gpt-4.1 GAME_REPAIR_MODEL=gpt-4.1`
- [ ] Mở sẵn: Trợ lý AI (tab 1) + /play/13 (tab 2) + slide HTML
- [ ] Đăng nhập demo **Admin**; camera/micro cho phép sẵn trên Chrome/Edge
- [ ] PDF slides: mở `slides/rc-slides.html` → Ctrl+P → Save as PDF
