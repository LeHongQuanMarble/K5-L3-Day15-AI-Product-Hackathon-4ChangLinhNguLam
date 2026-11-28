# Tổng hợp bằng chứng pain

> Điền ở guide bước 1.2, hoàn thiện trước **CP3 10:00 Thứ Bảy 28/11/2026**. Chấm ở rubric R1.
> Ba nguồn ngang nhau — tối thiểu **≥1 nguồn đạt ngưỡng**.
> **Trạng thái hiện tại (CP3 · 28/11/2026 08:55):** Đã thu thập và chốt **`n = 21` phản hồi khảo sát thực tế** (`P01`–`P21`, lưu ẩn danh tại `evidence/survey/results.csv`, **0 PII**, **0 hồ sơ trùng lặp hoàn toàn**). Ghi nhận minh bạch 1 phiếu mâu thuẫn nội tại (`P13` chọn tất cả phương án kể cả mục phủ định) và cụm 12 phiếu nộp nhanh sáng 28/11 (`P09`–`P20`, trống câu mở); giữ nguyên không tự ý xóa và báo cáo song song phân tích độ nhạy loại `P13` (**`n = 20` phiếu hợp lệ sạch**, vẫn **đạt đủ ngưỡng tối thiểu ≥20 phiếu khảo sát** theo Rubric R1 ngay cả khi loại `P13`).
> **Nguồn bổ trợ benchmark (27/11/2026):** 6 tình huống thật S1–S6 tóm tắt từ 6 phiếu đầu (`P01`–`P06`, xem `docs/HANDOFF-TV4-nguon-nguoi-dung.md` và `eval/benchmark.csv` B21–B30) dùng cho cột `source` của benchmark, **không tính trùng** là nguồn riêng cho Rubric R1.

## 1. Nguồn đã dùng

| Nguồn | Đạt ngưỡng? | File |
|---|---|---|
| Đào data (x/N, %, cách đếm chạy lại được, ≥5 ví dụ) | ☐ *(không sử dụng data thô BTC cho lát cắt A3)* | `evidence/data-mining.md` |
| Phỏng vấn (≥3 người ngoài nhóm, đúng người dùng) | ☐ *(0/3 — chưa thực hiện phỏng vấn sâu)* | `evidence/interviews/TEMPLATE.md` |
| **Khảo sát (≥20 người ngoài nhóm, đúng người dùng)** | **☑ (`21/20` tổng; `20/20` hợp lệ khi loại `P13` — đạt vững ngưỡng R1)** | `evidence/survey/questions.md` · `evidence/survey/results.csv` |
| Tình huống thật S1–S6 (tóm tắt từ `P01`–`P06`) | ⚠️ *không tính nguồn độc lập R1* | `docs/HANDOFF-TV4-nguon-nguoi-dung.md` · `eval/benchmark.csv` B21–B30 |

## 2. Số chính *(Khảo sát `evidence/survey/results.csv`, `n = 21`, thu từ 27/11/2026 18:12 đến 28/11/2026 08:54; độ nhạy loại `P13`: `n = 20`)*

- **Phân bố đối tượng (Câu 1 — `n = 21`):**
  - Giáo viên phổ thông & mầm non (**16/21 — 76.2%**; `n=20`: `15/20 = 75.0%`): Trung học cơ sở `6/21` (`28.6%`), Tiểu học `4/21` (`19.0%`), Trung học phổ thông `3/21` (`14.3%`), Mầm non `2/21` (`9.5%`), Tiểu học + THCS `1/21` (`4.8%`).
  - Đào tạo bậc cao / trung tâm (**5/21 — 23.8%**; `n=20`: `5/20 = 25.0%`): Cao đẳng/Đại học `2/21` (`9.5%`), Trung tâm đào tạo `2/21` (`9.5%`), Lab Coach AI20k `1/21` (`4.8%`, `P05`).
