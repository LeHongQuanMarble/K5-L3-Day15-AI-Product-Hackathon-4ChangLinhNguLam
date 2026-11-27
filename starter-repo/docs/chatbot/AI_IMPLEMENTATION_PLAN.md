# Kế hoạch giao việc cho agent coder

## Cổng và trình tự

G0 thiết kế → W1 hội thoại → W2 tái sử dụng chạy trọn → W3 sinh game mới → W4 tài liệu/chỉnh sửa → W5 nghiệm thu tổng.

Mỗi đợt phải được agent review kiểm tra trước khi nghiệm thu. Không commit/push tự động. Không tuyên bố hoàn thành toàn bộ ở W2; đây chỉ là luồng tối thiểu.

## G0 — Chốt bản triển khai cụ thể

Điều phối đọc lại mã và tài liệu, báo cáo diff từ mốc `faa44a8`, rồi lập bảng quyết định:

1. Cấu trúc state, schema phản hồi, chuyển đổi dữ liệu hội thoại/proposal cũ.
2. Cách lưu state/version và chống trùng có migration không mất dữ liệu.
3. Cách xác nhận rõ ràng, route mới/cũ và kiểm quyền mỗi hành động.
4. Lưu nguyên tử; tránh hàm commit nội bộ phá giao dịch; không giữ giao dịch khi gọi AI.
5. Giới hạn upload/LLM/context, định dạng tài liệu, chính sách lưu/xóa nguồn.
6. Cách tạo bằng chứng runtime/chuột cho từng bản game; không tự nhận kiểm thử đã đạt.
7. Phạm vi sửa tích hợp ở server/store/app.js/preview; bản sửa lỗi PUT App riêng.

Trình agent review, rồi trình người dùng các thay đổi dùng chung/hợp đồng cần xác nhận theo handoff. Chuẩn bị thiết kế/patch review được trước khi hỏi; không yêu cầu phê duyệt mơ hồ. Những việc chưa phụ thuộc quyết định vẫn tiếp tục được.

## Nhiệm vụ

Tên hàm/module là đề xuất; coder không tự đổi I/O bên ngoài. Mỗi nhiệm vụ phải có kiểm thử cùng patch. File dùng chung do điều phối tích hợp, trừ khi giao độc quyền cho một coder.

### C01 — Schema và bộ chuyển đổi

- Mục tiêu: thống nhất đầu vào/đầu ra và kiểm cấu trúc không cần framework lớn.
- File: `ailab/chatbot/schemas.py`, `__init__.py`, `ailab/test_chatbot_schemas.py`.
- Hàm: `validate_request(payload)->request/errors`; `validate_model_output(raw)->proposal/errors`; `normalize_requirements(data)->requirements`; `to_public_reply(state)->reply`.
- Logic: whitelist trường; kiểm kiểu/range/enum; tách lỗi text cũ; không cho model xác lập approval/ID kết quả.
- Phụ thuộc: G0.
- Test: thiếu/null/sai kiểu, JSON hỏng, lựa chọn/ID bất hợp lệ, phản hồi cũ.
- Nghiệm thu: mọi trạng thái API được serialize; không lộ HTML/key; giữ client cũ không crash.

### C02 — Quản lý hội thoại

- File: `ailab/chatbot/conversation.py`, `workflow.py`, `ailab/test_chatbot_conversation.py`.
- Hàm: `analyze_turn(text,state,context)->patch/intent`; `merge_requirements(old,patch)->new`; `find_missing_fields(req)->fields`; `process_turn(request,context)->state/reply`.
- Logic: chỉ hỏi phần thiết yếu; giữ lựa chọn cũ; phân biệt chỉnh sửa và yêu cầu mới; plan có version; không sinh HTML khi đang hỏi.
- Phụ thuộc: C01.
- Test: nhiều lượt, đủ thông tin ngay, đổi chủ đề, không áp dụng Exam với game danh sách, đầu ra AI lỗi.
- Nghiệm thu: ví dụ giáo viên “ôn toán” → lớp/chủ đề → số câu/cách chơi → phương án xác nhận, không lặp câu đã trả lời.

### I01 — Tích hợp chat web và lưu state

- File độc quyền điều phối: phần `_chat/_proposal` của `ailab/server.py`, phần chat `ailab/web/app.js`, state repository trong `ailab/chatbot/repository.py`; `store.py` chỉ theo G0 duyệt; `ailab/test_chatbot_api.py`.
- Hàm: `load_state(chatId,user)->state`; `save_state(expectedVersion,state,requestId)->state/conflict`; handler xác nhận phiên bản; `renderChatReply(reply)` ở UI.
- Logic: auth, migration được duyệt, bảo toàn hội thoại cũ, ghi optimistic version (chỉ ghi nếu phiên bản còn khớp), UI hiển thị câu hỏi và phương án.
- Phụ thuộc: C01–C02.
- Test: tải lại trang, chat cũ, truy cập chéo user, request trùng, hai lượt đồng thời, stale confirmation.
- Nghiệm thu W1: hỏi bổ sung hoạt động thật trong tab; chưa tự tạo App; lỗi không mất lịch sử.

