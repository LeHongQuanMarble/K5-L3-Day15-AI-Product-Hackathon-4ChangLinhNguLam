# I01 — Tích hợp hội thoại vào tab Trợ lý game (chốt trước khi giao coder)

Nền: commit `4430c49` (C01 + C02 DONE). Quy tắc G0 §7: chỉ thêm file mới, không sửa file gốc của `faa44a8`.
Không tạo Player/Exam/App trong I01. Không sinh HTML.

## 1. File và chủ sở hữu

| File | Coder | Ghi chú |
|---|---|---|
| `ailab/chatbot_server.py` (mới) | Backend | Lớp con `server.H`, điểm chạy mới |
| `ailab/chatbot/repository.py` (mới) | Backend | DDL, đọc/ghi state, chống trùng, quyền |
| `ailab/chatbot/workflow.py` (mở lại C02, chỉ THÊM) | Backend | Thêm `cancel_plan(state, proposalId, version)` dùng chung logic nhánh hủy hiện có; không đổi hành vi cũ |
| `ailab/chatbot/schemas.py` (mở lại C01, chỉ THÊM) | Backend | Thêm `"cancel_plan"` vào `ACTIONS`; không đổi hành vi cũ |
| `ailab/web/chatbot.js` (mới) | Frontend | Giao diện tab mới |
| `ailab/test_chatbot_api.py` (mới) | Kiểm thử | Sau khi backend + frontend bàn giao |

Lý do mở lại workflow/schemas: nút "Hủy phương án" cần thao tác tường minh, không dựa vào việc AI hiểu chữ "hủy". Quy tắc hủy phải nằm ở một chỗ (workflow), không chép sang repository.

## 2. Chạy

```
python ailab/chatbot_server.py          # AILAB_HOST, AILAB_PORT (mặc định 8800), AILAB_DB như server.py
```

`main()`: `store.init(AILAB_ADMIN_PASSWORD)` → `repository.ensure_schema(c)` → in địa chỉ + chế độ model (giả/thật, không in khóa) → `ThreadingHTTPServer((host, port), ChatbotH)`. `python ailab/server.py` vẫn chạy như cũ.

## 3. Lưu trữ (bảng mới, `CREATE TABLE IF NOT EXISTS`, không đụng bảng cũ)

```sql
chat_states(chat_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, version INTEGER NOT NULL,
            state TEXT NOT NULL, updated REAL NOT NULL);
chat_requests(user_id INTEGER NOT NULL, request_id TEXT NOT NULL, chat_id INTEGER, action TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('pending','done')), response TEXT, created REAL NOT NULL,
              PRIMARY KEY(user_id, request_id));
```

(`chat_results` để W2.) Bảng `chats` giữ nguyên: tin nhắn mới vẫn nối vào `chats.messages`.

## 4. Repository (`ailab/chatbot/repository.py`) — hàm nhận kết nối `c` từ handler, không giữ kết nối toàn cục

| Hàm | Vào → Ra |
|---|---|
| `ensure_schema(c)` | tạo 2 bảng trên, commit |
| `get_chat(c, chat_id, user)` | row `chats` của đúng user, không thì `Err(404,"not_found")` (không phân biệt "không có" với "của người khác") |
| `create_chat(c, user, title)` | insert + commit NGAY → chat_id (trước khi gọi AI) |
| `load_state(c, chat_id, user)` | `(state, version)`; chưa có → `schemas.new_state()`, 0 |
| `begin_request(c, user, request_id, chat_id, action)` | `None` nếu mới (ghi `pending`, commit); dict response đã lưu nếu `done`; `Err(409,"duplicate_pending")` nếu đang xử lý. `request_id=None` → bỏ qua |
| `finish_request(c, user, request_id, response)` / `drop_request(...)` | ghi `done` + response trong cùng giao dịch lưu; lỗi bất ngờ → xoá `pending` để thử lại được |
| `save_turn(c, chat_id, user, old_version, new_state, new_messages, request_id, response)` | **một giao dịch** `BEGIN IMMEDIATE`: đọc lại version → khác `old_version` thì `ROLLBACK` + `stale_version`; khớp thì nối tin nhắn vào `chats.messages`, ghi state (`INSERT` khi version 0, `UPDATE ... WHERE chat_id=? AND version=?`), `finish_request`, `COMMIT` |
| `catalog_for(c, user)` | `{"players":[{"id","name","manifest"}]}` chỉ Player `store.player_usable` (không HTML) |

Không giữ giao dịch khi gọi AI: trước lời gọi `workflow.*`, `c.in_transaction` phải là False.

