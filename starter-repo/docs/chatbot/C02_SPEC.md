# C02 — Quản lý hội thoại: I/O và tình huống kiểm thử (chốt trước khi viết mã)

Phạm vi: `ailab/chatbot/conversation.py`, `ailab/chatbot/workflow.py`, `ailab/test_chatbot_conversation.py`. Chỉ hàm thuần (không DB, không HTTP, không sinh HTML). Lưu state, route web là I01.

## Hàm

| Hàm | Vào | Ra |
|---|---|---|
| `conversation.merge_requirements(old, patch)` | TeacherRequirements + bản vá đã kiểm (schemas) | Requirements **mới**; trường vắng mặt giữ nguyên, `null` tường minh đặt null; không sửa `old` |
| `conversation.find_missing_fields(req, catalog=None)` | Requirements | Danh sách trường thiết yếu còn thiếu, theo thứ tự hỏi |
| `conversation.default_assumptions(req)` | Requirements | Giả định mặc định cần giáo viên xác nhận (vd "10 câu") — không ghi vào requirements |
| `conversation.diff_requirements(old, new)` | 2 requirements | `changes[]` dạng chữ cho giáo viên |
| `conversation.fake_analyze(text, state)` | Tin nhắn + state | Đầu ra cùng dạng JSON của LLM (quy tắc từ khóa). Luôn gắn nhãn giả |
| `conversation.analyze_turn(text, state, context)` | + `context.call_model` (tùy chọn) | `{output, simulated, model, calls, failure}`; LLM sai JSON → sửa tối đa 1 lần (≤ 2 lời gọi) |
| `workflow.process_turn(request, state, context)` | request (schemas.validate_request), state hiện tại | `(new_state, reply_text, meta)`; meta có `failure`, `simulated`, `model`, `calls` |
| `workflow.confirm_plan(state, proposalId, version)` | Xác nhận tường minh | `(new_state, failure)`; sai bản → `stale_version`, sai id → `invalid_input` |

`context = {call_model: (system,user)->{text,model,...} | None, history: [{role,text}], catalog: {...} | None, new_id: () -> str}`. Không có `call_model` → chế độ giả, `simulated=True`, `model="fake-rules"`.

## Quy tắc

- Trường thiết yếu (game câu hỏi): `subject`, `gradeOrAudience`, `topic`. Có `contentSource.kind=existing_exam` + `examId` hoặc `provided_questions` → không cần subject/topic. Có tài liệu → không cần topic.
- Game danh sách (vòng quay, bốc thăm, chọn tên; hoặc Player trong catalog có `content.kind=texts`): không hỏi môn/lớp/số câu.
- `questionCount` thiếu → giả định 10 câu, ghi `assumptions`, không ghi vào requirements.
- Mỗi lượt: `state.version` +1 khi state đổi. `expectedVersion` sai → `stale_version`, không gọi AI, state giữ nguyên.
- Đủ thông tin → `awaiting_confirmation` + proposal `plan_v2` (version 1). Requirements đổi sau đó → proposal.version +1, `changes[]`, xóa `confirmations`. Không đổi → giữ version.
- `intent=new_request` → requirements làm lại từ đầu, proposalId mới.
- "đồng ý" bằng chữ **không** xác nhận: bot nhắc bấm nút đúng phiên bản. Chỉ `confirm_plan` ghi xác nhận.
- Lỗi AI (exception / JSON hỏng 2 lần) → state giữ nguyên, `failure` (`model_unavailable` retryable / `invalid_model_output`).
- Audio → cảnh báo `unsupported_interaction`, chuột vẫn bật.
- Không gọi sinh HTML, không tạo Player/Exam/App; proposal chưa chọn Player/Exam/Model thật (C03/C04).
- Câu trả lời cho giáo viên do workflow soạn từ state (không để LLM tự hỏi lại trường đã có).

## Tình huống kiểm thử

