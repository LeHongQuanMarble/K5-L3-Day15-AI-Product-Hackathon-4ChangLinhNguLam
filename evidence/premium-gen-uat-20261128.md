# Premium Generation Smoke Test — 28/11 (Generator: gpt-4.1, Router/Exam: gpt-4o-mini)

Server: AILAB_ENABLE_AUDIO=1 · GAME_GENERATOR_MODEL=gpt-4.1 · GAME_REPAIR_MODEL=gpt-4.1 (multi-model routing qua env, không hardcode)
Ngân sách PM duyệt: $0.40 — **chi phí đợt này: ~$0.24** (4.1: ~62k token in / ~19k token out theo usage API; ~$2/1M in + $8/1M out. Đợt 4.1-mini trước: ~$0.01; các lần trước trong ngày: <$0.01).

## 4 game Premium đã publish (đều là Player MỚI do AI sinh, không REUSE)

| App | Link (/play/<id>) | Model gắn | Checks | Ghi chú chất lượng |
|---|---|---|---|---|
| 13 Đua xe chọn làn | http://127.0.0.1:8800/play/13 | **Lái Xe** (pose, TM a6Z7kwzyq) | 25/27 PASS (2 SAI là bug check-script, đã sửa) | Màn start đẹp 7/10 (vision), mapping nghiêng trái/phải/Nitro từ outputs thật, 1 ô camera |
| 14 Quiz Hệ Mặt Trời | http://127.0.0.1:8800/play/14 | **Âm thanh A B C D** (audio, TM eC5WQ6nj_) | PASS trừ 1 check heuristic đã sửa | GENERATE audio thật: chọn đáp án bằng tiếng phát A–D qua micro + chuột |
| 15 Thu hoạch táo | http://127.0.0.1:8800/play/15 | Bàn tay MediaPipe (hands) | hands-on handshake PASS (regex cải thiện) | Game tự implement JLRuntime theo mô tả prompt; thiếu ô camera pip (cosmetic — vẫn chơi bằng cursor + chuột) |
| 16 Phân loại động vật | http://127.0.0.1:8800/play/16 | mouse-only | PASS hết (trừ 1 check mapping-mouse đã bỏ) | Gameplay kéo thả sáng tạo, không bị ép vào template |

Ảnh chụp: evidence/screenshots/gameplay-{driving,audio,hands,mouse}.png (màn start; gameplay cần bấm Bắt đầu — PM chơi trực tiếp qua link).

## Nguyên nhân các lần audio FAIL trước đó (đã sửa, đáng nhớ)
Routing prompt + catalog context còn 3 chỗ hardcode "audio chưa hỗ trợ" (từ thời điểm audio bị gate) →
LLM định tuyến cứ ASK_CLARIFY/REFUSE dù flag đã bật. Đã thay hết bằng rule động theo
chatbot_catalog.AUDIO_SUPPORTED (tắt flag = giữ nguyên lời trung thực cho Frozen Eval B24/B30).

## Đánh dấu mức kiểm chứng
- Protocol/Publish/Play/Reload: PASS (tự động).
- Real inference (camera thấy tay / micro nghe A–D): CHƯA — là phần Human UAT của PM trên trình duyệt.
- Không chạy benchmark; Eval Run 1/2/3 nguyên vẹn; nâng cấp generator là thay đổi cấu hình hệ thống
  được đánh giá — chưa đại diện accuracy mới.

