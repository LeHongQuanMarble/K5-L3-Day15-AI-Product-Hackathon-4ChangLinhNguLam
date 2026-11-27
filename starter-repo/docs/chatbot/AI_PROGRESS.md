# Tiến độ và quyết định

Mốc bàn giao: 2026-11-27, múi giờ Asia/Bangkok. Commit khảo sát `faa44a8`, nhánh `feature/chatbot`. Trạng thái bên dưới là lúc soạn tài liệu, không phải lời cam kết mã đã được triển khai.

## Quy tắc trạng thái

- TODO: chưa làm.
- IN_PROGRESS: đang thực hiện, có chủ sở hữu.
- BLOCKED: chỉ rõ điều kiện cản trở và ai xử lý.
- REVIEW: có thay đổi/bằng chứng, đang chờ kiểm tra.
- DONE: đã đạt tiêu chí và có bằng chứng.

## Khảo sát đã thực hiện

| Mục | Trạng thái | Bằng chứng/giới hạn |
|---|---|---|
| 1.1 Repo local | DONE | Git root, status, branch, remote, log, tracked files đã đọc |
| 1.2 Đồng bộ | DONE | Fetch thành công ở phiên trước; chatbot...origin/main = 0/0 lúc kiểm tra, không đảm bảo remote không đổi sau đó |
| 1.3 Nhánh | DONE | feature/chatbot tại faa44a8 |
| 1.4 Tài liệu Hackathon | DONE | Đề, rubric, guide, spec/metric/team mẫu đã đọc |
| 1.5–1.10 Mã và hợp đồng | DONE | Đã đọc chatbot/Player/Model/Exam/App/web/API; kết luận ở bộ bàn giao |
| 1.11 Chạy sản phẩm | REVIEW | 27/27 unittest cũ đạt; API có bước đạt, PUT App lỗi; browser/AI thật/webcam chưa kiểm |
| 1.12–1.13 Tổng hợp/phạm vi | REVIEW | Đề xuất trong bộ tài liệu, cần G0 chốt triển khai |
| Bộ tài liệu bàn giao | REVIEW | Đã soạn, cần review chéo với mã và G0 |

## Công việc triển khai

| Task | Trạng thái | Chủ sở hữu | Bằng chứng |
|---|---|---|---|
| G0 Chốt thiết kế tích hợp | REVIEW | Điều phối | [G0_DECISIONS.md](G0_DECISIONS.md); chờ review + người dùng trả lời Q1–Q3 |
| C01 Schema | DONE | Điều phối (tuần tự) | `ailab/chatbot/schemas.py`, `ailab/test_chatbot_schemas.py`; 63/63 test OK; agent review đạt (lần 3) |
| C02 Hội thoại | DONE | Điều phối + Coder A–E (subagent) | C02_SPEC.md; conversation.py, workflow.py, test_chatbot_conversation.py; 118/118 OK; agent review đạt lần 3 (phạm vi hội thoại) |
| I01 Web/state | DONE | Backend (Opus) + Frontend (Sonnet) + Kiểm thử (Sonnet) | I01_SPEC.md; 142/142 OK; trình duyệt 21/21 PASS (`evidence/chatbot/I01/RESULTS.md`); agent review đạt lần 3 trong phạm vi tích hợp hội thoại; chưa nghiệm thu AI thật |
| C03 Danh mục/model | TODO | Chưa giao | Chưa có |
| C04 Exam | TODO | Chưa giao | Chưa có |
| I02 Lắp ghép | TODO | Điều phối | Chưa có |
| F01 PUT App | TODO | Điều phối/chủ backend | Lỗi đã tái hiện; chưa sửa |
| C05 Game mới | TODO | Chưa giao | Chưa có |
| C06 Kiểm chứng | TODO | Chưa giao | Chưa có |
| C07 Tài liệu | TODO | Chưa giao | Chưa có |
| C08 Chỉnh sửa | TODO | Chưa giao | Chưa có |
| I03 Nghiệm thu | TODO | Điều phối + review | Chưa có |

## Vấn đề mở

