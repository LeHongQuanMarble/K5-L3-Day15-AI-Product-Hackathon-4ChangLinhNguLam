# Chatbot tạo game học tập

Repo này được triển khai bởi agent code (Claude Code) theo kế hoạch trong `TASKS.md`.

## Bắt đầu với Claude Code

1. Copy toàn bộ bộ file này vào thư mục gốc của repo, rồi `git init` (nếu chưa có).
2. `cp .env.example .env` và điền `OPENAI_API_KEY`. Agent bị chặn đọc `.env`.
3. Mở Claude Code tại thư mục repo. Các skill trong `.claude/skills/` được nạp tự động:
   - `token-saver`: tiết kiệm token (bắt buộc)
   - `fast-coding`: quy trình code nhanh, ít lỗi (bắt buộc)
   - `edu-game-contract`: checklist khi động vào phần sinh/kiểm game
   - `next-task`: lệnh `/next-task` để làm task kế tiếp
   - `orchestrate`: lệnh `/orchestrate` để điều phối nhiều agent coder chạy song song
   - Subagent `.claude/agents/task-coder.md`: agent coder dùng trong chế độ song song
4. Chọn một trong hai cách chạy:
   - **Song song (nhanh):** gõ `/orchestrate`. Phiên chính thành agent điều phối, giao các task
     độc lập cho nhiều subagent `task-coder` chạy cùng lúc trong worktree riêng, merge qua cổng kiểm tra.
     Xem các đợt trong `docs/PARALLEL_PLAN.md`. Ví dụ `/orchestrate W1` để chỉ chạy đợt 1,
     hoặc `/orchestrate MAX_PARALLEL=6` để chạy nhiều agent hơn.
   - **Tuần tự:** gõ `/next-task` cho mỗi task (T01 → T23).

## Bộ file

| File | Vai trò |
|---|---|
| `CLAUDE.md` | Quy tắc bắt buộc, được nạp vào mọi phiên |
| `TASKS.md` | 23 task chi tiết: file, test, lệnh kiểm tra, bẫy thường gặp |
| `docs/SPEC.md` | Hành vi chatbot, luồng, state machine, kịch bản hội thoại |
| `docs/ARCHITECTURE.md` | Stack, cấu trúc thư mục, model dữ liệu, API |
| `docs/GAME_CONTRACT.md` | Contract game HTML + kịch bản kiểm thử Playwright |
| `docs/QUESTION_SCHEMA.md` | Định dạng và quy tắc bộ câu hỏi |
| `.claude/settings.json` | Cho phép sẵn pytest/ruff/git, chặn đọc `.env` và `git push` |
| `pyproject.toml` | Dependency, cấu hình pytest/ruff |

## Chạy (sau khi hoàn thành các task)

```
pip install -e ".[dev]"
python -m playwright install chromium
uvicorn app.main:create_app --factory --reload
```
Mở http://127.0.0.1:8000