### C03 — Danh mục, định tuyến và chọn model

- File: `ailab/chatbot/catalog.py`, `ailab/test_chatbot_catalog.py`.
- Hàm: `route_game(requirements,catalog)->route`; `select_model(manifest,models,preference)->selection/conflict`; `validate_mapping(manifest,model,mapping)->checks`.
- Input: danh mục được server lọc quyền; output: ID từ danh mục, lý do và cấu hình.
- Logic: chọn game rõ ràng có ưu tiên; lọc kind/role/số lớp; audio unsupported; mouse luôn true; không tạo HTML.
- Phụ thuộc: C01; có thể làm song song C02 trên file riêng.
- Test: ID bịa, model riêng tư, hands 2 action với game 4 input, lớp trùng, thiếu model, game chuột không cần model.
- Nghiệm thu: mọi selection qua lại `clean_app` được khi tích hợp; xung đột phải được giải thích.

### C04 — Bộ đề và kiểm nội dung

- File: `ailab/chatbot/exams.py`, `ailab/test_chatbot_exams.py`.
- Hàm: `prepare_exam(req,sources,existing)->examDraft`; `validate_exam_questions(draft)->checks`; `serialize_exam(draft)->content`; `review_grounding(draft,sources)->findings`.
- Logic: single/truefalse; 2–6 lựa chọn; đáp án hợp lệ; kiểm rỗng/trùng; nguồn từng câu; parse lại bằng store; không dùng LLM tự chấm làm chứng nhận đúng tuyệt đối.
- Phụ thuộc: C01; nguồn tài liệu có thể dùng fixture trước C07.
- Test: dấu phân cách, xuống dòng, đáp án sai, số câu, câu trùng, nguồn thiếu, chọn Exam thực tế.
- Nghiệm thu: dữ liệu qua `clean_exam/parse_questions`; UI có thể duyệt nội dung/đáp án; câu không chắc bị đánh dấu.

### I02 — Tái sử dụng, duyệt và lắp ghép

- File độc quyền điều phối: `repository.py`, phần chat API/UI, preview trong `app.js`, tests API.
- Hàm: `build_proposal(req,route,exam,selection)->proposal`; `preview_proposal(id,version,user)->securedData`; `accept_result(id,version,key,user)->GameResult`; `compose_app(artifacts,user)->appId`.
- Logic: xem thử đúng Exam; kiểm quyền/version lại; lưu kết quả nguyên tử; chống trùng; share=false; không sửa Player gốc. Không gọi HTTP ngược vào chính server nếu gọi hàm service được.
- Phụ thuộc: I01, C03–C04; G0 về giao dịch.
- Test: hai accept đồng thời, rollback khi tạo App lỗi, không lộ private resource, hash HTML trước/sau, teacher reject không tạo App.
- Nghiệm thu W2: hội thoại → game có sẵn → đề/model → duyệt → App → chuột chơi được; không gọi HTML generator.

### F01 — Lỗi PUT App hiện có

- File: đúng nhánh PUT trong `ailab/server.py`, kiểm thử hồi quy trong test API; điều phối sửa/tích hợp khi được xác nhận phạm vi.
- Hàm/I-O: giữ API `PUT /api/apps/<id>`; chuyển mapping sang JSON khi bind SQL, tương tự POST.
- Phụ thuộc: có thể chuẩn bị patch sớm; phải xong trước nghiệm thu revision.
- Test: cập nhật App có/không model, giữ mapping sau đọc lại, đổi examId, lỗi đầu vào không làm đổi bản cũ.
- Nghiệm thu: PUT không còn 500; dữ liệu đọc lại đúng; không đổi hợp đồng chung khác.

### C05 — Sản xuất game mới

- File: `ailab/chatbot/production.py`, phần sinh HTML trong `llm.py`, tests riêng; không cùng sửa llm.py với coder khác.
- Hàm: `reuse_player(player)->artifact`; `generate_player(plan,examSchema,modelCapabilities)->draft`; `repair_player(draft,findings)->draft`.
- Logic: context chỉ schema Exam và khả năng thực, không hardcode câu hỏi; mouse action cùng hàm model action; không khóa khởi động chờ camera; tối đa 2 lượt HTML.
- Phụ thuộc: C01, C03–C04, I02.
- Test: reuse generator 0 lần, manifest thiếu, game gọi mạng, không có chuột, dữ liệu đề đổi vẫn dùng cùng game.
- Nghiệm thu: HTML hợp đồng đạt; không sửa Player gốc; game lỗi không ready; preview trước duyệt.

### C06 — Bộ kiểm chứng và sandbox

