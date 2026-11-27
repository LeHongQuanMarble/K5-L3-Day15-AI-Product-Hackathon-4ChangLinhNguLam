# Bối cảnh dự án và phạm vi chatbot

## Mục tiêu đã xác nhận

Phát triển trực tiếp tab **Trợ lý game** trên web AI Lab để giáo viên hội thoại, hoàn thiện yêu cầu, nhận phương án, duyệt và mở được game học tập.

Luồng chính: nhập yêu cầu → hỏi thông tin thiếu → cân nhắc game có sẵn hoặc tạo mới → chuẩn bị bộ đề và model tương thích → giáo viên xác nhận → kiểm tra, xem thử, duyệt → tạo App → chơi bằng chuột hoặc model.

Khi đủ thông tin, không hỏi máy móc. Khi thiếu, chỉ hỏi phần thiết yếu; giá trị mặc định phải được trình giáo viên xác nhận. Khi giáo viên đã chọn game, không tự thay bằng game khác. Đổi bộ đề phải giữ Player và HTML nếu cơ chế chơi không cần đổi.

## Sáu yếu tố của nhiệm vụ

| Yếu tố | Nội dung |
|---|---|
| Mục tiêu | Trợ lý game hoàn chỉnh và tích hợp vào web đang có |
| Bối cảnh | Hackathon; đồng đội phụ trách nền tảng; ưu tiên luồng chạy thật, ổn định |
| Đầu vào | Hội thoại, yêu cầu, tài liệu, danh mục có quyền dùng, xác nhận |
| Đầu ra | Phản hồi có cấu trúc; Player/Exam/Model phù hợp; App và đường dẫn chơi |
| Ràng buộc | HITL, chuột dự phòng, nội dung tách HTML, sandbox, không bịa ID, giữ hợp đồng chung |
| Hoàn thành | Hai nhánh tạo game chạy trên web, chỉnh sửa đúng phạm vi, có bằng chứng kiểm thử và gọi AI thật |

## Vai trò

- Người dùng: chủ sản phẩm, học AI Engineering, duyệt thiết kế quan trọng và thay đổi hợp đồng chung.
- Agent điều phối: chia nhiệm vụ, quản lý quyền sửa file, tích hợp, kiểm thử và báo cáo.
- Agent coder: làm nhiệm vụ được giao, tự kiểm thử và gửi bằng chứng; không tự mở rộng phạm vi.
- Agent review: kiểm tra độc lập thiết kế, mã, hành vi và bằng chứng; chỉ ra lỗi theo mức độ, kiểm tra lại bản sửa.
- Đồng đội: chủ sở hữu các thành phần Player, runtime, Model, database và giao diện dùng chung; cần phối hợp khi thay đổi nền tảng.

## Bằng chứng khảo sát

Mốc đọc mã: commit `faa44a8`. Nhánh làm việc khi soạn: `feature/chatbot`.

| Thành phần | Hiện trạng đã đọc |
|---|---|
| `ailab/web/app.js: chatView()` | Gửi `{chatId,text}`, hiển thị phản hồi và đề xuất HTML |
| `ailab/server.py: _chat()` | Lưu hội thoại, gọi `llm.generate`, trả đề xuất |
| `ailab/llm.py: generate()` | Mong HTML; câu hỏi không có HTML bị xem là lỗi |
| `codebase/agent.py: answer()` | Luồng riêng cho CLI/eval, có trả câu hỏi không HTML |
| `ailab/store.py` | Có Model, Player, Exam, App, hội thoại, kiểm quyền và cấu hình |
| `ailab/contract.py` | Kiểm manifest `jl-camera`, quét cờ, chèn CSP và helper |
| `ailab/web/play.js` | Có nhánh image, pose, hands; audio chưa chạy |
| Xem thử đề xuất | Dùng câu hỏi mẫu, chưa phải bộ đề giáo viên đang chuẩn bị |

Đã chạy 27/27 unittest cũ đạt. Đã thử HTTP trên database tạm: đăng ký/quyền, chatbot giả, xem thử, chấp nhận Player Nháp, tạo App, lấy đề, thay nội dung Exam và chặn xóa Exam đang dùng. **PUT App lỗi 500** do `mapping` là dict chưa được JSON hóa. Không suy ra từ các kiểm tra này rằng game đã chơi đúng trong trình duyệt.

Chưa xác nhận: gọi AI thật trên máy hiện tại, webcam thật, toàn bộ chuột dự phòng, chất lượng kiến thức của bộ đề mẫu. Không đọc/hiển thị giá trị bí mật trong `.env`.

## Yêu cầu không được bỏ

1. Hai nhánh: reuse_existing (tái sử dụng) và generate_new (tạo mới).
2. Nhánh tái sử dụng không sinh lại HTML, không tạo file HTML, không sửa Player gốc.
3. Câu hỏi và đáp án ở Exam; HTML chỉ chứa cơ chế chơi và nhận dữ liệu ngoài.
4. Chuột luôn hoạt động kể cả model tải chậm/lỗi, camera bị từ chối/tắt. Chuyển điều khiển giữ điểm và tiến độ.
5. Chỉ dùng ID, lớp, khả năng model thực tế theo quyền người dùng. Audio phải báo chưa hỗ trợ.
6. Kiểm tra cấu trúc, kiến thức/nguồn, tương thích, an toàn, runtime và chuột; chưa kiểm thì ghi chưa kiểm.
7. Có xác nhận phương án và duyệt kết quả; không tự công khai. Game AI lưu Nháp, giữ quy trình Admin hiện có.
8. Sửa lỗi có giới hạn; không gọi AI lặp vô hạn hoặc tự đổi game đã chọn.
9. Hỗ trợ tài liệu, chỉnh sửa nhiều lượt, ghi nguồn và đánh giá; triển khai sau luồng tối thiểu nhưng vẫn phải theo dõi.

## Ranh giới

Được chuẩn bị thay đổi chức năng chatbot và tích hợp tối thiểu theo kế hoạch. Không xây lại runtime, đăng nhập hay database. Trước sửa file dùng chung, điều phối trình patch/phương án cụ thể để người dùng xác nhận theo handoff. Tạo bộ tài liệu này không đồng nghĩa đã duyệt mọi endpoint/schema đề xuất.

Không sửa file khung `run.py`, `codebase/tracing.py`, `eval/run_eval.py`, `cost/simulate.py`. Không commit/push nếu chưa được phép. Không tự reset/clean/force push, không ghi đè công việc đồng đội. Không tự đổi nhánh main.
