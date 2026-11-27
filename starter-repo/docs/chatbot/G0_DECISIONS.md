# G0 — Bảng quyết định triển khai (bản đề xuất, chờ duyệt)

Thời điểm: 2026-11-27 (Asia/Bangkok). Người soạn: agent điều phối. Trạng thái: **REVIEW**. Chưa có dòng mã nào bị sửa.

## 0. Hiện trạng so với mốc khảo sát

- Git root: `K5-L3-Day15-AI-Product-Hackathon-4ChangLinhNguLam/`, nhánh `feature/chatbot`, HEAD = `faa44a8` (đúng mốc). Không có thay đổi tracked; chỉ `starter-repo/docs/chatbot/` chưa track. Không pull/fetch trong phiên này.
- `python -m unittest discover -s ailab -p "test_*.py"`: 27/27 OK (Python 3.13.7, chạy lại trong phiên này).
- Kết luận: mã **không đổi** so với lúc khảo sát; bộ tài liệu vẫn khớp. Các phát hiện mới bên dưới là từ đọc lại mã, không phải do mã đổi.

### Phát hiện mới có tác động

| ID | Phát hiện | Bằng chứng | Tác động |
|---|---|---|---|
| N1 | `_chat` tạo chat mới bằng `INSERT` rồi **gọi LLM khi giao dịch ghi SQLite còn mở** (sqlite3 tự mở transaction trước INSERT). Request ghi khác có thể chờ tới timeout 10 s rồi lỗi. | `ailab/server.py:453` → `:458` → commit ở `:470` | Vi phạm quy tắc "không giữ giao dịch khi chờ AI". Sửa trong I01. |
| N2 | `store.add_player`, `replace_player_html`, `update_meta` tự `commit()` bên trong. | `ailab/store.py:305`, `:319`, `:379` | Không gộp được Player + Exam + App vào một giao dịch nếu gọi thẳng. Cần tham số `commit=True` (mặc định giữ hành vi cũ). |
| N3 | Danh mục mặc định: Quiz ABCD (camera, cần **4 lớp action**, `kinds=[image,pose]`) và Vòng quay (danh sách, không model). Model có sẵn duy nhất là Bàn tay: 2 action, kind `hands`. | `store.init`, `llm.QUIZ_TEMPLATE`; DB local chỉ có 2 player + 1 model | **Nhánh reuse cho game câu hỏi không tạo được App** trên DB mặc định: Quiz không nhận `hands` và cần 4 lớp; `clean_app` bắt buộc model khi có `inputs` (O04). Cần quyết định sản phẩm (Q1). |
| N4 | `codebase/ai.py` đọc `.env` tại `starter-repo/.env`; trên máy này file `.env` nằm ở thư mục cha (git root). Không đọc nội dung. | `codebase/ai.py:27-30` | Server hiện chạy **chế độ giả** trừ khi biến môi trường được đặt. Muốn có bằng chứng AI thật (T40) phải xử lý (Q3). |
| N5 | `ailab/data/ailab.db` local là schema cũ (chưa có bảng `exams`, cột `exam_id`). `store.init` tự thêm khi chạy server. | đọc read-only `PRAGMA table_info` | Không mất dữ liệu; test luôn dùng DB tạm. |
| N6 | F01 xác nhận bằng đọc mã: PUT truyền `mapping` dạng dict vào SQL. | `ailab/server.py:421-422` (POST ở `:410` có `json.dumps`) | Patch 1 dòng, xem §7. |

## 1. Schema state và phản hồi

- Một module `ailab/chatbot/schemas.py` (C01) định nghĩa `TeacherRequirements`, `ConversationState`, `GameProposal`, `ValidationResult`, `ChatError` bằng dict + hàm kiểm (không thêm thư viện).
- `ConversationState = {schema: 1, version, status, requirements, assumptions[], missingFields[], proposal|null, confirmations{planVersion?}, validation|null, result|null, history: [lượt tóm tắt]}`.
- Phản hồi `POST /api/chat` **giữ nguyên** `chatId`, `reply.role/text/simulated/model`; `reply.error` vẫn là **chuỗi** (UI cũ không crash). Thêm trường mới: `status, stateVersion, requirements, missingFields, questions, proposal, validation, result, failure` (lỗi có cấu trúc `ChatError`).
- Proposal mới có `kind: "plan_v2"` và `proposalId`; proposal cũ (có `index`, `html`) giữ nguyên dạng và route cũ.

## 2. Lưu state, version, chống trùng (migration cộng thêm, không mất dữ liệu)