## 5. Route (ChatbotH)

Mọi route chat cần đăng nhập (base `_api` đã chặn 401). Lỗi theo dạng base `{"error": code, "message": ...}`; lỗi của chatbot thêm `"failure": ChatError` (đã qua `schemas.to_public_failure`).

| Route | Xử lý |
|---|---|
| `GET /` và `/index.html` | đọc `web/index.html`, chèn `<script src="/chatbot.js"></script>` ngay trước `</body>` **trong bộ nhớ**; còn lại giao base `_static` (nên `/chatbot.js` được phục vụ như file tĩnh) |
| `POST /api/chat` | body `{chatId?, text, requestId?, expectedVersion?}` → `schemas.validate_request` (lỗi → 400 `invalid_input`). Có `chatId` → `get_chat`; không → `create_chat(title=text[:60])`. ≥ 60 tin → 409 `chat_full` (như cũ). `begin_request`. Đọc state, gọi `workflow.process_turn(request, state, context)` với `context={call_model, history, catalog}`; `call_model = ai.call_model` nếu `llm._real_model()` khác None, ngược lại None (chế độ giả). Rồi `save_turn` với tin user `{role:"user", text}` + tin bot `{role:"bot", text, simulated, model, kind:"chat_v2", status, stateVersion, error?}`. Trả 200 `{chatId, reply: schemas.to_public_reply(...)}`. |
| ↳ lỗi AI (`meta.failure` model_unavailable / invalid_model_output) | state KHÔNG đổi nhưng vẫn lưu tin user + tin bot có `error` (không mất lịch sử); trả 200, `reply.failure` + `reply.error` |
| ↳ `stale_version` (từ workflow hoặc lúc lưu) | KHÔNG lưu gì; 409 `{error:"stale_version", message, failure, stateVersion}` |
| `GET /api/chats` | giao base |
| `GET /api/chats/<id>` | base (messages, proposal cũ đã bỏ html) + thêm `"state"`: `schemas.to_public_reply(state, "", False, "")` bỏ `role/text/simulated/model` |
| `POST /api/chats/<id>/actions` | body `{action, proposalId, version, requestId?}`; `action ∈ {confirm_plan, cancel_plan}` (khác → 400). `get_chat` → `begin_request` → `workflow.confirm_plan` / `cancel_plan` → lỗi `stale_version`/`invalid_input` → 409/400 không lưu; thành công → `save_turn` (tin bot `kind:"action_v2"` với câu ngắn: "Đã xác nhận phương án phiên bản N." / "Đã hủy phương án phiên bản N.") → 200 `{chatId, reply}`. Không tạo Player/Exam/App. |
| `/api/chats/<id>/proposals/<idx>/(try|accept|reject)` | giao base nguyên vẹn (proposal HTML cũ) |
| Mọi route khác | giao base |

`cancel_plan(state, proposal_id, version)` (workflow): sai id → `invalid_input`; đã hủy hoặc sai version → `stale_version`; đúng → như nhánh `reject_intent` hiện có (`proposal.status="cancelled"`, `confirmations={}`, `status="needs_revision"`, version state +1).

## 6. Giao diện (`ailab/web/chatbot.js`)

- Không sửa `app.js`. Chạy sau `app.js`; quan sát `#app` (MutationObserver) và `hashchange`: khi hash là `#/chat` hoặc `#/chat/<id>` và `#main` đã có khung chat cũ của `app.js` (phần tử `.chat` chưa được đánh dấu), thay nội dung `#main > .ail-page` bằng giao diện mới (đánh dấu `data-chatbot-v2`). Hoạt động khi: đăng nhập rồi bấm tab, đổi tab qua lại, tải thẳng `#/chat`, tải lại `#/chat/<id>`.
- Tự có helper `h()`/`api()` riêng (không truy cập nội bộ `app.js`); dùng lại class CSS sẵn có (`ail-btn pri sm bad`, `ail-chip ok warn bad`, `chat`, `list`, `msgs`, `m user|bot`, `meta`, `err`, `note`, `bar`, `tag`).
- Cuộc trò chuyện đang mở ghi vào hash `#/chat/<id>` → tải lại mở đúng chat, gọi `GET /api/chats/<id>` để vẽ tin nhắn + `state`.
- Gửi: `POST /api/chat` kèm `requestId` mới mỗi lần bấm (giữ nguyên khi tự thử lại cùng một tin) và `expectedVersion = state.stateVersion` hiện có. Chặn bấm đúp khi đang chờ.
- Hiển thị theo `state` mới nhất:
  - `clarifying`: danh sách `questions[].text`.
  - Có `proposal`: thẻ phương án — phiên bản, `reason`, `assumptions`, `changes`, `warnings` (label + reason), cách điều khiển (chuột luôn bật; `interactionModel.kind` nếu có), chip trạng thái (`awaiting_confirmation` / `confirmed` / `cancelled`).
  - Nút "Xác nhận phương án (phiên bản N)" và "Hủy phương án" chỉ khi `proposal.status == "awaiting_confirmation"`; gọi `/actions` với `proposalId` + `version` đang hiển thị. Đã xác nhận → ghi chú "Bước chuẩn bị game sẽ có ở đợt sau" (không hứa tạo App).
  - Lỗi: `reply.error` / `failure.message`; 409 `stale_version` → báo "đã có bản mới hơn" và tải lại chat.
  - Nhãn chế độ giả khi `simulated` (model `fake-rules`): "Chế độ giả — không phải AI thật".