- **Tần suất tổ chức trò chơi (Câu 2 — trong 30 ngày gần đây / tháng):**
  - `1–2 lần/tháng`: **7/21 (`33.3%`)** (`n=20`: `7/20 = 35.0%`) (`P01, P02, P05, P06, P07, P16, P18`)
  - `3–5 lần/tháng`: **6/21 (`28.6%`)** (`n=20`: `6/20 = 30.0%`) (`P03, P08, P11, P12, P14, P21`)
  - `6–10 lần/tháng`: **4/21 (`19.0%`)** (`n=20`: `4/20 = 20.0%`) (`P09, P10, P19, P20`)
  - `Trên 10 lần/tháng`: **4/21 (`19.0%`)** (`n=20`: `3/20 = 15.0%`) (`P04, P13, P15, P17`)
  - *(Tổng `≥ 3 lần/tháng`: **14/21 — 66.7%**; `n=20`: `13/20 = 65.0%`. Câu 9 – lý do chưa tổ chức: trống `21/21` vì 100% đều đã tổ chức trong 30 ngày qua.)*
- **Công cụ đang sử dụng (Câu 3 — chọn nhiều):**
  - `Quizizz/Wayground`: **12/21 (`57.1%`)** (`n=20`: `55.0%`) · `PowerPoint/Google Slides`: **10/21 (`47.6%`)** (`n=20`: `50.0%`) · `Kahoot`: **10/21 (`47.6%`)** (`n=20`: `45.0%`) · `Trò chơi trực tiếp không sử dụng phần mềm`: **4/21 (`19.0%`)** · `Blooket`: **2/21 (`9.5%`)** · `Công cụ tự xây dựng`: **2/21 (`9.5%`)** · `Wordwall`: **1/21 (`4.8%`)**.
  - *Tự nhập khác:* `P05` (`"tạo bot trên tele cho học viên thực hành tấn công"`), `P07` (`"Agendaweb, yourhomework,…"`).
- **Khoảng thời gian chuẩn bị 1 trò chơi (Câu 4 — dữ liệu dạng khoảng, không tự nội suy trung bình điểm):**
  - `Từ 10 đến dưới 20 phút`: **8/21 (`38.1%`)** (`n=20`: `7/20 = 35.0%`)
  - `Từ 20 đến dưới 30 phút`: **8/21 (`38.1%`)** (`n=20`: `8/20 = 40.0%`)
  - `Từ 30 đến dưới 60 phút`: **3/21 (`14.3%`)** (`n=20`: `3/20 = 15.0%`) (`P05, P12, P20`)
  - `Từ 60 phút trở lên`: **2/21 (`9.5%`)** (`n=20`: `2/20 = 10.0%`) (`P04, P15`)
  - *Tổng hợp khoảng:* **`13/21` (`61.9%`)** tốn **`≥ 20 phút/trò chơi`** (`n=20`: `13/20 = 65.0%`); **`5/21` (`23.8%`)** tốn **`≥ 30 phút/trò chơi`** (`n=20`: `5/20 = 25.0%`).
- **Bước chuẩn bị tốn thời gian nhất (Câu 5 — chọn nhiều):**
  - `Soạn câu hỏi và đáp án`: **13/21 (`61.9%`)** (`n=20`: `12/20 = 60.0%`)
  - `Lựa chọn hình thức tương tác`: **11/21 (`52.4%`)** (`n=20`: `10/20 = 50.0%`)
  - `Tìm kiếm công cụ phù hợp`: **10/21 (`47.6%`)** (`n=20`: `9/20 = 45.0%`)
  - `Thiết kế giao diện và luật chơi`: **8/21 (`38.1%`)** (`n=20`: `7/20 = 35.0%`)
  - `Nhập hoặc chuyển đổi bộ câu hỏi`: **7/21 (`33.3%`)** (`n=20`: `6/20 = 30.0%`)
  - `Kiểm tra tính chính xác của nội dung`: **4/21 (`19.0%`)** (`n=20`: `3/20 = 15.0%`)
  - `Kiểm tra thiết bị và khả năng hoạt động`: **2/21 (`9.5%`)** (`n=20`: `1/20 = 5.0%`)
  - `Không có công việc nào đặc biệt tốn thời gian`: **1/21 (`4.8%`, `P13` — chọn mâu thuẫn cùng 7 mục trên)**
  - *Tự nhập khác:* `P05` (`"test bot tốn thời gian. Set system prompt và guardrails cho nó."`), `P07` (`"Ổn định học sinh"`).
