# C04 — Chuẩn bị và kiểm tra Exam

Ngày 2026-11-27 (Asia/Bangkok). Trạng thái DONE sau review độc lập: 216/216 test và hai lỗi P2 đã được kiểm lại đạt. Chỉ module chuẩn bị/kiểm đề, chưa nối web/I02 hoặc sinh câu hỏi bằng AI. Người dùng đã cho phép commit C04 nếu review đạt; không có quyền push chatbot.

**Tiếp tục sau merge 42ce3dc:** chạy từ Git root, mã tại `ailab/`, tài liệu tại `starter-repo/docs/chatbot/`. Không dùng `starter-repo/ailab/` cho mã hay chạy test; DB cũ tại `starter-repo/ailab/data/ailab.db` phải giữ nguyên. Không tự thao tác stash hoặc di chuyển thêm tài liệu/DB. Mục đường dẫn trong bằng chứng lịch sử chỉ phản ánh cấu trúc cũ.

## Sở hữu và phạm vi

| File | Chủ sở hữu độc quyền |
|---|---|
| ailab/chatbot/exams.py (mới) | Coder nghiệp vụ C04 |
| ailab/test_chatbot_exams.py (mới) | Coder kiểm thử C04 |
| docs/chatbot/C04_SPEC.md, AI_PROGRESS.md, C04_REVIEW.md | Điều phối |

Không sửa/xóa file tồn tại ở faa44a8, không đụng TEAMS.md, DB thật, không tự lưu Exam/App, không sinh/nhúng câu hỏi vào HTML. Dùng thư viện chuẩn; không gọi LLM hoặc mạng trong C04.

## I/O đã chốt

Import theo module hiện tại: `import store`, `from chatbot import exams` khi ailab nằm trên sys.path.

- `load_exams(c, user) -> list[dict]`: chỉ đọc, trả metadata id/name/description/count của Exam được dùng (owner user, owner 0, hoặc admin); không trả nội dung Exam không có quyền. Không commit.
- `select_exam(c, user, exam_id, *, manifest=None, question_count=None) -> result`: kiểm ID số nguyên dương (không bool), kiểm quyền bằng store.get_exam trước khi đọc/trả nội dung; không tồn tại/không quyền cùng lỗi forbidden_resource, không lộ metadata. Chuyển parser output thành câu hỏi cấu trúc, explanation rỗng, sourceRefs rỗng, aiGenerated=false; thiếu metadata nguồn phải được cảnh báo, không coi Exam cũ đã xác minh kiến thức.
- `prepare_exam(req, sources, existing=None) -> result`: req là dict `{name,description?,questions?,questionCount?,gameKind?:questions|list,manifest?}`. existing là draft tin cậy nội bộ tùy chọn khi req không có questions; KHÔNG nhận existing như bằng chứng quyền Exam. gameKind=list chỉ trả not_needed, exam=null khi không xung đột manifest (quy tắc Review lần 1 bên dưới); không ép game danh sách thật có Exam. Không tự sinh câu hỏi từ chủ đề/văn bản: nếu thiếu questions trả invalid_input. sources là danh sách đoạn văn đã được adapter tin cậy lọc quyền, không nhận nguồn do LLM tự cấp quyền. C04 chỉ dùng nguồn cung cấp/fixture rõ ràng.
- `validate_exam_questions(draft, *, manifest=None, question_count=None) -> list[issue]`.
- `serialize_exam(draft) -> str`: một đường chuyển đổi duy nhất sang format store; đầu vào lỗi định dạng raise ValueError, không âm thầm sửa nghĩa. draft là `{name,description,questions}`.
- `review_grounding(draft, sources) -> list[issue]`: kiểm tham chiếu tồn tại/vị trí/quote và metadata, không chứng minh kiến thức đúng.