- Tin nhắn cũ có `proposal` HTML (chat cũ): thẻ tối giản (tên, trạng thái, nút "Thêm vào Trình chơi"/"Không dùng" gọi route cũ khi còn `pending`). Xem thử proposal cũ: không làm ở I01 (ghi hạn chế).

## 7. Kiểm thử (`ailab/test_chatbot_api.py`)

Server thật `ChatbotH` trên cổng 0, DB tạm (`AILAB_DB`), `MODEL_PROVIDER=fake` đặt trước khi import, đóng server sau test. Không chạm `ailab/data/ailab.db`.

| ID | Tình huống | Kỳ vọng | Map |
|---|---|---|---|
| I01-01 | `GET /` | có `<script src="/chatbot.js">`; `GET /chatbot.js` 200 | — |
| I01-02 | Chưa đăng nhập gọi `/api/chat` | 401 | — |
| I01-03 | "Tạo game ôn toán" → "lớp 2" → "phép cộng có nhớ, 10 câu" | clarifying → clarifying (chỉ topic) → awaiting_confirmation; stateVersion 1,2,3 | T01–T03 |
| I01-04 | `GET /api/chats/<id>` sau đó (mô phỏng tải lại) | messages đủ 6, `state` đúng status/version/proposal | T04 |
| I01-05 | User B đọc/ghi/action chat của A | 404, không lộ nội dung | T07 |
| I01-06 | Gửi lại cùng `requestId` | trả đúng response cũ, không thêm tin nhắn, version không tăng | T18 |
| I01-07 | `expectedVersion` cũ | 409 `stale_version`, không lưu | T20 |
| I01-08 | Hai request đồng thời cùng `expectedVersion` (2 thread) | đúng 1 thành công, 1 bị 409; messages không bị ghi đè | T19 |
| I01-09 | confirm đúng bản / bản cũ / sai id | 200 / 409 / 400 | T20 |
| I01-10 | cancel → confirm bản đã hủy | 409; state `needs_revision` | — |
| I01-11 | Sửa yêu cầu sau confirm → confirm bản cũ | 409 | T20 |
| I01-12 | Chat cũ (chèn trực tiếp row có proposal HTML kiểu cũ) | GET không có `html`; route `/proposals/<idx>/reject` cũ vẫn chạy; gửi tin mới vào chat cũ được (state v0 → v1) | T04 |
| I01-13 | Lỗi AI (giả lập `call_model` ném lỗi) | 200, `reply.failure.code=model_unavailable`, tin nhắn vẫn lưu, state không đổi | T37 |
| I01-14 | Không có HTML/khóa trong mọi phản hồi chat | không chứa `<script`, `<html`, `srcdoc` | — |
| I01-15 | Không tạo Player/Exam/App | số dòng `players/exams/apps` không đổi sau toàn luồng | T17 |
| I01-16 | Route cũ khác vẫn chạy | `/api/me`, `/api/players`, `/api/exams` 200 | — |
| I01-17 | Bộ test cũ | `python -m unittest discover -s ailab -p "test_*.py"` OK | — |

**Trình duyệt:** điều phối chạy thử thật nếu phiên có công cụ trình duyệt; không có thì ghi **chưa kiểm** và đưa checklist thao tác tay: đăng nhập → tab Trợ lý game → 3 lượt hỏi → phương án → tải lại → xác nhận → hủy/sửa → đổi tab → tải thẳng `#/chat`.

## 8. Ngoài phạm vi I01

Tạo Player/Exam/App, xem thử phương án mới, F01 (PUT App), O16 (nhắc "đổi sang…"), tài liệu đính kèm, AI thật.
