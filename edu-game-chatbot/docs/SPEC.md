# SPEC — Chatbot tạo game học tập

> Tài liệu nguồn duy nhất về **hành vi sản phẩm**. Kiến trúc: `docs/ARCHITECTURE.md`.
> Contract game: `docs/GAME_CONTRACT.md`. Bộ câu hỏi: `docs/QUESTION_SCHEMA.md`.

## 1. Mục tiêu

Giáo viên trò chuyện với chatbot để tạo một **game học tập** dạng file HTML đơn. Game phải:
- dùng một **bộ câu hỏi** bắt buộc (giáo viên tự soạn, AI tạo từ tài liệu, hoặc AI tạo theo chủ đề);
- **chấm điểm** và có **màn hình kết quả cuối game**;
- qua kiểm thử tự động rồi mới đưa giáo viên chơi thử;
- được xuất ra thư mục và bàn giao cho hệ thống MAIN khi giáo viên hài lòng.

## 2. Luồng (theo sơ đồ gốc)

```mermaid
flowchart TD
  IN[INPUT: Tài liệu + Yêu cầu] --> G0{Game học tập?}
  G0 -- Không --> REJ[Từ chối, giải thích]
  G0 -- Có --> SRC{Nguồn câu hỏi?}
  SRC -- user --> QU[Nạp file câu hỏi]
  SRC -- document --> N1[N1. Đọc tài liệu] --> QG[AI tạo câu hỏi]
  SRC -- topic --> QG
  QU --> QA{Giáo viên duyệt bộ câu hỏi?}
  QG --> QA
  QA -- Tạo lại --> QG
  QA -- Đồng ý --> N2[N2. Phân tích & thiết kế game — GPT-6 Sol]
  MEM[(Session Memory)] <--> N2
  N2 --> N3[N3. Sinh HTML có đồ hoạ — GPT-6 Sol]
  N3 --> N4[N4. Kiểm tra tự động: Contract + Playwright]
  N4 --> ERR{Có lỗi?}
  ERR -- Có, còn lượt --> FIX[AI sửa lỗi, tối đa 2 lần] --> N4
  ERR -- Không --> N5[N5. Giáo viên chơi thử]
  ERR -- Có, hết lượt --> N5W[N5. Chơi thử kèm cảnh báo: chỉ cho Sửa/Huỷ]
  N5 --> OK{Hài lòng?}
  N5W --> CHAT
  OK -- Chưa --> CHAT[Chat yêu cầu chỉnh sửa] --> N2
  OK -- Có --> N6[N6. Xuất file vào Folder] --> MAIN[MAIN tiếp nhận]
```

Bổ sung so với sơ đồ gốc (bắt buộc, đã chốt):
1. **Cổng "Game học tập?"** ở INPUT: yêu cầu không phải game học tập thì từ chối. Không chạy N1–N6.
2. **Nguồn câu hỏi bắt buộc.** Thiếu nguồn thì chatbot phải hỏi, không được đoán.
3. **Duyệt bộ câu hỏi** trước N2 (với nguồn `user` thì chỉ hiển thị, không bắt duyệt).
4. **Hết 2 lần sửa vẫn lỗi:** vẫn sang N5, nhưng **không cho xuất**. Chỉ có nút "Chỉnh sửa" và "Huỷ".
5. Chỉnh sửa ở N5 có thể đụng tới câu hỏi. Khi đó N2 trả `question_edit` và hệ thống sửa bộ câu hỏi trước khi sang N3.
6. Giới hạn **10 vòng chỉnh sửa** mỗi phiên. Quá giới hạn thì phiên chuyển sang `failed`.

## 3. Trạng thái hội thoại (state machine)

