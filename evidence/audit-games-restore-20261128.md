# AUDIT & ĐỐI CHIẾU — Game của team trước/sau cleanup (28/11)

Phát hiện PM: "một số game do thành viên phát triển có dấu hiệu biến mất sau cleanup".
Kết quả audit đối chiếu 3 backup SQLite (không suy đoán, mọi số liệu từ DB thật):

## 1. Game của team (showcase/sample, owner NULL): 7/7 NGUYÊN VẸN & CHƠI ĐƯỢC

| Game | Contributor | Source commit | Trước cleanup | Hiện tại | Chơi được (API /try) |
|---|---|---|---|---|---|
| Quiz ABCD bằng cử chỉ (sample) | Khung AI Lab | store.init seed | Có | CÓ | PASS kinds=[image,pose] |
| Vòng quay chọn tên (sample) | Khung AI Lab | store.init seed | Có | CÓ | PASS |
| Cầu Lông 3D | TV3 | seed_players/badminton-3d.html | Có | CÓ | PASS kinds=[pose,image,audio] |
| Sút Penalty 3D | TV3 | seed_players/penalty-3d.html (cập nhật 28/11, branch feat/update-tet-penalty-games) | Có | CÓ (đã refresh HTML mới) | PASS kinds=[pose,image,audio,hands] |
| Giải cứu thế giới | TV3 | seed_players/rescue-world.html | Có | CÓ | PASS kinds=[image,pose,audio] |
| Tết 2027: Dê Vàng và cổng băng | TV3 | seed_players/tet-2027.html (cập nhật 28/11) | Có | CÓ (đã refresh HTML mới) | PASS kinds=[hands,image,pose] |
| Chim Bay Nói | TV3 | seed_players/voice-flap.html | Có | CÓ | PASS kinds=[audio] |

Seed files trên git: 5/5 file .html còn nguyên, working tree sạch.
Players mất giữa cleanup 1/2: **0** (đối chiếu backup pre-cleanup1 vs pre-cleanup3).

## 2. Những gì CÓ BỊ XOÁ — và vì sao không phải game của team

Cleanup 3 (12:05) xoá theo quy tắc "test fixture đã xác minh":
- 5 users: uat_real_1795838887 / uat_real_1795838931 / uat_real_1795839015 / modulecheck_1795840140 /
  uat_real_1795841316 — tài khoản do SCRIPT KIỂM THỬ của Claude tạo trong ca này (mẫu tên + timestamp khớp script).
- 7 apps (14–20) + 6 players (21–25, 38) + 7 exams + 7 drafts — TOÀN BỘ source='ai', owner = 5 test users trên:
  là kết quả GENERATE của các lần chạy UAT Real AI (bằng chứng đã lưu evidence/real-ai-uat-20261128-pm.md).
  KHÔNG có row nào của user thật (admin/demo_user/gv_*/co_*), KHÔNG có row showcase/sample nào.

Cleanup 1–2 (11:25): xoá 10 model placeholder tên "M" (URL `models/x/` 404 — fingerprint khớp chính xác
INSERT trong test_apps_edit.py/test_app_image.py, created=0.0) + 9 app "App thử" trỏ vào chúng.
Đây là dữ liệu test fixture làm nhiễm runtime DB (nguyên nhân lỗi 404 PM báo) — không phải model/game thật.

## 3. Game do thành viên phát triển NHƯNG chưa nằm trong main (chưa mất — chưa bao giờ được tích hợp)

| Branch | Contributor | Nội dung | Trạng thái |
|---|---|---|---|
| feature/chatbot (starter-repo era) | cũ | 74 file bản starter-repo đầu dự án | KHÔNG tích hợp — main đã refactor hoàn toàn, cấu trúc không còn tồn tại |
| feat/ui-ux-refactor | HViettt | UI refactor ~3k dòng | KHÔNG tích hợp — bị main vượt xa (views-assistant.js mới hơn trên main) |
| docs/t15-video, docs/tv4-source-nguoi-dung-handoff | TV3/TV4 | docs | docs-only, để owner merge |

## 4. Kết luận
1. Không game nào của team bị xoá hoặc mất. 7/7 game mẫu nguyên vẹn + chơi được (bằng chứng API 11:58).
2. Toàn bộ row bị xoá đều là test fixture do script kiểm thử tạo ra trong ca này — có backup đầy đủ
   (evidence/db-backups/ailab-pre-cleanup{,2,3}-20261128.db) — khôi phục được bất cứ lúc nào nếu PM cần.
3. Hiện còn 2 user test mới (uat_real_1795841836 — app 11 đua xe; audit_check_1795841903) chưa xoá —
   đợi PM duyệt lượt cleanup tiếp theo theo chính sách mới.
4. Chính sách cleanup áp dụng từ đây: CHỈ xoá nháp AI GENERATE thất bại hoặc test fixture đã xác minh;
   không đụng game thành viên/showcase/starter/game user thật/model thật bất kể chất lượng giao diện.

