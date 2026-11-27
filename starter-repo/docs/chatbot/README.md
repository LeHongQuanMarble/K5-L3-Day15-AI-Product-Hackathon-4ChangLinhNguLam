# Bàn giao Trợ lý game

Đây là bộ tài liệu giao việc cho **agent điều phối** và các **agent coder**. Agent đang tạo bộ tài liệu này giữ vai trò **review (kiểm tra độc lập)**, không phải agent điều phối triển khai.

## Cách bắt đầu

1. Đọc `AGENTS.md` tại `starter-repo/`, rồi đọc các tài liệu dưới đây theo thứ tự.
2. Kiểm tra Git và đọc lại mã nguồn hiện tại. Mốc khảo sát là `faa44a8`, nhánh `feature/chatbot`; mã có thể đã thay đổi sau bàn giao.
3. Hoàn thành cổng G0 trong `AI_IMPLEMENTATION_PLAN.md` trước khi giao việc viết mã.
4. Giao từng nhiệm vụ có phạm vi file rõ ràng. Không để hai agent cùng sửa một file.
5. Gửi bản thay đổi và bằng chứng kiểm thử cho agent review. Không tự coi việc coder hoàn thành là nghiệm thu cuối.

## Danh mục tài liệu

| File | Nội dung |
|---|---|
| [AI_PROJECT_CONTEXT.md](AI_PROJECT_CONTEXT.md) | Mục tiêu, phạm vi, hiện trạng và ràng buộc |
| [AI_INTEGRATION_CONTRACT.md](AI_INTEGRATION_CONTRACT.md) | Đầu vào, đầu ra, dữ liệu, API và quyền xác nhận |
| [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) | Kiến trúc, ranh giới trách nhiệm, cấu trúc mã đề xuất |
| [AI_PIPELINE.md](AI_PIPELINE.md) | Trạng thái, phân nhánh, duyệt, tự sửa và chỉnh sửa |
| [AI_IMPLEMENTATION_PLAN.md](AI_IMPLEMENTATION_PLAN.md) | Đợt triển khai, nhiệm vụ coder, phụ thuộc, phạm vi và nghiệm thu |
| [AI_TEST_CONTRACT.md](AI_TEST_CONTRACT.md) | Bộ tình huống và yêu cầu bằng chứng |
| [AI_PROGRESS.md](AI_PROGRESS.md) | Tiến độ thực tế, vấn đề mở và quyết định |
| [AI_HANDOFF.md](AI_HANDOFF.md) | Hướng dẫn điều phối và prompt khởi động |
| [AI_REVIEW_CHECKLIST.md](AI_REVIEW_CHECKLIST.md) | Quy trình review, mức độ lỗi, mẫu báo cáo |

## Trạng thái của bộ tài liệu

Yêu cầu sản phẩm xuất phát từ các xác nhận của người dùng. Các tên module, hàm, trường JSON và endpoint mới trong tài liệu là **thiết kế đề xuất**, chưa phải API đang hoạt động. Điều phối phải đối chiếu tính khả thi và chốt quyết định tại G0, không được bỏ yêu cầu sản phẩm để khớp mã hiện có.

Không sửa `spec.md` §7 hoặc `eval/metric_spec.yaml` đã khóa theo mốc Hackathon. Bộ kiểm thử bổ sung ở đây không thay thế tiêu chí chấm đã khóa.
