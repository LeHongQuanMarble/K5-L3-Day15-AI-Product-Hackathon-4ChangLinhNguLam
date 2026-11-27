# Quy trình review độc lập

## Vai trò

Agent review kiểm thiết kế và mã dựa trên yêu cầu đã chốt, đọc thay đổi thực tế và kiểm bằng chứng. Không tự trở thành điều phối hay sửa lan rộng chức năng. Có thể chạy kiểm tra độc lập, tái hiện lỗi trên DB tạm và yêu cầu bản sửa cụ thể.

## Mức độ lỗi

- P0: rò bí mật/quyền truy cập nghiêm trọng, mất dữ liệu hoặc thực thi không cách ly; chặn tích hợp.
- P1: hỏng luồng chính, không có chuột, sai xác nhận, tạo trùng, sửa game gốc ở reuse, ready giả; chặn nghiệm thu.
- P2: lỗi có cách tránh nhưng ảnh hưởng chức năng/độ tin cậy; cần sửa hoặc chủ sản phẩm chấp thuận hoãn có lý do.
- P3: cải thiện nhỏ về cách trình bày/tổ chức; không biến thành việc bắt buộc ngoài phạm vi.

## Checklist theo lớp

### Phạm vi và hợp đồng

- [ ] Task và file sửa đúng quyền sở hữu; không lẫn thay đổi đồng đội.
- [ ] API/field mới được đánh dấu và có chuyển tiếp cho chat/proposal cũ.
- [ ] Không sửa file khung, chuẩn đạt đã khóa hoặc kết quả eval cũ.
- [ ] Không thêm framework lớn không có lý do; dependency có khai báo.

### Hội thoại và luồng

- [ ] Hỏi đúng phần thiếu, không bắt buộc HTML ở mỗi lượt.
- [ ] State tồn tại qua tải lại trang; dữ liệu cũ không bị mất.
- [ ] Game giáo viên chọn được giữ; mọi thay thế có giải thích/xác nhận.
- [ ] Phiên bản và xác nhận gắn đúng user/bản; chỉnh sửa hủy xác nhận cũ.
- [ ] Model ngôn ngữ không có quyền tự phê duyệt hoặc tự cấp quyền dữ liệu.

### Sản phẩm và tương thích

- [ ] Reuse không gọi sinh HTML, không sửa Player gốc, không tạo file HTML.
- [ ] Generate nhận Exam ngoài, không hardcode kiến thức vào HTML.
- [ ] ID, kind, role, mapping lấy từ danh mục có quyền; không bịa audio hoạt động.
- [ ] Exam đúng cú pháp và nghĩa, có nguồn/nhận xét không chắc; giáo viên xem được đáp án.
- [ ] Preview sử dụng đúng Exam và phiên bản.
- [ ] Game danh sách không bị ép thành game câu hỏi.

### Runtime và an toàn

- [ ] Sandbox/CSP giữ nguyên; không đưa key/mật khẩu vào HTML/log.
- [ ] Tài liệu không được coi là chỉ dẫn; upload có giới hạn và quyền sở hữu.
- [ ] Chuột chơi được khi loading/denied/failed/off.
- [ ] Chuyển model/chuột không mất điểm hoặc tiến độ; không chấm hai lần.
- [ ] Runtime có bằng chứng thực, không chỉ regex hoặc LLM tự chấm.
- [ ] Thử gọi AI thật có trace; thông báo lỗi đã được làm sạch bí mật.

### Lưu trữ và tích hợp

- [ ] Không giữ transaction ghi trong lúc đợi model.
- [ ] accept lặp/đồng thời không tạo trùng; rollback khi lỗi.
- [ ] Kiểm quyền lại tại confirm/accept, kể cả resource đổi quyền sau lập plan.
- [ ] Không tự chia sẻ App hoặc nâng trạng thái duyệt Player.
- [ ] Sửa Exam của một App không làm đổi ngầm các App khác.
- [ ] F01 có regression PUT App, đọc lại mapping đúng kiểu.
- [ ] Web và adapter eval dùng chung quy tắc; answer vẫn đúng hợp đồng.

## Mẫu kết quả review

```text
Đợt/task:
Phạm vi đã đọc:
Kết quả: cần sửa / đạt trong phạm vi đã kiểm

Phát hiện (xếp mức nghiêm trọng):
- [P1] file:line — lỗi, tình huống tái hiện, tác động, hướng sửa tối thiểu.

Kiểm tra độc lập đã chạy:
- Lệnh/thao tác; kết quả; môi trường và loại model.

Chưa kiểm / rủi ro còn lại:
- ...

Điều kiện kiểm lại:
- Test nào phải đạt, bằng chứng nào còn thiếu.
```

Nếu không thấy lỗi, nói rõ phạm vi và giới hạn; không khẳng định toàn hệ thống an toàn/đúng khi chỉ review một task. Review tài liệu không thay review code, review code không thay kiểm thử runtime.