| ID | Tình huống | Kỳ vọng | Map |
|---|---|---|---|
| C02-01 | "Tạo game ôn toán" | clarifying; subject=Toán; hỏi lớp + chủ đề; không proposal | T01 |
| C02-02 | 3 lượt: ôn toán → lớp 2 → phép cộng, 10 câu | Lượt 2 chỉ hỏi chủ đề; lượt 3 ra proposal; không hỏi lại | T02 |
| C02-03 | Đủ thông tin ngay | awaiting_confirmation, không câu hỏi | T03 |
| C02-04 | Sửa "đổi thành 15 câu" | questionCount=15, trường khác giữ, proposal v2, changes, xóa xác nhận | — |
| C02-05 | "Yêu cầu mới: tiếng Anh lớp 5…" | requirements làm lại, proposalId mới | — |
| C02-06 | Vòng quay chọn tên | không hỏi môn/lớp/số câu; proposal | — |
| C02-07 | Lượt không nhắc trường cũ | không mất dữ liệu cũ | — |
| C02-08 | Gõ "đồng ý" | không xác nhận; nhắc bấm nút | — |
| C02-09 | confirm_plan đúng / sai version / sai id | ghi xác nhận / stale_version / invalid_input | T20 |
| C02-10 | Xác nhận rồi sửa | xác nhận bị hủy, version tăng | T20 |
| C02-11 | AI trả JSON hỏng 1 lần / 2 lần | sửa được (2 lời gọi) / invalid_model_output, state giữ | T37 |
| C02-12 | AI ném lỗi | model_unavailable retryable, state giữ | T37 |
| C02-13 | expectedVersion cũ | stale_version, không gọi AI | T20 |
| C02-14 | Chế độ giả | simulated=True, model=fake-rules | T40 (không phải bằng chứng thật) |
| C02-15 | AI tự đặt duyệt/ready | bị bỏ; status không ready | — |
| C02-16 | Yêu cầu dùng giọng nói | cảnh báo audio chưa hỗ trợ; mouse=True | T10 |
| C02-17 | Thiếu số câu | assumption 10 câu; questionCount vẫn null | — |
| C02-18 | Toàn luồng | không html trong state/reply; không gọi generator | T06 phần hội thoại |
| C02-19 | Ngoài phạm vi | requirements không đổi | — |
| C02-20 | Hủy phương án trước khi xác nhận ("không đồng ý, hủy phương án này") | needs_revision; proposal.status=cancelled; proposal.version giữ; confirmations={}; state.version+1; requirements không đổi; reply không có "đã xác nhận" | `CancelPlan.test_c02_20` |
| C02-21 | Hủy sau khi đã xác nhận | như C02-20; xác nhận bị xóa | `CancelPlan.test_c02_21` |
| C02-22 | Hủy khi đã hủy / chưa có phương án | state y nguyên (version không đổi) | `CancelPlan.test_c02_22` |
| C02-23 | `confirm_plan` vào bản đã hủy | `stale_version`, message "đã bị hủy", state không đổi | `CancelPlan.test_c02_23` |
| C02-24 | Sau hủy: "đồng ý" / lượt không đổi yêu cầu | giữ needs_revision + cancelled, không xác nhận | `CancelPlan.test_c02_24` |
| C02-25 | Sau hủy: "đổi thành 15 câu" | awaiting_confirmation, cùng proposalId, version+1, changes "Số câu: 10 → 15"; bản cũ bị từ chối, bản mới xác nhận được | `CancelPlan.test_c02_25` |
| C02-26 | `new_request` sau hủy | proposalId mới, version 1 | `CancelPlan.test_c02_26` |
| C02-27 | hands → "không dùng camera, chỉ dùng chuột" → "chơi bằng bàn tay" | v2 interactionModel không model/mapping, mouse=True, useModel=False, xóa xác nhận; v3 kind=hands, chờ xác nhận lại; state vào không bị sửa | `MouseOnly.test_c02_27` |
| C02-28 | useModel=False + audio | không cảnh báo `unsupported_interaction` | `MouseOnly.test_c02_28` |
| C02-29 | "Tạo vòng quay câu hỏi trắc nghiệm toán lớp 2, 10 câu" | hỏi `topic`; trả lời chủ đề → reason "Game ôn tập…" | `GameKind.test_c02_29` |
| C02-30 | "Làm vòng quay chọn tên học sinh gọi lên bảng" | không ép bộ đề, missing=[] | `GameKind.test_c02_30` |
| C02-31 | "Tạo vòng quay" | hỏi `gamePreference`; "quay câu hỏi" → hỏi subject/lớp/chủ đề; "chọn tên học sinh" → proposal | `GameKind.test_c02_31` |
| C02-32 | Catalog: manifest quyết định loại game | texts → list; questions=exam → questions | `GameKind.test_c02_32` |
| C02-33 | Thứ tự tín hiệu `game_kind` | subject thắng "chọn tên"; "bốc thăm" → list; chỉ "vòng quay" → None; rỗng → questions | `GameKind.test_c02_33` |
| C02-34 | TOPIC_CUT không cắt ở "có" | "phép cộng có nhớ", "…không nhớ", "…trong phạm vi 100", "phép chia có dư" giữ nguyên | `TopicKeep.test_c02_34` |
| C02-35 | Đổi chủ đề tường minh | "chủ đề phép trừ có nhớ" → topic mới | `TopicKeep.test_c02_35` |
| C02-36 | Trả lời chủ đề trần | "Từ láy và từ ghép" → topic | `TopicKeep.test_c02_36` |
| C02-37 | Đổi sang vòng quay rồi quay lại | list giữ subject/lớp, reason "Game danh sách"; "thôi, quay câu hỏi phép cộng" → questions | `GameSwitch.test_c02_37` |
| C02-38 | Loại đã rõ, không có cụm đổi ("lấy từ danh sách…") | giữ questions, giữ topic | `GameSwitch.test_c02_38` |
| C02-39 | "gọi tên các con vật bằng tiếng anh" không đổi; "chuyển sang bốc thăm…" đổi | questions/động vật; rồi list | `GameSwitch.test_c02_39` |
| C02-40 | "vòng quay chọn tên" không có cụm đổi | state y nguyên, vẫn hỏi topic; "Đổi sang…" → proposal | `GameSwitch.test_c02_40` |
| C02-41 | Game danh sách + "thêm câu hỏi phụ" | vẫn list | `GameSwitch.test_c02_41` |
| C02-42 | Player đã chọn mâu thuẫn loại mới (`gameConflict`) | hỏi cố định; "chọn game khác" → playerId None, list; "giữ game đã chọn" → playerId 8, questions | `GameConflict.test_c02_42..44` |