- File: `ailab/chatbot/validation.py`, `ailab/test_chatbot_validation.py`, bộ kiểm thử trình duyệt riêng theo G0; không sửa contract/runtime chung chưa duyệt.
- Hàm: `validate_bundle(bundle,context)->ValidationResult`; `check_compatibility(...)->checks`; `collect_runtime_evidence(proposalVersion,scenarioResults)->checks`.
- Logic: kiểm quyền/schema/nội dung/manifest/ánh xạ, an toàn, runtime, chuột và duyệt; regex chỉ cảnh báo, không đảm bảo an toàn đầy đủ. Kết quả not_checked ngăn ready khi check bắt buộc.
- Phụ thuộc: C01; C03–C05 để tích hợp.
- Test: camera denied/loading/model-failed/off, đổi điều khiển giữa game, click+model cùng lúc không chấm hai lần, JS lỗi/không finish, kiểm tra giả không được đánh passed.
- Nghiệm thu W3: game mới chạy trong sandbox với Exam thật, chuột hoạt động và có bằng chứng; runtime/model thật được phân biệt với mock.

### C07 — Tiếp nhận tài liệu

- File: `ailab/chatbot/documents.py`, tests tài liệu; endpoint/upload và UI do điều phối tích hợp độc quyền.
- Hàm: `validate_document(fileMeta,bytes)->accepted/error`; `extract_document(...)->segments`; `normalize_segments(...)->sources`; `get_document_for_user(id,user)->document`.
- Logic: TXT/nội dung dán, sau đó PDF/DOCX; giới hạn tài nguyên; nguồn trang/đoạn; không thực thi/tải URL tùy ý; nội dung tài liệu không làm chỉ dẫn hệ thống. Chọn thư viện tối thiểu và ghi requirements nếu cần.
- Phụ thuộc: C01, G0 upload/lưu trữ; C04 để tích hợp.
- Test: file quá lớn, giả đuôi, rỗng, PDF scan, tài liệu hỏng, prompt injection, truy cập tài liệu user khác, xóa/hết hạn nguồn.
- Nghiệm thu: trích xuất có nguồn; unsupported báo rõ; không ghi nội dung bí mật vào log; các định dạng còn thiếu vẫn TODO.

### C08 — Chỉnh sửa có chọn lọc

- File: `ailab/chatbot/workflow.py`/`conversation.py` do coder sở hữu trong đợt này, tests revision; API/store do điều phối.
- Hàm: `classify_revision(text,state)->affectedParts`; `revise_proposal(...)->newVersion/changes`; `apply_app_revision(...)->result` qua repository.
- Phụ thuộc: F01, I02, C05–C07 theo loại sửa.
- Test: đổi Exam giữ hash Player, đổi model giữ câu hỏi, Exam dùng chung không bị sửa ngầm, sửa cơ chế tạo bản riêng, xác nhận cũ bị từ chối.
- Nghiệm thu W4: sửa đúng phần, trình changes và duyệt lại, không mất điểm trong phiên chuyển điều khiển.

### I03 — Đánh giá và đóng gói tích hợp

- File: `codebase/agent.py` adapter lõi chung, tests session, docs hướng dẫn; không sửa runner/trace/metric đã khóa.
- Hàm: giữ `answer(text)->{"output":str}`, thêm adapter context kiểm thử rõ ràng nếu cần; không tạo dữ liệu thật khi eval.
- Phụ thuộc: toàn bộ nhiệm vụ trước.
- Test: regression, API, browser, multi-turn, model thật, chi phí/token, lỗi provider; chạy 2 lượt đánh giá đúng quy trình.
- Nghiệm thu W5: người ngoài có thể chạy từ hướng dẫn; có bằng chứng hai nhánh và revision; báo cáo giới hạn trung thực; agent review nghiệm thu.

## Điều phối song song

- W1: C01 trước; C02 và C03 có thể song song khi C01 ổn định. C04 chỉ song song nếu schema nguồn/đề đã thống nhất.
- W3: C05 và C06 có thể làm file riêng theo interface đã khóa; không cho sửa contract chung để làm test dễ qua.
- W4: C07 có thể chuẩn bị bằng fixture trong khi C08 làm revision, nhưng workflow.py chỉ có một chủ sở hữu.
- `server.py`, `store.py`, `web/app.js`, `llm.py`, `requirements.txt` phải có khóa sở hữu ghi trong AI_PROGRESS. Mặc định điều phối giữ file dùng chung.
- Khi giao agent: gửi mã task, commit nền, file được sửa, interface, test, acceptance và file cấm. Nếu có worktree thì tích hợp tuần tự sau review; nếu chung workspace không sửa chung file.

## Hoàn thành mỗi đợt

Coder gửi diff + test thật → điều phối tích hợp và chạy kiểm tra → review độc lập → sửa lỗi và kiểm lại → cập nhật tiến độ. Nếu thiếu bằng chứng, trạng thái REVIEW hoặc TODO, không DONE.
