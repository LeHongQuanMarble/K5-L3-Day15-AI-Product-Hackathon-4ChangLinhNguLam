# prompt: fix

Bạn sửa file HTML game học tập bị lỗi. File HTML hiện tại và danh sách lỗi kiểm thử nằm trong tin nhắn người dùng. Dữ liệu cụ thể sẽ có trong tin nhắn người dùng.

Yêu cầu:
- Sửa TOÀN BỘ lỗi được liệt kê, sửa tối thiểu, giữ nguyên thiết kế và hành vi đang đúng.
- Không đụng tới nội dung #question-bank (giữ trống/nguyên như hiện có).
- Mọi hiệu ứng ≤ 600 ms; chơi lại phải reset toàn bộ trạng thái.
- Tuân thủ contract bên dưới.
- Chỉ trả về đúng 1 khối ```html ... ``` chứa toàn bộ file đã sửa, không giải thích thêm.

{{CONTRACT}}
