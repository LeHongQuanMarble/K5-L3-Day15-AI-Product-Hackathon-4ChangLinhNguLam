# Tổng hợp bằng chứng pain

> Điền ở guide bước 1.2, hoàn thiện trước **CP3 10:00 Thứ Bảy 28/11/2026**. Chấm ở rubric R1.
> Ba nguồn ngang nhau — tối thiểu **≥1 nguồn đạt ngưỡng**.
> **Trạng thái hiện tại (CP3 · 28/11/2026 08:25):** Đã thu thập và chốt **`n = 20` phản hồi khảo sát thực tế** (`P01`–`P20`, lưu ẩn danh tại `evidence/survey/results.csv`, **0 PII**, **0 hồ sơ trùng lặp hoàn toàn**), đạt ngưỡng tối thiểu **≥20 phiếu khảo sát** theo Rubric R1. Ghi nhận minh bạch 1 phiếu mâu thuẫn nội tại (`P13` chọn tất cả phương án kể cả mục phủ định) và cụm 12 phiếu nộp nhanh sáng 28/11 (`P09`–`P20`, trống câu mở); giữ nguyên không tự ý xóa và báo cáo song song phân tích độ nhạy (`n = 19`, loại `P13`).
> **Nguồn bổ trợ benchmark (27/11/2026):** 6 tình huống thật S1–S6 tóm tắt từ 6 phiếu đầu (`P01`–`P06`, xem `docs/HANDOFF-TV4-nguon-nguoi-dung.md` và `eval/benchmark.csv` B21–B30) dùng cho cột `source` của benchmark, **không tính trùng** là nguồn riêng cho Rubric R1.

## 1. Nguồn đã dùng

| Nguồn | Đạt ngưỡng? | File |
|---|---|---|
| Đào data (x/N, %, cách đếm chạy lại được, ≥5 ví dụ) | ☐ *(không sử dụng data thô BTC cho lát cắt A3)* | `evidence/data-mining.md` |
| Phỏng vấn (≥3 người ngoài nhóm, đúng người dùng) | ☐ *(0/3 — chưa thực hiện phỏng vấn sâu)* | `evidence/interviews/TEMPLATE.md` |
| **Khảo sát (≥20 người ngoài nhóm, đúng người dùng)** | **☑ (20/20 — đạt ngưỡng tối thiểu R1; xem mục Hạn chế mẫu)** | `evidence/survey/questions.md` · `evidence/survey/results.csv` |
| Tình huống thật S1–S6 (tóm tắt từ `P01`–`P06`) | ⚠️ *không tính nguồn độc lập R1* | `docs/HANDOFF-TV4-nguon-nguoi-dung.md` · `eval/benchmark.csv` B21–B30 |

## 2. Số chính *(Khảo sát `evidence/survey/results.csv`, `n = 20`, thu từ 27/11/2026 18:12 đến 28/11/2026 08:24)*

- **Phân bố đối tượng (Câu 1 — `n = 20`):**
  - Giáo viên phổ thông & mầm non (**15/20 — 75.0%**): Trung học cơ sở `5/20` (`25.0%`), Tiểu học `4/20` (`20.0%`), Trung học phổ thông `3/20` (`15.0%`), Mầm non `2/20` (`10.0%`), Tiểu học + THCS `1/20` (`5.0%`).
  - Đào tạo bậc cao / trung tâm (**5/20 — 25.0%**): Cao đẳng/Đại học `2/20` (`10.0%`), Trung tâm đào tạo `2/20` (`10.0%`), Lab Coach AI20k `1/20` (`5.0%`, `P05`).
