# Bàn giao cho agent điều phối

## Vai trò được giao

Bạn là agent điều phối triển khai **Trợ lý game trên web hiện có**. Bạn phân chia nhiệm vụ cho agent coder, tích hợp và chạy kiểm thử. Agent tạo bộ tài liệu này giữ vai trò review độc lập. Chưa có coder nào được khởi chạy bởi phiên tạo tài liệu.

Người dùng muốn hiểu việc đang làm: báo cáo bằng tiếng Việt, giải thích thuật ngữ mới, tập trung một mục nhỏ. Không đổ toàn bộ code một lần hoặc tự chuyển sang xây lại nền tảng. Không lặp lại khảo sát đã có trừ khi mã đổi hoặc bằng chứng thiếu.

## Hành động đầu tiên

1. Kiểm tra Git root, branch, status và AGENTS.md; bảo vệ thay đổi hiện có. Không pull/merge tự động.
2. Đọc README của bộ bàn giao và toàn bộ hợp đồng/kế hoạch/test/review.
3. So sánh mã hiện tại với mốc khảo sát. Báo khác biệt có tác động, không coi tài liệu là nguồn chân lý hơn mã.
4. Thực hiện G0: chốt schema, state persistence, xác nhận/version, giao dịch, preview và kiểm runtime.
5. Chuẩn bị phương án/patch tối thiểu cho file dùng chung để review và xin xác nhận khi thuộc yêu cầu handoff; tiếp tục phần độc lập đã được phép.
6. Giao C01 rồi C02/C03 theo phụ thuộc; quản lý quyền sở hữu file.

## Prompt khởi động có thể sao chép

> Bạn là agent điều phối triển khai tab Trợ lý game trong starter-repo. Đọc docs/chatbot/README.md và các tài liệu được liên kết, tuân AGENTS.md. Mục tiêu là chatbot hội thoại để thu thập yêu cầu, chọn game có sẵn hoặc tạo mới, chuẩn bị Exam và Model thật tương thích, trình giáo viên xác nhận/duyệt, tạo App và mở chơi bằng chuột hoặc model. Agent review độc lập sẽ kiểm tra thiết kế, diff và bằng chứng. Bắt đầu G0; chưa giao coder viết toàn bộ dự án ngay. Giữ hợp đồng nền tảng, không commit/push, không đọc/hiển thị bí mật. Chia task theo AI_IMPLEMENTATION_PLAN.md, không cho agent sửa cùng file. Đầu tiên báo hiện trạng, quyết định G0 và phạm vi patch dùng chung; sau đó triển khai từng đợt đã được duyệt. Cập nhật AI_PROGRESS.md trung thực và gửi gói review sau mỗi đợt. Không tự bỏ tài liệu, chuột dự phòng, HITL, nhánh reuse hoặc generate_new.

## Mẫu giao coder

```text
Task: <C01/...>
Commit nền: <hash>
Mục tiêu: <một kết quả kiểm chứng được>
File được sửa: <danh sách chính xác>
File cấm/agent khác đang giữ: <danh sách>
Input/output và hàm: <theo hợp đồng + quyết định G0>
Phụ thuộc: <task/phiên bản schema>
Tình huống kiểm thử: <Txx + test task>
Nghiệm thu: <điều kiện cụ thể>
Yêu cầu bàn giao: diff, lệnh/test thật, kết quả, hạn chế, file đổi.
Không tự commit/push, mở rộng phạm vi hay đổi hợp đồng chung.
```

## Quy tắc phối hợp

- Module riêng có thể giao song song khi interface đã khóa; file dùng chung có một chủ sở hữu.
- Coder gặp xung đột interface gửi điều phối; không tự sửa file của agent khác.
- Điều phối đọc diff, tích hợp tuần tự, chạy test tổng, rồi gửi agent review.
- Review phát hiện lỗi: lập task sửa nhỏ, chỉ giao file liên quan; sau sửa kiểm lại bài tái hiện và regression cần thiết.
- Không yêu cầu người dùng nhập lại điều đã có trong handoff; chỉ hỏi quyết định thiết yếu chưa có.
- Không đánh DONE nếu chỉ có code mà thiếu bằng chứng. Không gọi model giả là AI thật.
- Nếu môi trường không có công cụ multi-agent, dùng tuần tự và nói rõ; không giả vờ có coder đang chạy.

## Gói gửi agent review

1. Task/đợt, mục tiêu và tiêu chí liên quan.
2. Commit nền, diff hoặc danh sách file + vị trí thay đổi.
3. Quyết định G0, xác nhận cần thiết và thay đổi hợp đồng nếu có.
4. Lệnh đã chạy, kết quả thực, loại model mock/thật.
5. Bằng chứng browser/API, proposalVersion/hash, tình huống chuột/camera.
6. Migration/rollback, chống trùng, quyền truy cập, phần chưa kiểm.
7. Vấn đề cần review tập trung; không giấu test fail hoặc lược bỏ test khó.

## Định nghĩa kết thúc

Kết thúc khi các đợt W1–W5 được nghiệm thu, hai nhánh hoạt động trên web, sửa qua hội thoại đúng phạm vi, kiểm runtime/chuột và AI thật có bằng chứng, không lỗi P0/P1. Nếu thiếu nguồn thật, webcam hoặc tài liệu định dạng nào thì báo trạng thái chính xác và xin quyết định phạm vi; không tự tuyên bố hoàn thiện.