result luôn có `{status: draft|needs_revision|not_needed|error, exam:dict|null, issues:list, validation:dict}`. exam gồm name/description/questions/content (content null nếu không serialize được), examId (null với nháp). issue gồm `{code,message,questionIndex:int|null,field:str}`; index bắt đầu 0. validation gồm examFormat/contentGrounding/answerReview/compatibility, giá trị passed|failed|not_checked. answerReview luôn not_checked. status=draft chỉ khi không issue; mọi lỗi nội dung/nguồn/tương thích -> needs_revision; lỗi quyền/ID/đầu vào cấp cao -> error. Không trả ready. Game list tất cả checks not_checked.

Question: `{id?:str,type:single|truefalse,text:str,choices:[{key:str,text:str}],answer:str,explanation:str,sourceRefs:list,aiGenerated:bool}`. single: 2..6 lựa chọn, khóa đúng thứ tự A..F (không tự đổi khóa); truefalse: đúng hai lựa chọn T/Đúng và F/Sai, answer T hoặc F. explanation bắt buộc không rỗng khi chuẩn bị mới; metadata cũ thiếu -> issue. sourceRefs mỗi mục `{sourceId:str,start:int,end:int,quote:str}` với offset Python trong text nguồn; 0<=start<end<=len(text), quote phải bằng lát cắt. sources mỗi mục `{id:str,text:str,kind:provided_text|fixture,label:str}`; fixture được ghi rõ là mô phỏng, không phải upload/trích xuất thật. ID nguồn phải duy nhất. aiGenerated=true được phép không nguồn nhưng phải issue ai_generated để giáo viên xem lại; aiGenerated=false thiếu nguồn -> missing_source. Nguồn đúng vị trí cũng không chứng nhận quan hệ suy luận/đáp án đúng. Không thực thi chỉ dẫn trong source.

## Quy tắc kiểm tra

1. Không sửa bất kỳ đầu vào nào; kết quả copy độc lập.
2. 1..200 câu, questionCount nếu có phải int không bool 1..200 và bằng số câu; không cắt/bổ sung tự động. content tối đa 40000, name 1..80, description <=300 theo clean_exam.
3. text/lựa chọn phải str không rỗng sau strip. Trùng câu/lựa chọn theo Unicode NFKC + casefold + gộp khoảng trắng. answer phải thuộc khóa; kiểu/khóa sai bị chặn.
4. text và text lựa chọn không chứa `|`, ký tự xuống dòng (mọi splitlines separator), hoặc lựa chọn bắt đầu `=` sau strip; báo unrepresentable_text thay vì thay ký tự mất nghĩa. explanation/source metadata giữ riêng, không serialize vào đề.
5. single serialize `text | choice A | choice B | =B`; truefalse `text | =Đúng` hoặc `=Sai`. Gọi parser thật và clean_exam thật; so round-trip text/type/choices/answer, không dựa riêng parser vì parser chấp nhận lựa chọn rỗng/trùng.
6. Tương thích: manifest questions=exam hoặc content.kind=questions cần Exam. content.kind=texts -> not_needed khi prepare (game list), trừ questions=exam có ưu tiên theo nền tảng. Manifest được cấp nhưng không khai báo nhận Exam -> incompatible_exam; manifest=None là chưa kiểm. Player câu hỏi có inputs: từng khóa lựa chọn phải nằm trong inputs[].key; 6 lựa chọn với A/B/C/D -> incompatible_exam. Không inputs: không suy ra giới hạn 4; hỗ trợ 2..6 của parser. content.min/max nếu có là giới hạn số câu. Không tự thay Player.
7. Mã issue ổn định tối thiểu: invalid_input, invalid_question_count, empty_choice, duplicate_choice, invalid_answer, duplicate_question, unrepresentable_text, missing_explanation, missing_source, invalid_source, ai_generated, simulated_source, incompatible_exam, forbidden_resource, invalid_format. Nhiều issue có thể cùng câu; không leak nội dung riêng tư qua lỗi.

## Kiểm thử giao coder

