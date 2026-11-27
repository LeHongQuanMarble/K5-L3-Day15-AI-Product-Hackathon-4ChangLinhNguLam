# Rà soát phạm vi chatbot — 2026-11-27

## Kết luận

Chỉ phát triển chatbot, tuân thủ spec.md và canvas.md chung. C01/C02/I01/C03/C04 đã có module và kiểm thử, nhưng chưa tạo thành chatbot hoàn chỉnh đầu cuối. Không coi kết quả đạt của từng module là nghiệm thu toàn bộ Agent theo Spec.

## Sai lệch đã sửa trong đợt này

| Vị trí | Sai lệch | Sửa |
|---|---|---|
| workflow.py, web/chatbot.js | Gọi bản yêu cầu sơ bộ là phương án, dễ nhầm là duyệt ApplicationPlan khi chưa có Exam/Model đầy đủ | Hiển thị yêu cầu sơ bộ; proposal và confirmation có scope=requirements; giải thích còn bước duyệt kế hoạch và preview riêng |
| chatbot_server.py | Sau thao tác xác nhận/hủy luôn ghi simulated=false, dù phương án được tạo bằng fake-rules | Giữ provenance của proposal; proposal cũ thiếu provenance được đánh dấu giả lập thận trọng |
| web/chatbot.js | Hiển thị chuột luôn bật khi chưa có game được kiểm thử | Hiển thị đây là yêu cầu điều khiển, chưa phải kết quả kiểm thử |
| REQUIREMENTS_ALIGNMENT.md | Phạm vi cũ có thể bị hiểu là giao chatbot làm toàn bộ nền tảng | Cập nhật theo yêu cầu mới nhất; phân biệt trách nhiệm chatbot và phụ thuộc |

Không thêm ApplicationPlan giả chỉ để khớp tên trường. API chat hiện hữu được giữ; đầu ra hợp đồng Agent đầy đủ còn là việc tích hợp bên dưới.

## Các task đã làm

| Task | Kết quả rà soát | Giới hạn phải giữ |
|---|---|---|
| C01 schema | Có normalize, whitelist public, lọc bí mật và cấu trúc lỗi | Chưa phải schema ApplicationPlan chung hoàn chỉnh |
| C02 hội thoại | Có hỏi thiếu, sửa yêu cầu, version và hủy xác nhận cũ | Xác nhận yêu cầu không cấp quyền tạo App hoặc báo ready |
| I01 web/API | Có kiểm chủ chat, version, requestId, lưu state; lỗi provenance đã sửa | Chưa nối C03/C04 thành kế hoạch hoàn chỉnh; chưa nghiệm thu browser lại trong đợt này |
| C03 catalog | Module chọn Player/Model và mapping đã có kiểm thử | Chưa được workflow/API gọi để hoàn tất kế hoạch; không coi Player tạm trong C02 là kết quả routing đã kiểm |
| C04 exams | Có chọn Exam theo quyền, chuẩn hóa và kiểm cấu trúc câu hỏi | Không sinh đề AI; answerReview not_checked không có nghĩa đáp án đã được xác minh |

## Khoảng trống còn phải làm trong chatbot

1. I02: gọi C03/C04 từ workflow; đọc tài nguyên theo quyền; giữ lựa chọn Player/Model/Exam hoặc trả xung đột rõ ràng.
2. Đầu vào lựa chọn model tường minh và adapter input/output theo Contract Spec; giữ API web cũ tương thích. Không chuyển bản yêu cầu chưa đầy đủ thành pending_approval.
3. Mock Agent theo T06 với bốn trường hợp: reuse, generate, thiếu thông tin, lỗi. Fixture phải simulated=true; chưa có dịch vụ generate thật thì không hứa đã tạo game thật.
4. Chỉ cho duyệt ApplicationPlan đã kiểm đủ thành phần. Duyệt Preview là cổng riêng, theo version; chỉnh sửa phải thu hồi duyệt cũ.
5. Sinh đề từ chủ đề/tài liệu, game mới và kiểm runtime cần interface với module phụ thuộc. Báo chưa hỗ trợ/chưa kiểm khi dịch vụ chưa có. Không tự sửa Player, Model registry, App store hoặc runtime gốc.

## Bảo toàn và kiểm chứng

- Thay đổi lần này chỉ trong file chatbot thêm mới, test chatbot và tài liệu chatbot. Không sửa spec.md/canvas.md, TEAMS.md, DB thật, .env hoặc file khung bị khóa.
- So với origin/main hiện tại: server.py, store.py, web/app.js và các file khung run.py, codebase/tracing.py, eval/run_eval.py, cost/simulate.py không khác. Lịch sử ba file nền tảng ailab nói trên chỉ có commit chuyển cấu trúc của main (14dea37); không có commit chatbot sửa chúng.
- `python -m unittest discover -s ailab -p 'test_*.py'`: 216 test đạt. API tests dùng DB tạm. Bổ sung assertion về scope yêu cầu, nhãn simulated và thông báo chưa duyệt kế hoạch.
- Chưa chạy lại trình duyệt hoặc kiểm dịch vụ AI thật trong đợt này. Không có bằng chứng game đầu cuối đã chơi được.
- Chưa commit/push các sửa đổi của đợt rà soát này.

## Prompt bàn giao điều phối

Chỉ điều phối coder hoàn thiện chatbot theo spec.md/canvas.md, đọc CHATBOT_COMPLIANCE_AUDIT.md và REQUIREMENTS_ALIGNMENT.md trước. Tiếp nhận sửa đổi hiện có, không ghi đè hoặc hoàn nguyên chúng. Ưu tiên I02: nối C03/C04 với workflow và xuất ApplicationPlan đúng Contract, có lựa chọn tài nguyên theo quyền và kiểm tương thích. Giữ xác nhận yêu cầu tách khỏi duyệt kế hoạch và duyệt preview; không ready khi chưa kiểm. Hoàn thiện Mock T06 có nhãn giả lập và các trường hợp reuse/generate/clarify/error. Chốt interface dịch vụ nền tảng, ghi rõ phụ thuộc chưa có thay vì tự viết lại. Chỉ sửa ailab/chatbot/**, ailab/chatbot_server.py, ailab/web/chatbot.js, ailab/test_chatbot_*.py và tài liệu chatbot; không sửa file gốc nền tảng, spec/canvas, TEAMS, DB thật, secrets hoặc file khung bị khóa. Không commit/push. Bàn giao danh sách file, test, giới hạn và yêu cầu review độc lập trước nghiệm thu.
