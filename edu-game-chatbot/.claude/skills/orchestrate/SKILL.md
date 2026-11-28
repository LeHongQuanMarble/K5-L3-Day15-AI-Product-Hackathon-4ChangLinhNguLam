---
name: orchestrate
description: Agent điều phối — đọc kế hoạch song song, giao các task độc lập cho nhiều subagent task-coder chạy cùng lúc trong worktree riêng, merge qua cổng kiểm tra, cập nhật tiến độ. Người dùng gọi bằng /orchestrate (tuỳ chọn kèm số đợt, ví dụ /orchestrate W1, hoặc MAX_PARALLEL=6).
disable-model-invocation: true
---

# /orchestrate — Điều phối agent coder chạy song song

Bạn là **agent điều phối**, **không trực tiếp viết code tính năng** (trừ T01).
Nhiệm vụ của bạn: hoàn thành `TASKS.md` nhanh nhất bằng cách chạy song song các task độc lập,
đồng thời giữ nhánh tích hợp luôn xanh.

Nạp skill `token-saver` trước khi bắt đầu. Tài liệu bạn cần: `docs/PARALLEL_PLAN.md` (đọc toàn bộ),
`TASKS.md` (chỉ grep tiêu đề và trạng thái, đọc nội dung từng task khi soạn brief).

## Tham số (đọc từ `$ARGUMENTS`, không có thì dùng mặc định)
- `MAX_PARALLEL` = 4: số subagent chạy cùng lúc.
- Đợt: mặc định chạy từ đợt chưa xong đầu tiên đến hết. `W1` nghĩa là chỉ chạy đợt 1 rồi dừng báo cáo.

## Bước 0 — Chuẩn bị (tuần tự, chỉ chạy một lần)
1. `git status --short` phải sạch. Nếu chưa có repo: `git init`, commit toàn bộ khung (`chore: skeleton`).
2. Tạo/chuyển sang nhánh tích hợp `integration` (chưa có thì tạo từ nhánh hiện tại).
3. Nếu T01 chưa `[x]`: tự làm T01 theo `TASKS.md`, đánh `[x]`, commit.
4. Kiểm tra môi trường: `python -c "import app,sys;print(app.__file__)"` phải nằm trong repo;
   `pytest -q` chạy được (test skipped là bình thường).
5. **Kiểm chứng đồ thị phụ thuộc:** grep import `^from app\.` trong `app/`. Nếu có phụ thuộc mới mà
   PARALLEL_PLAN §1 chưa ghi, cập nhật bảng trong đầu và báo người dùng ở báo cáo cuối.
   **Không** tự sửa docs.

## Bước 1 — Lập lịch
- Task **sẵn sàng** khi: đang `[ ]`, mọi phụ thuộc (PARALLEL_PLAN §1) đã `[x]` **và đã merge** vào `integration`.
- Hàng đợi: lấy các task sẵn sàng, sắp theo thứ tự ưu tiên trong PARALLEL_PLAN §2.
- Giao tối đa `MAX_PARALLEL` task cùng lúc. **Mọi lời gọi Agent của cùng một lượt phải nằm trong
  MỘT message** để chúng chạy song song.
- Khi một agent xong và đã merge: tính lại hàng đợi, giao tiếp ngay để luôn đủ `MAX_PARALLEL` agent đang chạy.
  Không chờ cả đợt xong nếu task của đợt sau đã đủ phụ thuộc.
- T18 (đường găng, phức tạp nhất): giao cho agent chạy một mình, không chạy song song với task khác của cùng file.

## Bước 2 — Giao việc
Gọi Agent với `subagent_type: "task-coder"`, `isolation: "worktree"`, `description: "T<nn> <tên ngắn>"`.
Trước mỗi lượt giao, đảm bảo `integration` đã commit, vì worktree được cắt từ HEAD hiện tại.

Prompt cho mỗi agent theo **đúng mẫu sau**, điền đủ, không bỏ dòng nào:

```
TASK: T<nn> — <tên task>
NHÁNH: tạo nhánh `task/T<nn>` trong worktree của bạn và commit vào đó.
NỘI DUNG TASK (nguyên văn từ TASKS.md):
<dán nguyên khối task T<nn>, từ tiêu đề tới trước task kế tiếp>

FILE ĐƯỢC SỬA (duy nhất): <danh sách từ PARALLEL_PLAN §3>
ĐÃ CÓ SẴN (được gọi, KHÔNG sửa): <các hàm/fixture của task phụ thuộc đã merge, ví dụ:
  conftest: settings, store, fake_llm, sample_bank, reference_html; app.domain.contract.inject_bank ...>
CHƯA CÓ (đừng gọi, hoặc tự stub trong test của bạn): <các hàm còn NotImplementedError mà task này có thể đụng>
KIỂM TRA BẮT BUỘC: <các lệnh ở dòng Kiểm tra của task> + `ruff check <file của bạn>`
BÁO CÁO theo định dạng trong agent task-coder.
```

## Bước 3 — Nhận kết quả và merge (tuần tự, từng nhánh một)
Với mỗi báo cáo trả về:
1. `STATUS` khác `DONE`: xem bước 4.
2. `git diff --name-only integration...task/T<nn>`: có file ngoài danh sách sở hữu thì **từ chối**,
   gửi `SendMessage` cho chính agent đó, yêu cầu hoàn tác các file đó.
3. `git merge --no-ff task/T<nn> -m "merge T<nn>: <tên>"`.
4. Chạy **cổng kiểm tra** (PARALLEL_PLAN §4). Nếu fail:
   `git merge --abort` (nếu đang xung đột), hoặc `git reset --hard HEAD~1` (chỉ áp dụng cho merge commit **vừa tạo**).
   Gửi lỗi (đã cắt gọn ≤ 40 dòng) cho đúng agent qua `SendMessage` để sửa trên nhánh của nó, rồi merge lại.
5. Pass: đánh `[x]` cho task trong `TASKS.md`, thêm dòng vào `PROGRESS.md`, commit `chore: T<nn> done`.
6. Ghi `BLOCKERS` và `PROPOSALS` của agent vào `PROGRESS.md` (mục "Câu hỏi" và "Đề xuất").

## Bước 4 — Xử lý thất bại
- Agent báo `BLOCKED` vì lỗi trong file của task khác: tạo task sửa nhỏ, giao cho **agent đã làm task đó**
  (`SendMessage`). Agent đó đã kết thúc thì giao agent mới kèm mô tả lỗi.
- Một task fail cổng kiểm tra **2 lần**: đánh `[~]`, ghi lý do vào `PROGRESS.md`, bỏ qua, tiếp tục các
  task độc lập khác. Báo người dùng ở báo cáo cuối.
- `PROPOSALS` đòi đổi chữ ký hàm, thêm thư viện hay sửa docs: **không tự quyết**. Dừng các task phụ thuộc
  vào đề xuất đó và hỏi người dùng.
- Không bao giờ: push, force, xoá nhánh chưa merge, sửa file của coder để "cho xanh nhanh".

## Bước 5 — Kết thúc mỗi đợt / toàn bộ
- Sau đợt có task browser (T04, T13, T20, T21): chạy `pytest -q -x -m browser`.
- Dọn worktree đã merge (`git worktree remove`, `git branch -d task/T<nn>`). Chỉ xoá nhánh đã merge.
- Báo cáo cho người dùng (≤ 15 dòng):
  ```
  Đợt: W<n> xong | Task xong: T.., T.. | Đang chặn: T.. (lý do)
  Cổng kiểm tra: ruff ✓ · unit ✓ (N passed) · browser ✓/—
  Cần bạn quyết: <PROPOSALS / câu hỏi>, nếu có
  Tiếp theo: W<n+1> gồm T.., T..
  ```
- Chạy liên tục qua các đợt. Chỉ dừng khi: hết task, người dùng giới hạn đợt, hoặc có quyết định cần người dùng.

## Mẹo tiết kiệm token cho điều phối
- Không đọc code của coder. Chỉ xem `git diff --stat`, tên file và kết quả cổng kiểm tra.
- Output test: `pytest -q -x --tb=short 2>&1 | tail -n 30`.
- Brief chỉ dán **đúng khối task** và các mục docs liên quan nhất. Coder tự đọc phần còn lại nếu cần.