- **Pain point gặp phải trong 30 ngày gần đây (Câu 6 — chọn nhiều):**
  - `Mất nhiều thời gian cấu hình`: **13/21 (`61.9%`)** (`n=20`: `12/20 = 60.0%`)
  - `Hạn chế về thời gian tổ chức`: **11/21 (`52.4%`)** (`n=20`: `10/20 = 50.0%`)
  - `Khó đưa bộ câu hỏi có sẵn vào trò chơi`: **8/21 (`38.1%`)** (`n=20`: `7/20 = 35.0%`)
  - `Câu hỏi hoặc đáp án có sai sót`: **7/21 (`33.3%`)** (`n=20`: `6/20 = 30.0%`)
  - `Thiết bị hoặc phần mềm không tương thích`: **5/21 (`23.8%`)** (`n=20`: `4/20 = 20.0%`)
  - `Công cụ không phù hợp với mục tiêu bài học`: **4/21 (`19.0%`)** (`n=20`: `3/20 = 15.0%`)
  - `Trò chơi gặp lỗi khi sử dụng trên lớp`: **3/21 (`14.3%`)** (`n=20`: `2/20 = 10.0%`)
  - `Không gặp vấn đề đáng kể`: **2/21 (`9.5%`)** (`P15` phản hồi thực + `P13` mâu thuẫn; `n=20`: `1/20 = 5.0%`)
  - `Hạn chế về chi phí`: **1/21 (`4.8%`, `P13`)**
  - *Tổ hợp sự cố kỹ thuật (`không tương thích` HOẶC `lỗi khi dùng trên lớp`):* **7/21 (`33.3%`)** (`P05, P06, P08, P13, P17, P19, P20`; loại `P13`: `6/20 = 30.0%`).
- **Nhu cầu hình thức tương tác (Câu 8 — chọn nhiều):**
  - `Chuột hoặc bàn phím`: **14/21 (`66.7%`)** (`n=20`: `13/20 = 65.0%`)
  - `Màn hình cảm ứng`: **6/21 (`28.6%`)** (`n=20`: `5/20 = 25.0%`)
  - `Cử chỉ hoặc chuyển động cơ thể`: **5/21 (`23.8%`)** (`P04, P07, P08, P09, P11` — Mầm non, Tiểu học/THCS, THPT, CĐ/ĐH; `n=20`: `5/20 = 25.0%`)
  - `Điện thoại cá nhân`: **5/21 (`23.8%`)** (`n=20`: `5/20 = 25.0%`)
  - `Trả lời trực tiếp trên lớp`: **4/21 (`19.0%`)** (`n=20`: `4/20 = 20.0%`)
  - `Giọng nói`: **1/21 (`4.8%`, `P04` Mầm non; `n=20`: `5.0%`)**
- **Phỏng vấn sâu:** `0/3` *(không thực hiện trong khung CP3; dùng nguồn khảo sát `n = 21` — và `n = 20` khi loại `P13` — làm nguồn chính đạt vững ngưỡng R1)*.

## 3. ≥5 trích dẫn nguyên văn ẩn danh (7 trích dẫn có mã `P01`–`P21`, 0 PII, giữ nguyên không diễn giải lại)

1. `"Các cháu nó hiếu động quá nên bảo tập trung vào trò chơi hơi khó."` — `P04` (Mầm non · Câu 7)
2. `"Nếu được tăng lương thì tốt, lúc đó tôi sẽ được dùng AI làm cho tiện."` — `P04` (Mầm non · Câu 10)
3. `"Các LC khóa cũ thỉnh thoảng vẫn hay cho làm Quizz Kahoot cho học viên. Mọi người tham gia cũng khá hào hứng nhưng về sau spam nhiêu quizz quá thành ra nó cũng bị nhàm chán, nên khóa này ko dùng mấy nữa. Hơn nữa là chất lượng câu trả lời cũng chưa được kiểm định kỹ , câu trả lời thiếu thuyết phục, chưa kiểm soát đc hết các bạn cheating"` — `P05` (Lab Coach AI20k · Câu 7)
4. `"Cần làm tốt khâu chuẩn bị nội dung cho từng Day. Câu hỏi phải thật hay và trọng tâm"` — `P05` (Lab Coach AI20k · Câu 10)
5. `"Lớp học mất trật tự hơn hẳn khi các bạn được nghe sẽ có trò chơi, nên việc đau đầu nhất thực ra là ổn định lớp học và đưa hướng dẫn cho học sinh."` — `P07` (Tiểu học, trung học cơ sở · Câu 7)
6. `"Thời gian soạn"` — `P02` (Cao đẳng/Đại học · Câu 10)
7. *(Bổ sung nguyên văn mục tự nhập Câu 5)* `"test bot tốn thời gian. Set system prompt và guardrails cho nó."` — `P05` (Lab Coach AI20k · Câu 5)

