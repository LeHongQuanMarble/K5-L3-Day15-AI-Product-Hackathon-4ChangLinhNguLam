# Đối chiếu spec.md, canvas.md và mã chatbot

Ngày đối chiếu: 2026-11-27, Asia/Bangkok. Không sửa spec.md/canvas.md. Bản cập nhật này phản ánh yêu cầu mới nhất: chỉ hoàn thiện chatbot và bảo đảm tích hợp đúng hợp đồng chung. Chi tiết rà soát và sửa mã chatbot nằm trong CHATBOT_COMPLIANCE_AUDIT.md. Đây không phải hợp đồng mới đã được cả nhóm duyệt.

## 1. Phạm vi sản phẩm

- `canvas.md` dòng 1, 5, 6: AI Game Composer cho giáo viên dùng **bộ câu hỏi có sẵn**, đề xuất tổ hợp Model + Player + Question Set, người duyệt trước tạo game.
- `spec.md` §4: kiến trúc mục tiêu rộng hơn, gồm tài liệu, sinh đề, tái sử dụng/sinh game, hai cổng duyệt, kiểm thử và chạy game.
- Handoff của người dùng vẫn yêu cầu hai nhánh, tài liệu, sinh đề và chuột dự phòng. Không bỏ các yêu cầu này vì Canvas hẹp hơn.

**Quyết định mới nhất của người dùng:** chỉ hoàn thành chức năng chatbot, tuân thủ spec.md và canvas.md chung, kiểm tra và sửa các vi phạm trong task đã làm. Chatbot chịu trách nhiệm hội thoại, chuẩn bị yêu cầu, điều phối các module được giao và trả đầu ra đúng hợp đồng. Các chức năng nền tảng như runtime, lưu App, model registry và quyền truy cập là phụ thuộc tích hợp; không tự viết lại hoặc sửa mã gốc để hoàn thành chúng. Luồng dùng bộ câu hỏi có sẵn của Canvas là trường hợp bắt buộc.

Hội thoại phải thể hiện đúng các trạng thái thu thập yêu cầu, chuẩn bị kế hoạch, chờ duyệt và kết quả tích hợp. Khi dịch vụ phụ thuộc chưa có, ghi rõ chưa hỗ trợ hoặc chưa kiểm tra; không bịa artifact, ID, kiểm chứng hoặc báo game sẵn sàng. Danh sách yêu cầu sản phẩm tổng thể bên dưới dùng để đối chiếu giao diện và phụ thuộc, không giao toàn bộ sản phẩm cho coder chatbot.

## 2. Những yêu cầu thống nhất

1. Workflow có điều kiện; không cần sản phẩm nhiều agent tự quyết. Nhiều coder là cách phát triển, không phải kiến trúc AI sản phẩm.
2. Chatbot hỏi thêm khi thiếu; dùng nguồn và danh mục thật theo quyền.
3. Tái sử dụng không sinh HTML hoặc sửa Player gốc.
4. Tạo mới tuân thủ contract; câu hỏi tách HTML.
5. Người dùng chọn game cụ thể thì giữ lựa chọn, giải thích khi không hợp.
6. Chuột luôn dùng được, không mất tiến độ khi model/camera lỗi.
7. Hai cổng HITL: duyệt ApplicationPlan và duyệt Game Preview. Không tự công khai hoặc thay vai trò Admin.
8. Sửa có giới hạn; chưa có bằng chứng kiểm tra thì không ready.

## 3. Chênh lệch với mã hiện tại