## Quy tắc bổ sung (hủy, chỉ chuột, loại game)

- `reject_intent` khi có proposal chưa hủy: `status=needs_revision`, `proposal.status=cancelled`, `proposal.version` giữ nguyên, `confirmations={}`, `state.version`+1, requirements không đổi. Đã hủy hoặc chưa có proposal: state y nguyên.
- `confirm_plan` vào bản cancelled → `stale_version` ("đã bị hủy"). Sau hủy, "đồng ý" hoặc lượt không đổi requirements giữ needs_revision. Lượt đổi requirements → `awaiting_confirmation`, cùng proposalId, version+1, có `changes`, phải xác nhận lại. `new_request` → proposalId mới, version 1.
- Chỉ chuột: `interaction.useModel=False` → `interactionModel={modelId:None, kind:None, mapping:{}, mouse:True}`, assumption "Chỉ chơi bằng chuột, không dùng camera.", không cảnh báo audio. Giáo viên nói lại cách chơi bằng model → proposal version+1, cần xác nhận lại.
- `conversation.game_kind(req, catalog)` → `"questions"|"list"|None`, thứ tự: (1) Player trong catalog có manifest không rỗng quyết định (`questions=="exam"` hoặc `content.kind=="questions"` → questions; `content.kind=="texts"` → list; manifest khác → questions), không đổi playerId; (2) mô tả có tín hiệu câu hỏi (câu hỏi/trắc nghiệm/quiz/đáp án/ôn tập/đề) → questions; (3) mô tả có tín hiệu danh sách (chọn tên, gọi tên, bốc thăm, danh sách…) → list, thắng subject/topic/questionCount cũ; (4) mô tả mơ hồ ("vòng quay"/"wheel") → questions nếu dữ liệu có tín hiệu câu hỏi (questionCount/topic/subject, contentSource existing_exam/provided_questions/document), ngược lại None → `find_missing_fields` trả `["gamePreference"]`, hỏi `FIELD_QUESTIONS["gamePreference"]`; (5) không mô tả → questions.
- Chỉ đổi loại game khi có cụm đổi tường minh (đổi sang, chuyển sang, thay bằng, đổi thành, "thôi, …") hoặc khi đang trả lời câu hỏi loại game (`gamePreference`). Loại đã rõ mà không có cụm đổi → không đổi loại, không ghi đè topic.
- `gameConflict`: Player đã chọn (`playerId`) mâu thuẫn loại game của mô tả mới → `clarifying`, missingFields `["gameConflict"]`, playerId giữ nguyên, hỏi `FIELD_QUESTIONS["gameConflict"]`. "chọn game khác" → playerId None, theo loại mới; "giữ game đã chọn" → description None, giữ playerId.
- Topic cũ được giữ, chỉ đổi khi giáo viên nói "chủ đề…", "đổi/sửa/thay…", hoặc đang trả lời câu hỏi topic. `TOPIC_CUT` chỉ cắt ở dấu phẩy/chấm phẩy/xuống dòng, "cho lớp", "lớp <số>", "(có )<số> câu", "độ khó", cụm điều khiển (chơi bằng…, bằng/dùng + bàn tay/chuột/camera/cử chỉ/giọng…) và "game/vòng quay/trắc nghiệm/quiz" sau chủ đề.

## Hạn chế đã biết

- Câu loại game không có cụm đổi bị bỏ qua lặng lẽ: bot vẫn hỏi chủ đề, không nhắc "nói 'đổi sang…'" (cần workflow ở vòng sau).
- Nhắc lại chủ đề không có "chủ đề/đổi/sửa/thay" thì không cập nhật topic.
- `fake_analyze` không xét manifest khi xác định loại game hiện tại.
- Câu hỏi `gameConflict` cố định, không nêu tên game.
- Chủ đề có "<số> câu" bên trong (vd "giải 3 câu đố") vẫn bị cắt.