| ID | Vấn đề | Xử lý tiếp |
|---|---|---|
| O01 | PUT App bind mapping dict gây HTTP 500 | F01, regression test, patch tối thiểu |
| O02 | Web và eval có hai luồng khác nhau | Lõi chung + adapter I03 |
| O03 | State mới, version, chống trùng chưa có | Quyết định lưu/migration ở G0 |
| O04 | Player có inputs bắt buộc model | Giữ hợp đồng trước; thay đổi chỉ sau duyệt |
| O05 | Shared App có thể chạy Player draft | Không tự sửa chính sách; bot mặc định share=false; phối hợp nhóm |
| O06 | Preview dùng câu hỏi mẫu | I02 dùng đúng Exam và version |
| O07 | Prompt ví dụ contract thiếu click mặc dù yêu cầu chuột | C05/C06 kiểm hành vi; không sửa contract chung ngầm |
| O08 | Chưa có metadata nguồn/giải thích trong Exam chuẩn | Lưu metadata trong chatbot hoặc phương án G0 duyệt, không bịa schema đang tồn tại |
| O09 | Upload PDF/DOCX, OCR và giới hạn chưa chốt | C07/G0, công bố khả năng thật |
| O10 | Chưa gọi AI thật/webcam/browser | I03/C06, cần bằng chứng trước nghiệm thu |
| O11 | Tài liệu nhóm/metric/team còn mẫu | Phối hợp chủ tài liệu; không tự điền số, khóa metric giữ nguyên |
| O12 | `_chat` giữ giao dịch ghi SQLite trong lúc gọi LLM khi tạo chat mới (server.py:453–470) | Sửa trong I01 theo G0 §4 |
| O13 | Danh mục mặc định không có game câu hỏi nào tạo App được không cần model ≥4 lớp | Chờ Q1 trong G0 |
| O15 | Chế độ giả: `TOPIC_CUT` cắt chủ đề ở chữ "có" | Đã sửa (Coder D) + test C02-34, chờ agent review |
| O16 | Câu nói loại game không có cụm đổi bị bỏ qua lặng lẽ, bot không nhắc "nói 'đổi sang…'" | Cần sửa workflow.py ở vòng sau (ngoài phạm vi review lần 2) |
| O14 | `.env` nằm ở git root, `codebase/ai.py` đọc `starter-repo/.env` → server chạy chế độ giả | Chờ Q3 trong G0; không đọc nội dung `.env` |

## Sở hữu file

Chưa có coder được khởi chạy hoặc giao file trong phiên bàn giao. Mặc định file dùng chung do điều phối giữ: `server.py`, `store.py`, `web/app.js`, `llm.py`, `requirements.txt`. Trước mỗi task cập nhật bảng:

| File/phạm vi | Agent | Task | Bắt đầu | Trạng thái bàn giao |
|---|---|---|---|---|
| `ailab/chatbot/__init__.py`, `ailab/chatbot/schemas.py`, `ailab/test_chatbot_schemas.py` (file mới) | Điều phối | C01 | 2026-11-27 | DONE |
| `ailab/chatbot/workflow.py` | Coder A (subagent) | C02 sửa lỗi 1–2 | 2026-11-27 | Bàn giao, điều phối tự review đạt |
| `ailab/chatbot/conversation.py` | Coder B (subagent) | C02 sửa lỗi 3 | 2026-11-27 | Bàn giao, điều phối tự review đạt |
| `ailab/chatbot/conversation.py` | Coder D (subagent, Opus) | C02 review lần 2: chủ đề + đổi loại game | 2026-11-27 | Bàn giao (3 vòng), điều phối tự review đạt |
| `ailab/test_chatbot_conversation.py`, `docs/chatbot/C02_SPEC.md` | Coder E (subagent, Sonnet) | C02 review lần 2: test + spec | 2026-11-27 | DONE |
| `ailab/chatbot_server.py`, `ailab/chatbot/repository.py` (mới); `workflow.py`, `schemas.py` (chỉ thêm `cancel_plan`) | Coder Backend (Opus) | I01 | 2026-11-27 | DONE |
| `ailab/web/chatbot.js` (mới) | Coder Frontend (Sonnet) | I01 | 2026-11-27 | DONE |
| `ailab/test_chatbot_api.py` (mới), bằng chứng trình duyệt `evidence/chatbot/I01/` (mới) | Coder Kiểm thử (Sonnet) | I01 | 2026-11-27 | DONE |
| `ailab/test_chatbot_conversation.py`, `docs/chatbot/C02_SPEC.md` | Coder C (subagent, Sonnet) | C02 test hồi quy + spec | 2026-11-27 | Bàn giao, điều phối tự review đạt |