| State | Chatbot đang chờ | Thoát sang |
|---|---|---|
| `AWAIT_REQUEST` | Mô tả game | `AWAIT_SOURCE` / `REJECTED` |
| `AWAIT_SOURCE` | Chọn nguồn câu hỏi (3 nút) | `AWAIT_SOURCE_INPUT` |
| `AWAIT_SOURCE_INPUT` | Upload file câu hỏi / upload tài liệu / gõ chủ đề | `BUILDING_QUESTIONS` |
| `BUILDING_QUESTIONS` | (đang chạy N1/N1b) | `AWAIT_QUESTION_APPROVAL` / `READY_TO_DESIGN` / `AWAIT_SOURCE_INPUT` (nếu file lỗi) |
| `AWAIT_QUESTION_APPROVAL` | "Đồng ý" / "Tạo lại" + góp ý | `READY_TO_DESIGN` / `BUILDING_QUESTIONS` |
| `PIPELINE_RUNNING` | (đang chạy N2→N3→N4↔FIX) | `AWAIT_REVIEW` |
| `AWAIT_REVIEW` | "Hài lòng" / "Chỉnh sửa" / "Huỷ" | `AWAIT_REVISION_TEXT` / `EXPORTING` / `CANCELLED` |
| `AWAIT_REVISION_TEXT` | Nội dung chỉnh sửa | `PIPELINE_RUNNING` |
| `EXPORTING` | (N6 + bàn giao MAIN) | `DONE` |
| `DONE` / `REJECTED` / `CANCELLED` / `FAILED` | Trạng thái kết thúc | — |

Quy tắc chung:
- Đang ở state "đang chạy" mà người dùng nhắn: trả lời "Đang xử lý bước X, vui lòng đợi". Không chạy song song.
- Người dùng gõ chữ khi đang có nút bấm: dùng LLM phân loại ý định thành một trong các nút. Không chắc thì hỏi lại.
- Mọi lỗi ngoài dự kiến: báo lỗi thân thiện, lưu vào memory. Phiên giữ nguyên state để thử lại (nút "Thử lại").

## 4. Kịch bản hội thoại mẫu (chuẩn để viết test e2e)

```
BOT : Xin chào! Thầy/cô muốn tạo game học tập về nội dung gì?
GV  : Tạo game ôn tập phân số cho lớp 4
BOT : Game học tập bắt buộc có bộ câu hỏi. Thầy/cô muốn lấy câu hỏi từ đâu?
      [Tôi có sẵn bộ câu hỏi] [Tạo từ tài liệu của tôi] [Tạo theo chủ đề]
GV  : (bấm) Tạo theo chủ đề
BOT : Thầy/cô nhập chủ đề và số câu (mặc định 10):
GV  : Phân số lớp 4, 8 câu
BOT : (tiến độ) Đang tạo bộ câu hỏi…
BOT : Bộ câu hỏi: 8 câu, tổng 80 điểm. [xem trước 5 câu] [Đồng ý] [Tạo lại]
GV  : Đồng ý
BOT : (tiến độ) Thiết kế game… → Sinh HTML… → Kiểm thử… (sửa lỗi 1/2)… → Đạt
BOT : Mời thầy/cô chơi thử: [iframe game] [Hài lòng — xuất file] [Chỉnh sửa] [Huỷ]
GV  : Chỉnh sửa → "Đổi màu nền sang xanh dương, thêm 2 câu về so sánh phân số"
BOT : (chạy lại N2 → sửa câu hỏi → N3 → N4) … Mời chơi thử phiên bản v2
GV  : Hài lòng — xuất file
BOT : Đã xuất game "…" (v2). MAIN đã tiếp nhận. [Tải về .zip]
```

Câu từ chối mẫu: *"Mình chỉ hỗ trợ tạo game học tập. Yêu cầu '…' không có mục tiêu học tập vì …
Thầy/cô có thể thử: 'Game ôn từ vựng tiếng Anh chủ đề động vật lớp 3'."*

## 5. Ràng buộc phi chức năng

- Tất cả chữ hiển thị cho người dùng bằng **tiếng Việt**.
- Model mặc định của N2/N3: `gpt-6-sol`. Cấu hình qua `.env`, không hard-code ở chỗ khác.
- Một bước LLM bị timeout (120 s) hoặc lỗi mạng thì retry tối đa 2 lần với backoff (2 s, 5 s).
- Tài liệu: `.pdf .docx .txt .md`, tối đa 10 MB/file, 5 file/phiên. Cắt còn `MAX_DOC_CHARS` ký tự.
- Bộ câu hỏi: 3–50 câu.
- Không log API key và nội dung `.env`.
- Mọi đường dẫn file từ người dùng phải nằm trong thư mục phiên (chống path traversal).