- **Tần suất tổ chức trò chơi (Câu 2 — trong 30 ngày gần đây / tháng):**
  - `1–2 lần/tháng`: **7/20 (`35.0%`)** (`P01, P02, P05, P06, P07, P16, P18`)
  - `3–5 lần/tháng`: **5/20 (`25.0%`)** (`P03, P08, P11, P12, P14`)
  - `6–10 lần/tháng`: **4/20 (`20.0%`)** (`P09, P10, P19, P20`)
  - `Trên 10 lần/tháng`: **4/20 (`20.0%`)** (`P04, P13, P15, P17`; loại `P13`: `3/19 = 15.8%`)
  - *(Tổng `≥ 3 lần/tháng`: **13/20 — 65.0%**. Câu 9 – lý do chưa tổ chức: trống `20/20` vì 100% đều đã tổ chức trong 30 ngày qua.)*
- **Công cụ đang sử dụng (Câu 3 — chọn nhiều):**
  - `Quizizz/Wayground`: **11/20 (`55.0%`)** · `PowerPoint/Google Slides`: **9/20 (`45.0%`)** · `Kahoot`: **9/20 (`45.0%`)** · `Trò chơi trực tiếp không sử dụng phần mềm`: **4/20 (`20.0%`)** · `Blooket`: **2/20 (`10.0%`)** · `Công cụ tự xây dựng`: **2/20 (`10.0%`)** · `Wordwall`: **1/20 (`5.0%`)**.
  - *Tự nhập khác:* `P05` (`"tạo bot trên tele cho học viên thực hành tấn công"`), `P07` (`"Agendaweb, yourhomework,…"`).
- **Khoảng thời gian chuẩn bị 1 trò chơi (Câu 4 — dữ liệu dạng khoảng, không tự nội suy trung bình điểm):**
  - `Từ 10 đến dưới 20 phút`: **8/20 (`40.0%`)** (`n=19`: `7/19 = 36.8%`)
  - `Từ 20 đến dưới 30 phút`: **7/20 (`35.0%`)** (`n=19`: `7/19 = 36.8%`)
  - `Từ 30 đến dưới 60 phút`: **3/20 (`15.0%`)** (`P05, P12, P20`)
  - `Từ 60 phút trở lên`: **2/20 (`10.0%`)** (`P04, P15`)
  - *Tổng hợp khoảng:* **`12/20` (`60.0%`)** tốn **`≥ 20 phút/trò chơi`** (`n=19`: `63.2%`); **`5/20` (`25.0%`)** tốn **`≥ 30 phút/trò chơi`** (`n=19`: `26.3%`).
- **Bước chuẩn bị tốn thời gian nhất (Câu 5 — chọn nhiều):**
  - `Soạn câu hỏi và đáp án`: **13/20 (`65.0%`)** (`n=19`: `63.2%`)
  - `Tìm kiếm công cụ phù hợp`: **10/20 (`50.0%`)** (`n=19`: `47.4%`)
  - `Lựa chọn hình thức tương tác`: **10/20 (`50.0%`)** (`n=19`: `47.4%`)
  - `Thiết kế giao diện và luật chơi`: **7/20 (`35.0%`)** (`n=19`: `31.6%`)
  - `Nhập hoặc chuyển đổi bộ câu hỏi`: **6/20 (`30.0%`)** (`n=19`: `26.3%`)
  - `Kiểm tra tính chính xác của nội dung`: **4/20 (`20.0%`)** (`n=19`: `15.8%`)
  - `Kiểm tra thiết bị và khả năng hoạt động`: **2/20 (`10.0%`)** (`n=19`: `5.3%`)
  - `Không có công việc nào đặc biệt tốn thời gian`: **1/20 (`5.0%`, `P13` — chọn mâu thuẫn cùng 7 mục trên)**
  - *Tự nhập khác:* `P05` (`"test bot tốn thời gian. Set system prompt và guardrails cho nó."`), `P07` (`"Ổn định học sinh"`).