Ba bảng mới, tạo bằng `CREATE TABLE IF NOT EXISTS` trong `ailab/chatbot/repository.py: ensure_schema(c)`; `store.init` gọi thêm **một dòng** `ensure_schema(c)`:

```sql
chat_states(chat_id INTEGER PRIMARY KEY REFERENCES chats(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL, version INTEGER NOT NULL, state TEXT NOT NULL, updated REAL NOT NULL);
chat_requests(request_id TEXT NOT NULL, user_id INTEGER NOT NULL, chat_id INTEGER,
              action TEXT NOT NULL, response TEXT NOT NULL, created REAL NOT NULL,
              PRIMARY KEY(user_id, request_id));
chat_results(chat_id INTEGER NOT NULL, proposal_id TEXT NOT NULL, proposal_version INTEGER NOT NULL,
             app_id INTEGER NOT NULL, player_id INTEGER NOT NULL, exam_id INTEGER, model_id INTEGER,
             player_created INTEGER NOT NULL, created REAL NOT NULL, PRIMARY KEY(chat_id, proposal_id));
```

- Bảng `chats` không đổi. Chat cũ chưa có `chat_states` → state rỗng version 0, tạo khi có lượt mới.
- Ghi state theo optimistic version: `UPDATE chat_states SET ... , version=version+1 WHERE chat_id=? AND version=?`; `rowcount=0` → `stale_version` (409).
- `requestId` (tùy chọn, UUID do client tạo) → tra `chat_requests` trước khi xử lý; có rồi thì trả lại `response` đã lưu. Client cũ không gửi `requestId` vẫn chạy.
- Accept trùng/đồng thời bị chặn bởi `PRIMARY KEY(chat_id, proposal_id)` của `chat_results`, ghi trong cùng giao dịch với App.

## 3. Xác nhận tường minh và route

| Route | Dùng cho |
|---|---|
| `POST /api/chat` (giữ) | Tin nhắn; thêm `requestId?`, `expectedVersion?` |
| `POST /api/chats/<cid>/actions` (mới) | `{action: confirm_plan|accept_result|reject_result, proposalId, version, requestId}` |
| `GET /api/chats/<cid>/plans/<proposalId>/preview?version=N` (mới) | Xem thử bằng **bộ đề thật của proposal**, không dùng `SAMPLE_QUESTIONS` |
| `/api/chats/<cid>/proposals/<idx>/(try|accept|reject)` (giữ) | Chỉ proposal HTML cũ; hành vi không đổi, không tạo App |
| `GET /api/chats/<cid>` (giữ) | Thêm `state` (đã làm sạch, không HTML) |

Mỗi action: xác thực user sở hữu chat → so `version` với state hiện tại → **đọc lại quyền** Player/Model/Exam ngay lúc đó. LLM không bao giờ tự gọi các action này; câu "đồng ý" chỉ khiến bot hiện nút xác nhận.

## 4. Lưu nguyên tử

- Mọi lời gọi LLM chạy **ngoài** giao dịch. Trình tự: đọc state (không khóa) → gọi AI → `BEGIN IMMEDIATE` → so version → ghi → `COMMIT`.
- Sửa N1: chat mới được `INSERT` + commit trước khi gọi LLM (hoặc tạo sau khi LLM trả). Chọn: insert + commit trước, để lỗi AI vẫn giữ tin nhắn người dùng.
- `accept_result`: một giao dịch `BEGIN IMMEDIATE` gồm Player draft (chỉ generate_new), Exam mới (nếu có), App (`share=0`), `chat_results`, cập nhật state. Lỗi → `ROLLBACK`.
- Thay đổi store tối thiểu: thêm tham số `commit=True` cho `add_player` (mặc định giữ hành vi). Insert Exam/App viết trong repository, tái dùng `clean_exam`, `clean_app`.

## 5. Giới hạn

| Mục | Giá trị đề xuất |
|---|---|
| Tin nhắn | 3–2000 ký tự (giữ), tối đa 60 tin/chat (giữ) |
| LLM mỗi lượt hội thoại | ≤ 2 lời gọi (phân tích + 1 lần sửa JSON); sinh HTML ≤ 2 lượt (giữ) |
| Timeout provider | theo `codebase/ai.py` (120 s); không thêm retry mạng tự động ở W1–W2 |
| Context gửi LLM | state yêu cầu + 12 tin cuối + danh mục rút gọn (id, tên, manifest tóm tắt, model kind/lớp), không gửi HTML |
| Tài liệu (W4) | Dán chữ/TXT ≤ 50 000 ký tự trước. DOCX bằng `zipfile`+`xml` (thư viện chuẩn). PDF cần thư viện ngoài → xin duyệt ở W4; chưa có OCR thì báo rõ. Lưu trong DB theo user, xóa khi xóa chat. |