| Yêu cầu tài liệu | Hiện trạng mã | Việc cần triển khai |
|---|---|---|
| ApplicationPlan có name/player/model/exam/interaction | Web trả chatId/reply và proposal plan_v2; không có ApplicationPlan envelope | Chốt adapter/version cho hợp đồng nhóm, giữ tương thích web cũ |
| Kế hoạch trước duyệt đã có bộ đề, đáp án, Player, Model | `_build_proposal` để exam=None, modelId=None, mapping={}, auto mode chưa định tuyến | I02 nối C03 và C04 trước cổng duyệt kế hoạch hoàn chỉnh |
| Chọn tài nguyên giáo viên yêu cầu | T06 có selected_player_id/selected_model_id/selected_exam_id; chat hiện chỉ nhận text/context và schema nội bộ chưa có lựa chọn modelId tường minh | Chốt cách truyền lựa chọn và kiểm quyền, không bỏ selected_model_id |
| Mock và Real cùng hợp đồng, T06 không chờ T12 | fake-rules trả phân tích lượt; không phải Mock ApplicationPlan đầy đủ | Bổ sung mock adapter/service và kiểm bốn tình huống T06 |
| Chọn bộ đề có sẵn là luồng tối thiểu | select_exam có kiểm quyền nhưng chưa được gọi từ web | Tích hợp danh sách/chọn đề, hiển thị nội dung/đáp án/nguồn thiếu |
| Sinh câu hỏi từ tài liệu/chủ đề | C04 chỉ nhận câu hỏi cấu trúc hoặc Exam đã tồn tại | O17 còn TODO, cần task sinh đề AI riêng; không gọi C04 DONE là toàn bộ Exam Generator |
| Production → Validator → Composer → Preview → duyệt game → Runtime | Chưa nối/sinh/lưu App qua chatbot | Chốt lưu nháp/private và preview, chỉ mở quyền phù hợp sau duyệt |
| Tài liệu và Knowledge Base | Chưa upload/trích xuất/tra cứu | C07 và nguồn tri thức có căn cứ, không bịa đã có KB |

C01, C02, I01, C03 và C04 đã review đạt theo phạm vi từng module. Không hồi tố kết quả đó thành nghiệm thu T06, ApplicationPlan hoàn chỉnh hoặc luồng game cuối cùng.

## 4. Bảng ánh xạ hợp đồng đề xuất

Hợp đồng Spec ghi rõ còn là **đề xuất v1.0 cần nhóm thống nhất**. Không đổi API đang chạy chỉ bằng thay tên trường; dùng lớp chuyển đổi sau khi chốt.

| Spec / hợp đồng nhóm | Mã hiện có / nguồn đề xuất |
|---|---|
| session_id (string) | chatId (integer); cần ánh xạ ID ổn định, kiểm quyền, không ép kiểu tùy tiện |
| message đầu vào | text |
| history | history do server đọc, không tin lịch sử client như state chuẩn |
| document_ids | documentIds; cần adapter và quyền nguồn |
| selected_player_id | requirements.gamePreference.playerId |
| selected_model_id | Chưa có lựa chọn model tường minh trong schema; cần thiết kế bổ sung |
| selected_exam_id | requirements.contentSource.examId |
| generation_mode | gamePreference.mode / kết quả route_game |
| schema_version | Chưa có trường public tương ứng; SCHEMA_VERSION nội bộ là phiên bản state, không tự coi là phiên bản hợp đồng |
| simulated | simulated; mock/fixture phải ghi rõ |
| status / message / errors | status nội bộ / reply.text / failure; cần bảng trạng thái và danh sách lỗi rõ ràng |
| application_plan.name | Tên App cần được chuẩn bị; không dùng nhãn Player thay thế âm thầm |
| application_plan.player | Player ID/mode từ C03; HTML mới chỉ ở backend/preview có kiểm quyền |
| application_plan.model | modelId/kind/mapping từ C03, sure/holdMs được kiểm theo nền tảng |
| application_plan.exam | Exam ID hoặc content đã C04 kiểm, kèm metadata trong state riêng |
| application_plan.interaction | primary, fallback=mouse, mouse_always_enabled=true |

`clarifying` có thể ánh xạ sang `needs_clarification`. Không ánh xạ mọi `awaiting_confirmation` hiện tại thành `pending_approval`: proposal yêu cầu sơ bộ chưa đủ Player/Model/Exam. Cần phân biệt xác nhận yêu cầu với duyệt kế hoạch hoàn chỉnh. Mọi ánh xạ khác phải được định nghĩa trước code.

Nếu generate_new chưa có HTML thì đó là bản thiết kế trước sản xuất, chưa phải Player hoàn chỉnh. Cần làm rõ giai đoạn/validation thay vì bịa HTML/ID cho hợp schema. HTML phục vụ xem thử vẫn phải secure và chạy sandbox; chốt ranh giới ApplicationPlan nội bộ với phản hồi công khai.

