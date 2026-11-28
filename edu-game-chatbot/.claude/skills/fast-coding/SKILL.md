---
name: fast-coding
description: Quy trình code nhanh và ít lỗi cho repo này — test trước theo tiêu chí task, vòng lặp sửa ngắn, gộp tool call song song, quy tắc dừng khi bế tắc. BẮT BUỘC nạp đầu mỗi phiên làm việc.
---

# Fast coding

## Vòng lặp mỗi task (không bỏ bước)
1. **Hiểu (≤ 2 phút):** đọc task trong `TASKS.md` và các mục docs ở dòng **Đọc**. Liệt kê trong đầu:
   file cần tạo, hàm public và signature, các case test.
2. **Test trước:** viết test từ mục **Test** của task. Chạy để thấy test fail đúng lý do
   (ImportError/AssertionError, không phải lỗi cú pháp trong test).
3. **Code tối thiểu** để test pass. Không thêm tính năng ngoài task.
4. **Chạy hẹp:** `pytest <file_test> -q -x --tb=short`. Sửa tới khi xanh.
5. **Dọn:** `ruff check <files> --fix --quiet && ruff format <files>`.
6. **Kiểm tra cuối:** chạy đúng các lệnh ở dòng **Kiểm tra**, rồi `pytest -q -x -m "not browser"`
   để chắc không làm hỏng task trước.
7. Đánh dấu xong theo CLAUDE.md.

## Tốc độ
- **Gộp tool call độc lập vào một lượt:** ví dụ Read 3 file cùng lúc, hoặc Write file code và file test cùng lúc.
- Viết cả file một lần khi đã rõ signature, không viết từng hàm rồi chạy.
- Dùng lại helper sẵn có: `parse_json`, `extract_html`, `inject_bank`, `validate_bank`,
  `store.safe_path`, `replies.*`. Grep trước khi viết hàm mới.
- Fixture dùng chung đặt trong `tests/conftest.py`: `fake_llm`, `store`, `settings`,
  `sample_bank`, `reference_html`.
- Test async: `pytest-asyncio` với `asyncio_mode = "auto"` (đã cấu hình), không cần decorator.
- Test cần trình duyệt phải gắn `@pytest.mark.browser` để vòng lặp nhanh bỏ qua được.

## Tránh lỗi hay gặp
- `bool` là `int` trong Python: kiểm `isinstance(x, bool)` **trước**.
- Windows: luôn `encoding="utf-8"` khi đọc/ghi file; dùng `Path`, không nối chuỗi đường dẫn.
- Playwright sync API không được chạy trong event loop: bọc bằng `asyncio.to_thread`.
- Đăng ký `page.on(...)` **trước** `page.goto`. Luôn `dialog.dismiss()`.
- `asyncio.create_task`: giữ reference trong một `set`, `add_done_callback(set.discard)`.
- Pydantic v2: `model_dump(mode="json")` khi ghi JSON, `model_validate` khi đọc.
- Không hard-code chuỗi tiếng Việt ngoài `replies.py`; không hard-code model/timeout ngoài `config.py`.

## Quy tắc dừng
- **Cùng một lỗi sau 2 lần sửa:** dừng, đọc lại spec/contract liên quan và traceback đầy đủ (một lần),
  rồi đổi hướng. Không thử mò lần thứ 3 theo cùng cách.
- **Sau 3 hướng khác nhau vẫn fail:** ghi tình trạng vào `PROGRESS.md` (lỗi, đã thử gì) rồi hỏi người dùng.
- Spec mơ hồ: hỏi, không tự bịa hành vi.
- Không bao giờ sửa test cho "xanh" bằng cách nới điều kiện so với tiêu chí trong `TASKS.md`.