*(Tất cả các ô câu mở để trống ở `P01, P03, P06, P08–P21` được giữ nguyên trạng thái trống, không suy diễn hay bịa lời trích dẫn.)*

## 4. Đối chiếu giữa các nguồn & Hạn chế của mẫu

- **Nguồn độc lập hiện có:** 1 nguồn đạt vững ngưỡng R1 (`evidence/survey/results.csv`, `n = 21`, và `n = 20` hợp lệ khi loại `P13`). Chưa có nguồn phỏng vấn sâu (`0/3`) để đối chiếu chéo định tính ở các phiếu `P09`–`P21`.
- **Hạn chế mẫu cần ghi nhận minh bạch:**
  1. **1 phiếu mâu thuẫn nội tại (`P13` — `28/11 08:20:41`, THCS):** chọn đồng thời tất cả lựa chọn (gồm cả `"Không có công việc nào đặc biệt tốn thời gian"` và `"Không gặp vấn đề đáng kể"`). Giữ nguyên trong dữ liệu gốc; nhờ bổ sung `P21`, phân tích độ nhạy loại `P13` vẫn giữ đủ **`n = 20` phiếu hợp lệ** và thứ hạng Top pain points & nhu cầu tương tác **không thay đổi**.
  2. **Cụm thời gian thu thập (`P09`–`P20`):** 12 phiếu gửi tập trung trong 8 phút sáng 28/11 (`08:16–08:24`) và không điền câu mở Câu 7 (cùng `P21` lúc `08:54:30`), làm độ sâu định tính thấp hơn nhóm 8 phiếu đầu (`P01`–`P08`).
  3. **Dữ liệu thời gian chuẩn bị (Câu 4) ở dạng khoảng:** không cho phép tính trung bình phút chính xác từng cá nhân; dùng phân bố theo khoảng và trung vị khoảng (`20–<30 phút`) làm Baseline.
  4. **Đối tượng đa dạng:** 76.2% (`16/21`) là giáo viên Mầm non/Phổ thông; 23.8% (`5/21`) thuộc CĐ/ĐH, Trung tâm đào tạo và Lab Coach AI20k.

## 5. Kết luận & Kiểm chứng giả thuyết (`evidence/hypothesis.md`)

> **Phân biệt rõ 3 mức độ xác thực (không đánh đồng khảo sát nhu cầu với kiểm chứng sản phẩm):**
> - **Problem Validation (Xác thực vấn đề):** **Có bằng chứng khảo sát (`n = 21`; loại `P13`: `n = 20`)** — xác nhận giáo viên thật sự gặp pain về cấu hình mất thời gian (`61.9%`), soạn câu hỏi/đáp án (`61.9%`), hạn chế thời gian tổ chức (`52.4%`), khó nạp bộ đề có sẵn (`38.1%`), sai sót câu hỏi/đáp án (`33.3%`) và lỗi tương thích/trên lớp (`33.3%`).
> - **Hypothesis Validation (Kiểm chứng giả thuyết):** **Xác nhận phần lớn giả thuyết về pain & `Mouse Fallback`**, nhưng **tổ hợp `≥ 30 phút` hoặc lỗi kỹ thuật chỉ đạt `47.6%` (`n=20: 45.0%`), thấp hơn ngưỡng gốc `66.7%`** — cần ghi nhận trung thực.
> - **Product Validation (Xác thực giải pháp/sản phẩm):** **CHƯA ĐẠT** — khảo sát chỉ đo hành vi & Baseline hiện tại; **chưa đo thời gian *With Agent* từ giáo viên thật (chờ T04 UAT)**, do đó **KHÔNG tuyên bố sản phẩm đã giảm thời gian chuẩn bị**.

