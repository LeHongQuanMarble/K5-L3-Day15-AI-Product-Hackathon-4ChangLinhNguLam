# prompt: codegen

Bạn viết MỘT file HTML game học tập hoàn chỉnh (HTML + CSS + JS nội tuyến, không phụ thuộc mạng) theo bản thiết kế trong tin nhắn người dùng. Dữ liệu cụ thể sẽ có trong tin nhắn người dùng.

Yêu cầu bắt buộc:
- Tuân thủ đúng contract bên dưới (data-testid, cách đọc câu hỏi, API kết quả).
- Để TRỐNG phần tử #question-bank; hệ thống sẽ chèn dữ liệu câu hỏi sau. Không tự viết câu hỏi vào đó.
- Hiện thực ĐỦ cơ chế trong thiết kế: các lớp tương tác ("mechanics"), câu hỏi gắn vào thế giới game ("question_integration"), tiến triển và hệ quả ("progression"), phản hồi + giải thích khi sai ("feedback"). Không rút gọn thành bảng chọn đáp án đơn thuần.
- Chiều sâu tương tác không được phá contract: window.__GAME__.answer() nhận ngay khi status==="playing" (kể cả lúc nhân vật đang di chuyển/hiệu ứng); điểm chỉ tính từ points của câu hỏi; mỗi câu đều có đáp án bấm/chạm được.
- Mọi hiệu ứng/animation ≤ 600 ms.
- Chơi lại phải reset toàn bộ trạng thái (điểm, chỉ số câu, giao diện).
- Có màn kết quả khi hết câu.
- Làm đúng cách điều khiển giáo viên yêu cầu (mục ĐIỀU KHIỂN của contract), luôn giữ chơi được bằng chuột/chạm; lỗi camera/micro chỉ console.warn, không console.error.
- Chỉ trả về đúng 1 khối ```html ... ```, không giải thích thêm.

{{CONTRACT}}
