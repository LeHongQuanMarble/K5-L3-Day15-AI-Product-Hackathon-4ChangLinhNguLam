# Giả thuyết — viết TRƯỚC khi tìm bằng chứng (5 phút, commit ngay)

> Điền ở guide bước 1.1. Ôn lại: ngày 2 · lab ngày 2.
> Viết **trước** khi đọc dòng data đầu tiên hay hỏi người đầu tiên, để không sửa cho khớp kết quả. Kết quả ngược giả thuyết vẫn đủ điểm nếu số là thật.

- Ngày giờ viết: 27/11/2026 16:20 (UTC+7)
- Người dùng chính (một vai cụ thể): Giáo viên / giảng viên trực tiếp soạn và tổ chức trò chơi ôn tập tương tác cho buổi học.
- **Mình nghĩ:** Khi chuẩn bị trò chơi ôn tập cho bài giảng, giáo viên phải tự lựa chọn hình thức tương tác, đưa bộ câu hỏi vào trò chơi và kiểm tra tính tương thích với thiết bị sử dụng, khiến quá trình chuẩn bị tốn thời gian và có nguy cơ gián đoạn khi tổ chức trên lớp.
- **Có thể còn cách giải thích khác:** Giáo viên đã quen sử dụng các công cụ có sẵn (như Kahoot, Quizizz hoặc slide hỏi đáp truyền thống) và điểm nghẽn thực sự nằm ở khâu soạn bộ câu hỏi hoặc thiếu thời lượng trên lớp, chứ không phải khâu lựa chọn hình thức tương tác hay kiểm tra tính tương thích thiết bị.
- **Mình đúng nếu thấy:** *(Tiêu chí giả thuyết đặt trước khi nghiên cứu — chưa phải kết quả nghiên cứu)* Tối thiểu 2/3 giáo viên/giảng viên ngoài nhóm được phỏng vấn kể được ít nhất 1 lần cụ thể trong 1 tháng qua phải tốn ≥30 phút cho việc chọn công cụ/cấu hình trò chơi ôn tập hoặc gặp sự cố tương thích thiết bị/bộ câu hỏi khi đưa lên lớp.
- **Nguồn sẽ dùng** (≥1 nguồn đạt ngưỡng, guide 1.2 — *tất cả hiện CHƯA thu thập*): [ ] đào data · [ ] phỏng vấn ≥3 *(nguồn chính dự kiến)* · [ ] khảo sát ≥20 *(phương án bổ sung nếu khả thi)* — nguồn chính: phỏng vấn tối thiểu 3 giáo viên/giảng viên ngoài nhóm · nguồn bổ sung (nếu khả thi): khảo sát hành vi tối thiểu 20 người ngoài nhóm.

## Chi tiết các giả thuyết nghiệp vụ & sản phẩm *(Trạng thái: CHƯA ĐƯỢC XÁC THỰC)*

1. **Giả thuyết về người dùng:** Giáo viên/giảng viên có nhu cầu tạo hoạt động trò chơi ôn tập tương tác gắn với bộ câu hỏi của bài giảng nhưng bị giới hạn thời gian chuẩn bị và không muốn phải tự lập trình hay cấu hình kỹ thuật phức tạp.
2. **Giả thuyết về vấn đề:** Quy trình chọn hình thức tương tác, đưa bộ câu hỏi vào trò chơi và kiểm tra tính tương thích với thiết bị lớp học hiện còn rời rạc, tốn thời gian và dễ phát sinh lỗi khi vận hành trên lớp.
3. **Giả thuyết về giá trị sản phẩm:** Việc để hệ thống phân tích yêu cầu giảng dạy, lựa chọn tổ hợp `Model + Player` phù hợp từ Catalog, kiểm tra tính tương thích và cho giáo viên phê duyệt (HITL) trước khi ghép nối trò chơi sẽ giúp giảm thời gian chuẩn bị và kiểm duyệt.
4. **Giả thuyết về tính khả thi (phạm vi P0):** Catalog hiện có trong AI Lab (`Model + Player + Question Set`) kết hợp Mouse Fallback đáp ứng được các nhu cầu ôn tập phổ biến qua luồng `REUSE`; các yêu cầu ngoài Catalog dừng ở mức đề xuất kế hoạch (`PROPOSE_GENERATE`) ở P0.