| Giả thuyết / Tiêu chí | Trạng thái | Bằng chứng từ khảo sát (`n = 21` · nhạy `n = 20` loại `P13`) |
|---|---|---|
| **H-Pain 1:** Giáo viên tốn nhiều công cấu hình, soạn/đưa bộ câu hỏi vào trò chơi | **XÁC NHẬN** | `Mất nhiều thời gian cấu hình` **61.9% (`13/21`; `n=20: 60.0%`)**; `Soạn câu hỏi và đáp án` **61.9% (`13/21`; `n=20: 60.0%`)**; `Khó đưa bộ câu hỏi có sẵn vào trò chơi` **38.1% (`8/21`; `n=20: 35.0%`)**; `Câu hỏi/đáp án sai sót` **33.3% (`7/21`; `n=20: 30.0%`)**. |
| **H-Alt (Giả thuyết thay thế):** Điểm nghẽn thực sự nằm ở soạn câu hỏi & thời lượng lớp học | **XÁC NHẬN SONG SONG** | `Soạn câu hỏi và đáp án` (**61.9%**) và `Hạn chế về thời gian tổ chức` (**52.4%**) nằm trong Top 2 — chứng minh chỉ chọn vỏ game là chưa đủ, cần **sinh & chuẩn hóa bộ câu hỏi kèm HITL duyệt đáp án**. |
| **H-Tech (Tiêu chí gốc ≥ 2/3 tốn ≥ 30 phút hoặc lỗi tương thích/trên lớp)** | **XÁC NHẬN MỘT PHẦN (CHƯA ĐẠT NGƯỠNG 66.7%)** | Tổ hợp `≥ 30 phút` (`23.8%`, `5/21`) HOẶC `không tương thích/lỗi lớp` (`33.3%`, `7/21`) đạt **47.6% (`10/21`; `n=20`: `45.0%`)** — thấp hơn ngưỡng giả thuyết ban đầu `66.7%`. Tuy nhiên, **61.9% (`13/21`; `n=20: 65.0%`)** tốn `≥ 20 phút/trò chơi` và **33.3%** thực sự gặp lỗi tương thích/trên lớp. |
| **H-Interaction:** `Mouse Fallback` là nền tảng bắt buộc; cử chỉ có nhu cầu thực nhưng không phải số đông | **XÁC NHẬN** | `Chuột/bàn phím` **66.7% (`14/21`; `n=20: 65.0%`)**, `Màn hình cảm ứng` **28.6% (`6/21`)** vs `Cử chỉ/chuyển động cơ thể` **23.8% (`5/21`)**, `Giọng nói` **4.8% (`1/21`)**. Khẳng định bắt buộc giữ `Mouse Fallback` và giữ `audio` ngoài P0. |
| **H-Value:** AI Game Composer giúp giảm thời gian chuẩn bị thực tế (*With Agent < Baseline*) | **CHƯA XÁC NHẬN** | Khảo sát chỉ đo **nhu cầu & Baseline hiện tại**; chưa có thử nghiệm đo thời gian *With Agent* trên giáo viên thật → **không kết luận** sản phẩm đã được product-validated. |
| **Phản hồi bất lợi / ngoài phạm vi công cụ** | **GHI NHẬN TRUNG THỰC** | `P15` không gặp vấn đề đáng kể (chơi trực tiếp không phần mềm); `P07` đau đầu nhất là ổn định trật tự lớp; `P04` lo chi phí dùng AI; `P05` cảnh báo nhàm chán do spam quiz và cheating. |

- **Baseline bàn giao cho TV4 (`cost/personas.yaml` & `data/DATA_CARD.md`):**
  - **Tần suất tổ chức trò chơi / 30 ngày (tháng) (`n = 21` · nhạy `n = 20`):** `1–2 lần` (`33.3%` · `n=20: 35.0%`), `3–5 lần` (`28.6%` · `n=20: 30.0%`), `6–10 lần` (`19.0%` · `n=20: 20.0%`), `>10 lần` (`19.0%` · `n=20: 15.0%`) — gợi ý 3 persona khớp dữ liệu thật: **Ít (`1–2 lần/tháng`, 33.3% / 35.0%)**, **Vừa (`3–5 lần/tháng`, 28.6% / 30.0%)**, **Nhiều (`≥ 6 lần/tháng`, 38.1% / 35.0%)**.
  - **Thời gian chuẩn bị Baseline / trò chơi:** `10–<20 phút` (`38.1%`), `20–<30 phút` (`38.1%`), `30–<60 phút` (`14.3%`), `≥ 60 phút` (`9.5%`) — **trung vị khoảng: `20–<30 phút/trò chơi`** (`61.9%` tốn `≥ 20 phút`; `n=20: 65.0%`).
  - **Impact / tháng:** Chưa tính thành số tiết kiệm vì chưa có thời gian *With Agent* đo thực nghiệm (chờ T04 UAT).