- **Pain point gặp phải trong 30 ngày gần đây (Câu 6 — chọn nhiều):**
  - `Mất nhiều thời gian cấu hình`: **12/20 (`60.0%`)** (`n=19`: `11/19 = 57.9%`)
  - `Hạn chế về thời gian tổ chức`: **11/20 (`55.0%`)** (`n=19`: `10/19 = 52.6%`)
  - `Khó đưa bộ câu hỏi có sẵn vào trò chơi`: **8/20 (`40.0%`)** (`n=19`: `7/19 = 36.8%`)
  - `Câu hỏi hoặc đáp án có sai sót`: **6/20 (`30.0%`)** (`n=19`: `5/19 = 26.3%`)
  - `Thiết bị hoặc phần mềm không tương thích`: **5/20 (`25.0%`)** (`n=19`: `4/19 = 21.1%`)
  - `Công cụ không phù hợp với mục tiêu bài học`: **3/20 (`15.0%`)** (`n=19`: `2/19 = 10.5%`)
  - `Trò chơi gặp lỗi khi sử dụng trên lớp`: **3/20 (`15.0%`)** (`n=19`: `2/19 = 10.5%`)
  - `Không gặp vấn đề đáng kể`: **2/20 (`10.0%`)** (`P15` phản hồi thực + `P13` mâu thuẫn; `n=19`: `1/19 = 5.3%`)
  - `Hạn chế về chi phí`: **1/20 (`5.0%`, `P13`)**
  - *Tổ hợp sự cố kỹ thuật (`không tương thích` HOẶC `lỗi khi dùng trên lớp`):* **7/20 (`35.0%`)** (`P05, P06, P08, P13, P17, P19, P20`; loại `P13`: `6/19 = 31.6%`).
- **Nhu cầu hình thức tương tác (Câu 8 — chọn nhiều):**
  - `Chuột hoặc bàn phím`: **13/20 (`65.0%`)** (`n=19`: `63.2%`)
  - `Màn hình cảm ứng`: **6/20 (`30.0%`)** (`n=19`: `26.3%`)
  - `Cử chỉ hoặc chuyển động cơ thể`: **5/20 (`25.0%`)** (`P04, P07, P08, P09, P11` — Mầm non, Tiểu học/THCS, THPT, CĐ/ĐH; `n=19`: `26.3%`)
  - `Trả lời trực tiếp trên lớp`: **4/20 (`20.0%`)**
  - `Điện thoại cá nhân`: **4/20 (`20.0%`)**
  - `Giọng nói`: **1/20 (`5.0%`, `P04` Mầm non)**
- **Phỏng vấn sâu:** `0/3` *(không thực hiện trong khung CP3; dùng nguồn khảo sát `n = 20` làm nguồn chính đạt ngưỡng R1)*.

## 3. ≥5 trích dẫn nguyên văn ẩn danh (có mã `P01`–`P20`, 0 PII, không diễn giải lại)

1. `"Các cháu nó hiếu động quá nên bảo tập trung vào trò chơi hơi khó."` — `P04` (Mầm non · Câu 7)
2. `"Nếu được tăng lương thì tốt, lúc đó tôi sẽ được dùng AI làm cho tiện."` — `P04` (Mầm non · Câu 10)
3. `"Các LC khóa cũ thỉnh thoảng vẫn hay cho làm Quizz Kahoot cho học viên. Mọi người tham gia cũng khá hào hứng nhưng về sau spam nhiêu quizz quá thành ra nó cũng bị nhàm chán, nên khóa này ko dùng mấy nữa. Hơn nữa là chất lượng câu trả lời cũng chưa được kiểm định kỹ , câu trả lời thiếu thuyết phục, chưa kiểm soát đc hết các bạn cheating"` — `P05` (Lab Coach AI20k · Câu 7)
4. `"Cần làm tốt khâu chuẩn bị nội dung cho từng Day. Câu hỏi phải thật hay và trọng tâm"` — `P05` (Lab Coach AI20k · Câu 10)
5. `"Lớp học mất trật tự hơn hẳn khi các bạn được nghe sẽ có trò chơi, nên việc đau đầu nhất thực ra là ổn định lớp học và đưa hướng dẫn cho học sinh."` — `P07` (Tiểu học, trung học cơ sở · Câu 7)
6. `"Thời gian soạn"` — `P02` (Cao đẳng/Đại học · Câu 10)
7. *(Bổ sung nguyên văn mục tự nhập Câu 5)* `"test bot tốn thời gian. Set system prompt và guardrails cho nó."` — `P05` (Lab Coach AI20k · Câu 5)