## Nội dung chưa được xác thực & Chỉ số dự kiến đo lường
- **Chưa được xác thực:** Tần suất tạo trò chơi ôn tập mỗi tháng của giáo viên; thời gian thực tế cho từng bước chuẩn bị và kiểm duyệt; mức độ sẵn sàng sử dụng tương tác camera/cử chỉ so với chuột trong điều kiện lớp học thật; tỉ lệ gặp sự cố thiết bị.
- **Phương pháp xác thực:** Phỏng vấn trực tiếp theo nguyên tắc Mom Test với tối thiểu 3 giáo viên/giảng viên ngoài nhóm (ghi chép ẩn danh từng người vào `evidence/interviews/P1.md`…); bổ sung khảo sát hành vi ≥20 người nếu khả thi trước CP3.
- **Chỉ số dự kiến đo lường:**
  - Thời gian hoàn thành tạo và kiểm duyệt 1 trò chơi sẵn sàng dùng trên lớp (phút/trò chơi).
  - Tỉ lệ lựa chọn đúng tổ hợp `Model + Player` tương thích trên bộ câu thử (`eval/benchmark.csv`).
  - Tỉ lệ xử lý đúng các nhánh cần hỏi lại (`ASK_CLARIFY`), đề xuất tạo mới (`PROPOSE_GENERATE`) và từ chối hợp lệ (`REFUSE`).

## 5 câu hỏi phỏng vấn theo hướng Mom Test *(tập trung hành vi quá khứ, không dẫn dắt)*
1. "Lần gần nhất thầy/cô chuẩn bị một trò chơi hoặc hoạt động ôn tập tương tác cho buổi học là khi nào? Thầy/cô đã thực hiện những bước nào từ lúc có bộ câu hỏi đến khi đưa lên lớp?"
2. "Trong lần chuẩn bị đó, bước nào tốn nhiều thời gian nhất và mất khoảng bao lâu? Điều gì khiến bước đó kéo dài?"
3. "Thầy/cô đã từng gặp trường hợp trò chơi hoặc hoạt động tương tác chuẩn bị sẵn bị trục trặc (về thiết bị, hiển thị hoặc câu hỏi) trước hoặc trong giờ học chưa? Khi đó thầy/cô đã xử lý ra sao?"
4. "Hiện tại thầy/cô đang sử dụng công cụ nào để tạo hoạt động ôn tập từ bộ câu hỏi? Lý do nào khiến thầy/cô tiếp tục dùng công cụ đó và điểm nào gây bất tiện nhất?"
5. "Trong một tháng qua, có buổi học nào thầy/cô dự định tổ chức trò chơi ôn tập nhưng cuối cùng không thực hiện không? Lý do chính lúc đó là gì?"

---

## Đối chiếu sau khảo sát (`n = 21` · cập nhật 28/11/2026 08:55, không sửa giả thuyết gốc ở trên)

- **Nguồn đạt ngưỡng:** `[x] khảo sát ≥20` (`21/20` phản hồi ẩn danh `P01`–`P21` tại `evidence/survey/results.csv`; kể cả khi loại `P13` mâu thuẫn vẫn đạt **`20/20` phiếu hợp lệ**; phỏng vấn `0/3`).
- **Xác nhận:** Pain về **mất thời gian cấu hình (`61.9%`; `n=20: 60.0%`)**, **soạn câu hỏi/đáp án (`61.9%`; `n=20: 60.0%`)**, **khó đưa bộ đề có sẵn vào trò chơi (`38.1%`)**, **sai sót câu hỏi/đáp án (`33.3%`)**, và vai trò bắt buộc của **`Mouse Fallback` (`66.7%` chuột/bàn phím + `28.6%` cảm ứng)** so với cử chỉ (`23.8%`) và giọng nói (`4.8%`). Giả thuyết thay thế về điểm nghẽn **soạn câu hỏi (`61.9%`) & hạn chế thời lượng tổ chức (`52.4%`)** cũng được xác nhận song song.
- **Xác nhận một phần (thấp hơn ngưỡng gốc `2/3 = 66.7%`):** Tổ hợp tốn `≥ 30 phút` (`23.8%`) HOẶC gặp lỗi tương thích/trên lớp (`33.3%`) đạt **`47.6%` (`10/21`; loại `P13`: `45.0%`, `9/20`)**; tuy nhiên **`61.9%` (`13/21`; `n=20: 65.0%`)** tốn `≥ 20 phút/trò chơi`.
- **Chưa xác nhận:** Giả thuyết giá trị sản phẩm (tiết kiệm thời gian *With Agent*) chưa được kiểm chứng thực nghiệm vì khảo sát chỉ đo nhu cầu & Baseline (chờ T04 UAT). Chi tiết đầy đủ xem `evidence/summary.md`.