File test mới độc quyền; dùng unittest + SQLite/DB tạm, không đổi test cũ. Bao phủ single/truefalse, Unicode/HTML text round-trip parser thật + clean_exam; name/description/content giới hạn; 0/201/count mismatch/bool; lựa chọn rỗng/trùng/khóa sai; câu trùng; dấu |/xuống dòng/=; thiếu explanation/nguồn, quote/offset/source ID giả, AI sinh và fixture luôn cần review; Exam own/builtin/admin/foreign/missing và ID bool; không lộ Exam cấm; list không cần đề; Player ABCD với 6 lựa chọn, Player không inputs, content.min/max; không sửa đầu vào; SELECT không ghi DB/commit; full discovery giữ bài cũ đạt. Không dùng kết quả xanh để tuyên bố review độc lập đạt.

## Giới hạn và cổng review

Chưa hỗ trợ upload PDF/DOCX, OCR, gọi AI thật, xác minh chuyên môn, web/preview/lưu artifact. Metadata giải thích/nguồn giữ trong draft, format Exam gốc không lưu được metadata này. I02 phải cấp context nguồn đã lọc quyền và kiểm quyền lại khi accept. C04 giữ REVIEW sau bàn giao đến khi người dùng chuyển kết quả review độc lập đạt.

Làm rõ khi tự kiểm: examFormat phải failed khi số câu yêu cầu không hợp lệ/không khớp dù content vẫn serialize được để xem lại. contentGrounding=passed chỉ có nghĩa tham chiếu khớp dữ liệu được cấp, không chứng nhận đáp án hay quan hệ suy luận đúng; answerReview luôn not_checked. Nguồn fixture/AI tự sinh vẫn có issue và needs_revision.

## Review lần 1 — hợp đồng sửa hai P2

C04 tiếp tục REVIEW. Quyết định chốt trước giao coder:

- Metadata công khai của câu hỏi giữ aiGenerated (boolean) và sourceRefs[].sourceId (chuỗi đã che bí mật), start/end (số nguyên không bool, không âm) cùng quote đã lọc như cũ. Giữ các trường nguồn cũ documentId/kind/page/paragraph/locator; không đổi tên hoặc tự dựng nguồn từ chúng. Chỉ whitelist trường đã thống nhất, bỏ trường lạ/nội bộ và che chuỗi bí mật, không sửa draft/state gốc. Quote vẫn áp dụng giới hạn công khai 500 ký tự; không dùng quote đã che/cắt để kiểm lại offset hay chứng minh kiến thức.
- gameKind được cung cấp tường minh và loại manifest được nhận diện khác nhau (list ↔ questions): trả status=needs_revision, exam=null, issue incompatible_exam với field=gameKind, compatibility=failed; các checks khác not_checked. Không trả not_needed âm thầm hoặc tự thay Player. Phát hiện xung đột trước nhánh bỏ qua Exam và trước đòi câu hỏi. Khi không có gameKind tường minh thì suy theo manifest; manifest questions=exam ưu tiên content.kind=texts như nền tảng. Game danh sách thật hoặc list không manifest vẫn not_needed.
- Chủ file: coder metadata chỉ schemas.py + AI_INTEGRATION_CONTRACT.md; coder nghiệp vụ chỉ exams.py; coder kiểm thử chỉ test_chatbot_exams.py sau khi hai coder chốt interface. Điều phối giữ C04_SPEC/C04_REVIEW/AI_PROGRESS/AI_IMPLEMENTATION_PLAN.
- Hồi quy phải đi prepare_exam → proposal trong state → to_public_reply, giữ metadata cần thiết/nguồn cũ, kiểm không mutation và không lộ trường lạ/bí mật. Bao phủ cả hai hướng xung đột, game bình thường và manifest có ưu tiên questions=exam.
- Sinh câu hỏi bằng AI **chưa triển khai**. Module chuẩn bị đề không đồng nghĩa Exam Generator hoàn thành; kế hoạch tiếp theo phải theo dõi riêng sinh đề, provenance, tích hợp provider và nghiệm thu nội dung/giáo viên.