*(Tất cả các ô câu mở để trống ở `P01, P03, P06, P08–P20` được giữ nguyên trạng thái trống, không suy diễn hay bịa lời trích dẫn.)*

## 4. Đối chiếu giữa các nguồn & Hạn chế của mẫu

- **Nguồn độc lập hiện có:** 1 nguồn đạt ngưỡng R1 (`evidence/survey/results.csv`, `n = 20`). Chưa có nguồn phỏng vấn sâu (`0/3`) để đối chiếu chéo định tính ở các phiếu `P09`–`P20`.
- **Hạn chế mẫu cần ghi nhận minh bạch:**
  1. **1 phiếu mâu thuẫn nội tại (`P13` — `28/11 08:20:41`, THCS):** chọn đồng thời tất cả lựa chọn (gồm cả `"Không có công việc nào đặc biệt tốn thời gian"` và `"Không gặp vấn đề đáng kể"`). Giữ nguyên trong dữ liệu gốc; kiểm tra độ nhạy loại `P13` (`n = 19`) cho thấy thứ hạng Top pain points & nhu cầu tương tác **không thay đổi**.
  2. **Cụm thời gian thu thập (`P09`–`P20`):** 12 phiếu gửi tập trung trong 8 phút sáng 28/11 (`08:16–08:24`) và không điền câu mở Câu 7, làm độ sâu định tính thấp hơn nhóm 8 phiếu đầu (`P01`–`P08`).
  3. **Dữ liệu thời gian chuẩn bị (Câu 4) ở dạng khoảng:** không cho phép tính trung bình phút chính xác từng cá nhân; dùng phân bố theo khoảng và trung vị khoảng (`20–<30 phút`) làm Baseline.
  4. **Đối tượng đa dạng:** 75% (`15/20`) là giáo viên Mầm non/Phổ thông; 25% (`5/20`) thuộc CĐ/ĐH, Trung tâm đào tạo và Lab Coach AI20k.

## 5. Kết luận & Kiểm chứng giả thuyết (`evidence/hypothesis.md`)

> **Phân biệt rõ 3 mức độ xác thực (không đánh đồng khảo sát nhu cầu với kiểm chứng sản phẩm):**
> - **Problem Validation (Xác thực vấn đề):** **Có bằng chứng khảo sát (`n = 20`)** — xác nhận giáo viên thật sự gặp pain về soạn câu hỏi/đáp án (`65%`), cấu hình mất thời gian (`60%`), hạn chế thời gian tổ chức (`55%`), khó nạp bộ đề có sẵn (`40%`), và lỗi tương thích/trên lớp (`35%`).
> - **Hypothesis Validation (Kiểm chứng giả thuyết):** **Xác nhận phần lớn giả thuyết về pain & `Mouse Fallback`**, nhưng **tổ hợp `≥ 30 phút` hoặc lỗi kỹ thuật chỉ đạt `50.0%` (`n=19: 47.4%`), thấp hơn ngưỡng gốc `66.7%`** — cần ghi nhận trung thực.
> - **Product Validation (Xác thực giải pháp/sản phẩm):** **CHƯA ĐẠT** — khảo sát chỉ đo hành vi & Baseline hiện tại; **chưa đo thời gian *With Agent* từ giáo viên thật (chờ T04 UAT)**, do đó **KHÔNG tuyên bố sản phẩm đã giảm thời gian chuẩn bị**.

