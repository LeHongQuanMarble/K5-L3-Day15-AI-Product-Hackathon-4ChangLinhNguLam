# CLAUDE.md — Chatbot tạo game học tập

Dự án: chatbot web (FastAPI + JS thuần) giúp giáo viên tạo **game học tập HTML có chấm điểm**
theo luồng INPUT → N1 → N1b → N2 ⇄ Session Memory → N3 → N4 ⇄ FIX(≤2) → N5 → N6 → MAIN.

## Hai chế độ làm việc
- **Song song (khuyến nghị):** người dùng gọi `/orchestrate`. Phiên chính là **điều phối** (skill `orchestrate`),
  giao task cho subagent `task-coder` trong worktree riêng theo `docs/PARALLEL_PLAN.md`.
  Khi là `task-coder`: làm theo `.claude/agents/task-coder.md`, **không** sửa `TASKS.md`/`PROGRESS.md`
  (điều phối cập nhật), bỏ qua bước 2 và mục "Hoàn thành một task" bên dưới.
- **Tuần tự:** người dùng gọi `/next-task`, mỗi lần một task, theo các mục bên dưới.

## BẮT BUỘC đầu mỗi phiên
1. Nạp skill **`token-saver`** và **`fast-coding`** (nằm trong `.claude/skills/`) rồi làm theo suốt phiên.
2. Mở `TASKS.md`, chọn task `[ ]` đầu tiên (hoặc task `[~]` đang dở). Chỉ làm **một task**.
3. Chỉ đọc các mục docs mà task ghi ở dòng **Đọc**. Không đọc lại toàn bộ docs.
4. Khi sửa `contract.py`, `n3_generate.py`, `n4_test.py`, `fixer.py`, `reference_game.html` hoặc prompt `codegen`/`fix`: nạp thêm skill **`edu-game-contract`**.

## Nguồn sự thật (theo thứ tự ưu tiên)
`docs/SPEC.md` (hành vi) > `docs/GAME_CONTRACT.md` · `docs/QUESTION_SCHEMA.md` > `docs/ARCHITECTURE.md` > `TASKS.md`.
Nếu tài liệu mâu thuẫn hoặc thiếu: **dừng lại và hỏi người dùng**, không tự đoán. Ghi câu hỏi vào `PROGRESS.md`.

## Ràng buộc sản phẩm (không bao giờ vi phạm)
- Chỉ tạo **game học tập**. Yêu cầu khác thì từ chối ở INPUT.
- **Không có bộ câu hỏi hợp lệ thì không được vào N2.** Nguồn: `user` | `document` | `topic`.
- Bộ câu hỏi do **hệ thống** nhúng vào HTML (`inject_bank`), không để LLM tự viết.
- Mọi game có **chấm điểm** và **màn hình kết quả cuối game** (GAME_CONTRACT §3).
- FIX tối đa `MAX_FIX_ATTEMPTS` (=2) lần mỗi phiên bản. Chưa pass N4 thì **không được xuất**.
- Chữ hiển thị cho người dùng: tiếng Việt, chỉ nằm trong `app/chatbot/replies.py`.

## Khung code có sẵn
- Mọi hàm public đã được khai báo (tên, tham số, kiểu, docstring), thân hàm là `raise NotImplementedError`.
  Nhiệm vụ: **viết phần thân**. Docstring là đặc tả của hàm.
- **Không đổi** tên hàm, tham số, kiểu trả về, trường model, button id hay các `id`/`data-testid` trong `web/index.html`.
  Thấy cần đổi thì ghi vào `PROGRESS.md` mục "Đề xuất" và hỏi người dùng.
- Test của task đang bị skip: xoá dòng `pytestmark = ...skip...` rồi viết nội dung cho các test có sẵn.

## Quy tắc code
- Python 3.11+, type hints đầy đủ, `async` cho I/O. Node là hàm thuần, nhận dependency qua tham số.
- Không thêm thư viện ngoài stack (ARCHITECTURE §1) khi chưa hỏi.
- Test **không bao giờ** gọi LLM thật: dùng `FakeLLM` trong `tests/conftest.py`.
- Không đọc/in `.env`, không log API key.
- Không sửa file trong `docs/` trừ khi người dùng yêu cầu.

## Lệnh
```
pip install -e ".[dev]" && python -m playwright install chromium
ruff check . --fix && ruff format .
pytest -q -x -m "not browser"          # nhanh
pytest -q -x -m browser                # Playwright
pytest tests/unit/test_xxx.py -q -x    # chỉ test của task đang làm
uvicorn app.main:create_app --factory --reload
```

## Hoàn thành một task
1. Mọi lệnh ở dòng **Kiểm tra** pass, `ruff check .` sạch.
2. Đánh `[x]` trong `TASKS.md`, thêm 1 dòng vào `PROGRESS.md`: `T<nn> | <ngày> | <tóm tắt ≤ 15 từ> | <lưu ý nếu có>`.
3. `git commit -m "T<nn>: <tên task>"`. Không push nếu người dùng chưa yêu cầu.
4. Báo cáo ngắn (≤ 5 dòng) rồi dừng, chờ người dùng gọi task tiếp theo (`/next-task`).
