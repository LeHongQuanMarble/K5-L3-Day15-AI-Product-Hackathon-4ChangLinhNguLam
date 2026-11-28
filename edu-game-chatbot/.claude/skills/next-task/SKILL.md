---
name: next-task
description: Thực hiện task tiếp theo chưa xong trong TASKS.md theo đúng quy trình của repo. Người dùng gọi bằng /next-task (có thể kèm mã task, ví dụ /next-task T07).
disable-model-invocation: true
---

# /next-task

1. Nạp skill `token-saver` và `fast-coding` nếu chưa nạp trong phiên này.
2. Grep `TASKS.md` tìm `^### \[~\]`, nếu không có thì tìm `^### \[ \]` đầu tiên (hoặc đúng mã task trong `$ARGUMENTS`).
   Chỉ Read đoạn của task đó (từ tiêu đề tới `### ` kế tiếp).
3. Kiểm tra task phụ thuộc: các file mà task cần dùng phải đã tồn tại. Thiếu thì báo người dùng và dừng.
4. Đổi tiêu đề task thành `[~]`.
5. Làm theo vòng lặp trong skill `fast-coding`.
6. Hoàn thành theo mục "Hoàn thành một task" trong `CLAUDE.md`.
7. Báo cáo ≤ 5 dòng: task, file đã tạo/sửa, kết quả lệnh kiểm tra, lưu ý (nếu có).