## 6. Bằng chứng runtime / chuột

- Unit + API: `unittest`, DB tạm (`AILAB_DB`), provider giả, server local tự tắt.
- Trình duyệt: ưu tiên công cụ sẵn có trong phiên (Claude in Chrome / built-in browser nếu bật được); nếu không, checklist thao tác tay để người dùng chạy, kết quả ghi vào `evidence/chatbot/`. Không cài framework trình duyệt lớn. Chưa chạy thì ghi `not_checked`.
- Mỗi bằng chứng ghi `proposalId`, `version`, hash SHA-256 HTML, `examId`/hash nội dung đề, loại model (giả/thật).

## 7. Phạm vi file — QUY TẮC "CHỈ THÊM, KHÔNG SỬA" (người dùng chốt 2026-11-27)

Không sửa bất kỳ file hiện có nào (`server.py`, `store.py`, `llm.py`, `contract.py`, `web/*`, `codebase/*`, test cũ). Mọi thay đổi nằm trong file **mới**:

| File mới | Vai trò |
|---|---|
| `ailab/chatbot/*.py` | Lõi chatbot (schemas, conversation, workflow, catalog, exams, production, validation, documents, repository) |
| `ailab/chatbot_server.py` | Điểm chạy mới: lớp con của `server.H`. Thêm/ghi đè route chat mới (`/api/chat`, `/actions`, `/plans/.../preview`), gọi `ensure_schema` + seed sau `store.init()`, gắn `<script src="/chatbot.js">` vào `index.html` **trong bộ nhớ** khi phục vụ (file gốc không đổi). Route khác chuyển nguyên cho `server.H`. |
| `ailab/web/chatbot.js` | Giao diện tab Trợ lý game mới: khi hash là `#/chat`, thay nội dung `#main` do `app.js` vẽ; dùng lại class CSS sẵn có |
| `ailab/test_chatbot_*.py` | Test mới |

Hệ quả cần biết:

- Chạy bản chatbot mới bằng `python ailab/chatbot_server.py`. `python ailab/server.py` vẫn chạy y như cũ (chatbot cũ). Nhập hai điểm chạy làm một là việc của nhóm sau này (sửa 1–2 dòng), ngoài phạm vi hiện tại.
- **F01**: không sửa `server.py`. `chatbot_server.py` ghi đè riêng nhánh `PUT /api/apps/<id>` với `json.dumps(mapping)`; lỗi gốc trong `server.py` vẫn còn và được ghi ở AI_PROGRESS cho chủ backend.
- **Lưu nguyên tử (§4)**: repository tự viết INSERT Player/Exam/App, tái dùng `contract.parse/scan`, `store.clean_exam/clean_app` (các hàm này không commit). Không gọi `store.add_player` trong giao dịch.
- **N1** (khóa DB trong `_chat` cũ): chỉ tránh được trong luồng mới; `_chat` cũ giữ nguyên.
- **Q1**: Player mẫu "Quiz bấm chuột" được seed bởi `chatbot.repository` (khi chạy `chatbot_server.py`), không qua `store.init`.
- Rủi ro: `chatbot.js` phụ thuộc cấu trúc DOM `#main` của `app.js`; nếu đồng đội đổi `app.js` cần kiểm lại. Có test trình duyệt ở W1.

## 8. Câu hỏi cần người dùng quyết định

- **Q1 (N3) — đã chốt theo §7:** Nhánh reuse cho game câu hỏi với danh mục mặc định. Đề xuất: thêm **một Player mẫu "Quiz bấm chuột"** (manifest `questions:"exam"`, không `inputs`, hợp lệ với contract hiện tại) qua seed trong `store.init`. Không đổi `clean_app`/contract. Quiz ABCD camera vẫn dùng được khi giáo viên có model Teachable Machine ≥ 4 lớp.
- **Q2:** Cho phép điều phối dùng subagent (Agent tool có sẵn trong phiên) làm coder cho C01/C03, hay làm tuần tự trong một phiên.
- **Q3 (N4):** Để có bằng chứng AI thật: người dùng tự đặt biến môi trường / copy `.env` vào `starter-repo/`, hay tạm thời chỉ dùng chế độ giả đến W5.