## 5. Mâu thuẫn/chưa rõ cần chốt

1. Spec đang có **hai mục §4**: phần thiết kế mới và khung mẫu cũ chưa xóa. Các mục khác còn placeholder; không coi chúng là dữ liệu hoàn chỉnh.
2. Canvas nói bộ câu hỏi có sẵn; Spec nói sinh đề/tài liệu/game mới. Không tự diễn giải thành bỏ bớt phạm vi.
3. Spec yêu cầu kế hoạch hợp lệ trước pending_approval, nhưng generate_new sinh HTML sau duyệt plan và chỉ yêu cầu HTML hợp lệ trước bàn giao Player hoàn chỉnh. Cần phân biệt plan giai đoạn thiết kế và artifact sau sản xuất.
4. Spec liệt kê mouse trong bảng “Model Kind”, còn runtime/model registry không có kind mouse. Trong code, mouse là phương thức điều khiển, không tự tạo model kind/ID mouse.
5. Bộ đề cũ không có metadata giải thích/nguồn. C04 trả needs_revision/answerReview not_checked: I02 phải có thao tác giáo viên xem và xác nhận phù hợp, không tự đánh passed hoặc bỏ kiểm.
6. Cập nhật từ main đã chuyển mã ra gốc; tài liệu chatbot vẫn ở starter-repo/docs/chatbot. Đừng giao coder đường dẫn cũ starter-repo/ailab.

Việc sửa spec.md/canvas.md thuộc tài liệu nhóm: chỉ đề xuất đoạn cần sửa, không tự thay đổi hai file gốc trong task đồng bộ này.

## 6. Thứ tự triển khai đề xuất cho điều phối

1. Chỉ triển khai chatbot. Lập ma trận yêu cầu Spec/Canvas → phần chatbot phụ trách hoặc dịch vụ phụ thuộc → interface → test → trạng thái. Chốt ApplicationPlan v1 với đầu mối tích hợp; không tự mở rộng sang sửa nền tảng.
2. Giao coder adapter/schema và validator kế hoạch, không ghi lại nền tảng; interface ổn định trước chia song song.
3. Giao Mock ApplicationPlan T06 độc lập provider thật, dùng catalog fixture được ghi rõ và ID tương thích thật trong cùng fixture; không dùng ID minh họa trong spec như ID production.
4. Thiết kế I02 cho cả hai nhánh reuse_existing và generate_new, cùng Exam có sẵn/tạo mới và đầu vào tài liệu. Có thể nghiệm thu từng đợt, nhưng phải giữ đầy đủ đường đi và phụ thuộc: C03/C04 → phương án hoàn chỉnh → giáo viên duyệt → private draft/preview → duyệt kết quả → App/runtime. Chốt giao dịch, version, idempotency và quyền lại tại accept. Không ghi I02 hoặc sản phẩm tổng thể DONE nếu mới có một nhánh mà phạm vi nghiệm thu yêu cầu cả hai.
5. Theo dõi task chưa làm: sinh đề AI O17, game mới C05, validator runtime/chuột C06, tài liệu C07, revision C08, real model/eval I03.

## 7. Test bổ sung trước nghiệm thu tích hợp

- Cùng đầu vào, mock/real adapter có cùng schema; fake không cần key và simulated=true.
- T06: reuse không HTML mới; generate dùng template có contract; thiếu thông tin needs_clarification; tài nguyên không hợp lệ error.
- Kế hoạch thiếu Exam/Player/Model bắt buộc không pending_approval; trường không áp dụng như game danh sách/model không cần thì biểu diễn rõ, không bịa tài nguyên.
- selected_model_id/Player/Exam được giữ hoặc báo xung đột; không tự đổi game đã chọn.
- Hai lần duyệt tách biệt và theo version; từ chối/chỉnh sửa thu hồi xác nhận cũ.
- Bộ đề có sẵn thiếu nguồn không bị tự chứng nhận đúng; giáo viên xem được đáp án và giới hạn.
- Chuột là điều khiển, không model registry kind; audio không được hứa hoạt động.
- Không sửa file gốc, không ghi DB thật trong test, không tự công khai/push.
