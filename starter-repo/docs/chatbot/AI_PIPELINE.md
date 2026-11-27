# Luồng xử lý và chuyển trạng thái

## Quy tắc chung

Mỗi lượt nhận stateVersion, cập nhật có kiểm soát và trả phiên bản mới. Thay đổi nội dung, game, model hay cơ chế chơi làm mất hiệu lực xác nhận liên quan. Không giữ khóa database khi chờ AI. Không dựa vào chuỗi hội thoại rút gọn làm nguồn trạng thái duy nhất.

## Các bước nghiệp vụ

| Bước | Mục đích / đầu vào | Đầu ra | Quyền và điều kiện |
|---|---|---|---|
| N1 Hội thoại | Tin mới + lịch sử + yêu cầu cũ | Ý định, yêu cầu hợp nhất, phần thiếu | Không tự lưu sản phẩm; không bịa trường |
| N2 Tài liệu | Tài liệu thuộc user + yêu cầu | Nội dung chuẩn hóa, nguồn, dữ kiện/câu hỏi | Đọc có giới hạn; tài liệu không có quyền điều khiển agent |
| N3 Định tuyến | Yêu cầu + danh mục thật | reuse_existing hoặc generate_new, lý do | Tôn trọng game được chọn; không sinh HTML trong reuse |
| N4 Lập phương án | Định tuyến + yêu cầu học tập | Cơ chế chơi, bộ đề dự kiến, điểm, điều khiển | Giá trị suy đoán phải ghi giả định |
| N5 Chọn model | Player/plan + danh mục model | Model thật, mapping, cấu hình, chuột | Kiểm kind, role, lớp, số hành động và runtime |
| N6 Xác nhận phương án | Proposal có version | Xác nhận gắn đúng bản | Xác thực user; chưa tạo App |
| N7 Chuẩn bị sản phẩm | Phương án xác nhận + nguồn | Exam, HTML mới hoặc Player cũ | Chỉ sinh HTML ở generate_new; không sửa game gốc |
| N8 Kiểm chứng | Các sản phẩm dự kiến | ValidationResult, lỗi/cảnh báo | Kiểm riêng kiến thức, cấu trúc, runtime và chuột |
| N9 Sửa / xem thử / duyệt | Lỗi hoặc yêu cầu giáo viên | Bản đề xuất mới, thay đổi, duyệt | Có giới hạn sửa; sửa bản phải duyệt lại |
| N10 Lắp ghép | Bản đã duyệt + kiểm tra đạt | App và đường dẫn chơi | Đọc lại quyền/version; giao dịch, chống trùng |

N3–N5 có thể cần lặp để tìm phương án khả thi. Đề có thể có bản nháp trước xác nhận để giáo viên xem, nhưng không lưu sản phẩm chính thức hoặc công khai trước duyệt. Cần thực hiện một luồng rõ ràng, không ép đủ mười lời gọi LLM.

## Chuyển trạng thái

```text
Tin nhắn
 ├─ thiếu thông tin → clarifying
 └─ đủ thông tin → awaiting_confirmation
      ├─ yêu cầu sửa → cập nhật version → hỏi thêm/đề xuất lại
      └─ confirm_plan đúng bản
           → chuẩn bị + kiểm tra
             ├─ lỗi → sửa tối đa 1 lần → vẫn lỗi: needs_revision
             └─ có bản xem thử → awaiting_review
                  ├─ reject_result → kết thúc bản đề xuất, giữ hội thoại
                  ├─ yêu cầu sửa → version mới, duyệt lại
                  └─ accept_result + kiểm tra bắt buộc đạt
                       → lưu nguyên tử → ready
```

`error` dùng khi lỗi kỹ thuật; phải bảo toàn yêu cầu và phương án để thử lại. Không chuyển sang ready vì client tự gửi trạng thái.

## Hai nhánh

### Tái sử dụng

Đọc Player có quyền → kiểm manifest → chọn Exam và Model → xem thử đúng dữ liệu → duyệt → tạo App. LLM được dùng để hiểu yêu cầu, tạo đề hoặc giải thích lựa chọn, nhưng **không gọi sinh lại HTML**. Không ghi đè Player gốc; so hash HTML trước/sau để nghiệm thu.

### Tạo mới

Lập plan → giáo viên xác nhận → sinh HTML theo contract → kiểm → một lượt sửa nếu cần → chạy sandbox với Exam dự kiến → duyệt → lưu Player draft, Exam và App. Không đưa key vào HTML, không tự mở camera/micro, không gọi mạng từ game. Giữ CSP và sandbox.

## Chỉnh sửa có chọn lọc

| Giáo viên yêu cầu | Thành phần xử lý |
|---|---|
| Đổi chủ đề, câu hỏi, số câu | Exam; kiểm lại tương thích; giữ HTML nếu phù hợp |
| Đổi model/cử chỉ | Model/mapping; kiểm lại hành động và chuột |
| Đổi cơ chế chơi | Player mới/bản nháp riêng, không sửa Player dùng chung |
| Đổi tên App | Metadata ứng dụng |
| Đổi cách chơi chỉ chuột | Chọn Player phù hợp; không lén xóa yêu cầu inputs |

Mọi thay đổi phải ghi changes[] để giáo viên hiểu. Nếu cần thay đổi ngoài thành phần được yêu cầu, giải thích trước.

## Điều kiện ready

Có kết quả lưu hợp lệ; quyền và version còn đúng; các check bắt buộc đạt; có bằng chứng chơi bằng chuột với model chưa sẵn sàng/lỗi; nội dung được kiểm tra và giáo viên duyệt. Nếu còn not_checked bắt buộc, giữ awaiting_review/needs_revision. Không coi smoke test API là bằng chứng runtime.

Chuột và model đi vào cùng hàm hành động của game, dùng chung khóa chọn/điểm/số câu. camera.status không reset game. Kiểm thử chuyển qua lại trong cùng phiên để phát hiện mất tiến độ và chấm điểm hai lần.

## Log và giới hạn

Ghi requestId, chatId, version, bước, thời gian, số lần gọi, model, token và mã lỗi. Không log mật khẩu/key hoặc toàn bộ tài liệu theo mặc định. Tổng số lượt gọi và timeout mỗi bước phải có giới hạn cấu hình. Ban đầu: sinh HTML tối đa 2 lượt, sửa JSON đầu ra tối đa 1 lượt; retry mạng có giới hạn và không được làm tạo trùng.