| Giả thuyết / Tiêu chí | Trạng thái | Bằng chứng từ khảo sát (`n = 20`) |
|---|---|---|
| **H-Pain 1:** Giáo viên tốn nhiều công cấu hình, soạn/đưa bộ câu hỏi vào trò chơi | **XÁC NHẬN** | `Mất nhiều thời gian cấu hình` **60% (`12/20`)**; `Soạn câu hỏi và đáp án` **65% (`13/20`)**; `Khó đưa bộ câu hỏi có sẵn vào trò chơi` **40% (`8/20`)**; `Câu hỏi/đáp án sai sót` **30% (`6/20`)**. |
| **H-Alt (Giả thuyết thay thế):** Điểm nghẽn thực sự nằm ở soạn câu hỏi & thời lượng lớp học | **XÁC NHẬN SONG SONG** | `Soạn câu hỏi và đáp án` (**65%**) và `Hạn chế về thời gian tổ chức` (**55%**) nằm trong Top 2 — chứng minh chỉ chọn vỏ game là chưa đủ, cần **sinh & chuẩn hóa bộ câu hỏi kèm HITL duyệt đáp án**. |
| **H-Tech (Tiêu chí gốc ≥ 2/3 tốn ≥ 30 phút hoặc lỗi tương thích/trên lớp)** | **XÁC NHẬN MỘT PHẦN (CHƯA ĐẠT NGƯỠNG 66.7%)** | Tổ hợp `≥ 30 phút` (`25%`, `5/20`) HOẶC `không tương thích/lỗi lớp` (`35%`, `7/20`) đạt **50.0% (`10/20`; `n=19`: `47.4%`)** — thấp hơn ngưỡng giả thuyết ban đầu `66.7%`. Tuy nhiên, **60% (`12/20`)** tốn `≥ 20 phút/trò chơi` và **35%** thực sự gặp lỗi tương thích/trên lớp. |
| **H-Interaction:** `Mouse Fallback` là nền tảng bắt buộc; cử chỉ có nhu cầu thực nhưng không phải số đông | **XÁC NHẬN** | `Chuột/bàn phím` **65% (`13/20`)**, `Màn hình cảm ứng` **30% (`6/20`)** vs `Cử chỉ/chuyển động cơ thể` **25% (`5/20`)**, `Giọng nói` **5% (`1/20`)**. Khẳng định bắt buộc giữ `Mouse Fallback` và giữ `audio` ngoài P0. |
| **H-Value:** AI Game Composer giúp giảm thời gian chuẩn bị thực tế (*With Agent < Baseline*) | **CHƯA XÁC NHẬN** | Khảo sát chỉ đo **nhu cầu & Baseline hiện tại**; chưa có thử nghiệm đo thời gian *With Agent* trên giáo viên thật → **không kết luận** sản phẩm đã được product-validated. |
| **Phản hồi bất lợi / ngoài phạm vi công cụ** | **GHI NHẬN TRUNG THỰC** | `P15` không gặp vấn đề đáng kể (chơi trực tiếp không phần mềm); `P07` đau đầu nhất là ổn định trật tự lớp; `P04` lo chi phí dùng AI; `P05` cảnh báo nhàm chán do spam quiz và cheating. |

- **Baseline bàn giao cho TV4 (`cost/personas.yaml` & `data/DATA_CARD.md`):**
  - **Tần suất tổ chức trò chơi / 30 ngày (tháng):** `1–2 lần` (`35%`), `3–5 lần` (`25%`), `6–10 lần` (`20%`), `>10 lần` (`20%`) — gợi ý 3 persona khớp dữ liệu thật: **Ít (`1–2 lần/tháng`, 35%)**, **Vừa (`3–5 lần/tháng`, 25%)**, **Nhiều (`≥ 6 lần/tháng`, 40%)**.
  - **Thời gian chuẩn bị Baseline / trò chơi:** `10–<20 phút` (`40%`), `20–<30 phút` (`35%`), `30–<60 phút` (`15%`), `≥ 60 phút` (`10%`) — **trung vị khoảng: `20–<30 phút/trò chơi`** (`60%` tốn `≥ 20 phút`).
  - **Impact / tháng:** Chưa tính thành số tiết kiệm vì chưa có thời gian *With Agent* đo thực nghiệm (chờ T04 UAT).