## Nhật ký quyết định và bằng chứng

Mỗi quyết định ghi: ID, thời điểm Asia/Bangkok, vấn đề, lựa chọn, lý do, người duyệt, task ảnh hưởng. Mỗi lần nghiệm thu ghi: commit/diff, lệnh, kết quả, artifact, người review. Không ghi DONE dựa trên kế hoạch.

### Nhật ký

- 2026-11-27 · Điều phối · Kiểm lại Git: HEAD `faa44a8`, nhánh `feature/chatbot`, không thay đổi tracked. Chạy lại `python -m unittest discover -s ailab -p "test_*.py"`: 27/27 OK (Python 3.13.7). Soạn G0_DECISIONS.md (REVIEW). Chưa sửa mã.
- 2026-11-27 · Người dùng chốt quy tắc **chỉ thêm file mới, không sửa file hiện có**. G0 §7 viết lại: điểm chạy mới `ailab/chatbot_server.py`, UI `web/chatbot.js`; F01 xử lý bằng ghi đè trong server mới, lỗi gốc giữ nguyên cho chủ backend.
- 2026-11-27 · Người dùng đồng ý G0 §7 (server riêng `chatbot_server.py`). Mặc định: làm tuần tự không subagent; dùng chế độ AI giả tới W5 (chưa có bằng chứng AI thật). C01 xong ở mức REVIEW; chỉ thêm file mới, `git status` không có file tracked bị đổi.
- 2026-11-27 · Review C01 lần 1: (1) bộ lọc xoá mọi trường `key` → mất `choices[].key`, `inputs[].key`; (2) blacklist không bảo vệ result/validation/failure.details. Sửa: thay bằng whitelist theo từng cấp + che chuỗi trông như khóa. Thêm 4 test. Bằng chứng: 4 test mới chạy với bộ lọc cũ → 1 ERROR + 2 FAIL; với bản mới → OK. C01 giữ REVIEW.
- 2026-11-27 · Review C01 lần 2 (P2): WARNING thiếu `reason` → mất lý do cờ của `contract.scan()`. Sửa: thêm `reason` vào WARNING (qua `_scalar`/`redact`). Thêm test `test_contract_scan_flags_kept_whole` dùng cờ thật từ `contract.scan()`. Bằng chứng: test mới với schemas.py trước sửa → FAIL (thiếu `reason`); bản mới → 63/63 OK. Git: `git diff --quiet faa44a8` đúng, chỉ có file chưa track. C01 giữ REVIEW; C02 chưa bắt đầu (chờ review đạt). Chưa kiểm: API/trình duyệt (chưa tích hợp).
- 2026-11-27 · Người dùng báo agent review đạt C01 → C01 DONE. Bắt đầu C02, chốt I/O trong C02_SPEC.md.
- 2026-11-27 · C02 → REVIEW. 19 tình huống C02-01…19 có test. Trong lúc làm phát hiện và sửa lỗi chế độ giả: "độ khó dễ" bị hiểu thành Khó. Git: `git diff --quiet faa44a8` đúng, chỉ file chưa track. Chưa kiểm: AI thật (prompt ANALYZE_SYSTEM chưa chạy với provider thật), API/web (I01), chất lượng hiểu tiếng Việt của chế độ giả ngoài các câu trong test.
- 2026-11-27 · Review C02: 3 lỗi (P1 hủy phương án giữ xác nhận; P2 chỉ chuột vẫn chọn hands; P2 vòng quay câu hỏi bị coi là danh sách). Điều phối tái hiện được cả 3 trước khi giao. Giao Coder A (workflow.py) và Coder B (conversation.py) chạy song song bằng subagent; Coder C (test + spec) chờ A/B. C02 giữ REVIEW.
- 2026-11-27 · Coder A, B bàn giao. Điều phối tự review diff + chạy lại 3 tái hiện trên bản gộp: hết lỗi, 93/93 OK, state đầu vào không đổi. Chấp nhận thêm của A: bỏ cảnh báo audio khi chỉ chuột. Vấn đề mở mới O15 (P3, chế độ giả): `TOPIC_CUT` cắt ở chữ "có" → "phép cộng có nhớ" thành "phép cộng". Giao Coder C (Sonnet) test hồi quy + spec.
- 2026-11-27 · Coder C bàn giao 14 test C02-20…33 + spec. Điều phối tự review: không test cũ nào bị xoá (khác biệt duy nhất ngoài phần thêm là C đổi file sang CRLF — P3, chưa chuẩn hoá); 107/107 OK; test mới trên code trước sửa → 8 FAIL + 3 ERROR. `git diff --name-status faa44a8` rỗng. Xin người dùng chuyển Codex review tổng thể C02.
- 2026-11-27 · Commit C01 `d9e7e7a` (chỉ file mới, chưa push). Review C02 lần 2: (1) O15 chủ đề "phép cộng có nhớ" bị cắt; (2) "Tạo game ôn toán lớp 2" → "Đổi sang vòng quay chọn tên học sinh" vẫn hỏi chủ đề (dữ liệu cũ thắng ý định mới). Điều phối tái hiện được cả 2. Giao tuần tự: Coder D (conversation.py) rồi Coder E (test + spec). C02 giữ REVIEW; không commit theo chỉ đạo vòng này.
- 2026-11-27 · Coder D bàn giao lần 1: lỗi 1 (chủ đề) đạt; lỗi 2 đạt ca tái hiện nhưng điều phối tự review phát hiện hồi quy: game câu hỏi đã rõ bị đổi ngầm sang danh sách khi câu chứa "danh sách từ vựng"/"gọi tên các con vật". Trả lại Coder D: chỉ đổi loại khi có cụm đổi tường minh hoặc đang trả lời câu hỏi loại game.
- 2026-11-27 · Coder D bàn giao lần 2–3: chặn đổi loại game khi không có cụm đổi tường minh; câu loại game không bị nhận làm chủ đề. Điều phối tự review: các ca review + hồi quy đạt, state đầu vào không đổi; 106/107 (chỉ test_c02_33 dòng đầu, theo quyết định mới). Giao Coder E (Sonnet) test + spec.
- 2026-11-27 · Coder E bàn giao 11 test C02-34…44 + spec, file test về LF. Điều phối tự review: dòng cũ duy nhất đổi là kỳ vọng dòng đầu test_c02_33 (questions → list, theo quyết định review lần 2); 118/118 OK; test mới trên conversation.py trước sửa → 11 FAIL. Git: so faa44a8 chỉ có file thêm mới. Gửi agent review. Chưa commit (theo chỉ đạo).
- 2026-11-27 · Agent review xác nhận C02 đạt trong phạm vi hội thoại: 118/118 test, các lỗi review trước không còn tái hiện. C02 → DONE, commit theo quy tắc "commit khi DONE". Bắt đầu I01. Vấn đề mở O16 chuyển theo sang vòng sau.
- 2026-11-27 · C02 commit `4430c49`. Chốt I01_SPEC.md (route, bảng `chat_states`/`chat_requests`, repository, UI tiếp quản tab, 17 ca test). Quyết định: mở lại workflow.py/schemas.py chỉ để THÊM `cancel_plan` (nút Hủy cần thao tác tường minh, quy tắc hủy giữ một chỗ). Trình duyệt: phiên không có công cụ MCP; máy có Chrome → kiểm bằng Chrome headless + CDP (script thư viện chuẩn), không cài framework.
- 2026-11-27 · BE/FE bàn giao. Điều phối tự review: workflow/schemas chỉ thêm (`cancel_plan`, `_cancel` dùng chung), 118 OK; chatbot.js nạp trong Chrome headless không lỗi JS. Phát hiện P1: `chatbot_server.py` sập khi stdout ra file (cp1252, UnicodeEncodeError) → Backend sửa `_utf8_streams()`; điều phối kiểm lại: server chạy nền, `/` có `<script src="/chatbot.js">`, 2 lượt chat đúng (clarifying v1 → chỉ hỏi topic), chưa đăng nhập → 401. Giao Coder Kiểm thử.
- 2026-11-27 · Review I01 chưa đạt: (1) FE: phản hồi chậm của chat A cập nhật giao diện/URL sau khi đổi sang B/tạo chat mới/rời tab; (2) BE: replay request đã xử lý vào chat đầy trả 409 chat_full thay vì response đã lưu (điều phối tái hiện: lượt 30 → 200, replay → 409 chat_full); kiểm quyền trước replay; (3) Test: cô lập DB, khôi phục cấu hình, chạy full discovery. Dừng Coder Kiểm thử đang chạy để tránh trùng file; giao song song FE (chatbot.js) và BE (chatbot_server.py, repository.py); Test sau BE. Không còn Chrome/server headless sót lại.
- 2026-11-27 · FE bàn giao (cơ chế `sess`/`inst`/`isLive`, kiểm cú pháp Chrome OK, chưa kiểm phản hồi chậm thật). BE bàn giao (thứ tự quyền → replay → chat đầy; fingerprint, `request_mismatch`). Điều phối tự review BE: replay khi chat đầy → 200 body y hệt; request mới vào chat đầy → 409 chat_full; 135/135 OK. Giao Coder Test: cô lập DB qua `store.DB_PATH`, hồi quy (a)–(g), trình duyệt + ca phản hồi chậm.
- 2026-11-27 · Coder Test bàn giao: 24 test API (I01-01…16 + hồi quy replay a–g), cô lập DB theo lớp qua `store.DB_PATH`, khôi phục cấu hình; discovery 142/142 OK (điều phối chạy lại). Trình duyệt 16/16 PASS gồm 4 ca phản hồi chậm (đổi chat, chat mới, rời tab, chat chưa có id). Điều phối xem ảnh 12: chat B đúng, không lẫn tin A. Quan sát: `ailab/data/ailab.db` có ghi lúc 15:20 (chat id 1 của admin) và 15:32 (player id 3 draft) — schema vẫn cũ, không có bảng `chat_states`/`exams` → không do chatbot_server/test (dùng DB tạm); khả năng do chạy server cũ trên DB thật. Không đụng vào DB này.
- 2026-11-27 · Review I01 lần 2: còn P2 — GET lịch sử chậm về sau POST cùng chat ghi đè messages/state mới. Lưu bản chatbot.js trước sửa (scratchpad i01_r2_before) để làm bằng chứng trước/sau. Giao Coder Frontend: khóa gửi khi đang tải + nút "Thử tải lại" khi lỗi, và chặn áp dụng phản hồi cũ theo số thứ tự request + stateVersion. Coder Test làm sau FE. I01 giữ REVIEW.
- 2026-11-27 · FE bàn giao sửa P2: `loading`/`loadErr`/`locked()`, `reqSeq`/`loadSeq`/`applied`, `verOk()`; nút `button.chatbot-retry`. Kiểm cú pháp Chrome OK; chưa chạy kịch bản chậm. Giao Coder Test: bước trình duyệt 17–21 (GET chậm, thứ tự, GET lỗi + thử lại, chuyển chat/chat mới/rời tab khi đang tải) + chạy TRƯỚC/SAU bằng CDP Fetch phục vụ bản chatbot.js cũ, không sửa file repo.
- 2026-11-27 · Coder Test bàn giao bước 17–21 + chạy trước/sau (CDP Fetch phục vụ chatbot.js cũ). Điều phối tự review: 142/142 OK; bản mới 21/21 PASS; bản cũ FAIL 17 (không khóa, 1 POST lọt), 18b (tin "tin gửi khi đang tải 18b" mất sau khi GET cũ về), 19 (không có "Thử tải lại"); ảnh new_17_loading cho thấy khóa + "Đang tải cuộc trò chuyện…". Không còn tiến trình headless; `ailab/data/ailab.db` không đổi từ 15:32. Gửi agent review.
- 2026-11-27 · Agent review xác nhận I01 đạt trong phạm vi tích hợp hội thoại (kiểm độc lập 142/142, đối chiếu bản sửa + bằng chứng trình duyệt; chưa nghiệm thu AI thật). I01 → DONE, commit theo quy tắc. Bắt đầu C03.
