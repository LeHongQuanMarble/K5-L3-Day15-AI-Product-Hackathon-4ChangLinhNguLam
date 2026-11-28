---
name: token-saver
description: Quy tắc tiết kiệm token khi code trong repo này — đọc file có chọn lọc, giới hạn output lệnh, không lặp lại nội dung. BẮT BUỘC nạp đầu mỗi phiên làm việc.
---

# Token saver

Áp dụng suốt phiên. Mục tiêu: hoàn thành task với ít token nhất mà không giảm chất lượng.

## Đọc
- **Grep/Glob trước, Read sau.** Tìm đúng symbol hoặc đoạn cần sửa rồi Read với `offset`/`limit`.
  Không Read nguyên file > 200 dòng nếu chỉ cần một hàm.
- Docs: chỉ đọc các mục `§` mà task ghi. Dùng Grep tiêu đề `^## ` để nhảy tới đúng mục.
- **Không đọc lại** file vừa Write/Edit để "kiểm tra". Tool đã báo thành công là đủ.
- Không mở `tests/fixtures/*.html`, `*.json` lớn, `sessions/`, `output/`, lockfile, ảnh chụp
  trừ khi task bắt buộc. Muốn biết cấu trúc thì dùng Grep `data-testid` hoặc `head -c 500`.
- Không đọc `node_modules`, `.venv`, `__pycache__`, `.pytest_cache`.

## Chạy lệnh
- pytest luôn có `-q -x --tb=short`. Chỉ chạy file test của task. Chạy cả suite chỉ ở bước cuối.
- Output dài thì cắt: `| tail -n 40` (lỗi nằm ở cuối), hoặc `2>&1 | grep -E "FAILED|Error|assert" | head -n 30`.
- `ruff check . --fix --quiet` thay vì in mọi cảnh báo.
- `pip install -q`, `playwright install` chỉ chạy 1 lần ở T01.
- Không `cat` file HTML do LLM sinh ra. Muốn xem thì dùng `grep -n` theo testid.

## Sửa
- Dùng **Edit** cho thay đổi nhỏ. Write cả file chỉ khi tạo mới hoặc thay > 50% nội dung.
- Không tạo file tài liệu/ghi chú ngoài `PROGRESS.md` khi chưa được yêu cầu.
- Không thêm comment giải thích hiển nhiên. Docstring 1 dòng là đủ.

## Giao tiếp
- Không nhắc lại kế hoạch hay nội dung file trong câu trả lời. Báo cáo cuối task ≤ 5 dòng.
- Không dán code đã viết vào tin nhắn. Dùng link `path:line`.
- Không giải thích lựa chọn hiển nhiên. Chỉ nêu quyết định không hiển nhiên hoặc điểm lệch khỏi spec.

## Subagent
- Không tạo subagent cho việc vài lệnh Grep/Read làm được.
- Chỉ dùng subagent `Explore` khi phải quét > 15 file mà chỉ cần kết luận.
