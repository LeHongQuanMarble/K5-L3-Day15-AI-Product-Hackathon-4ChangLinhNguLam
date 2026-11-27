# Data card — dữ liệu bản chạy thử dùng

> T16 · bản CP2 trước **18:30 ngày 27/11/2026** · chấm R4.
> Snapshot gốc: `main` @ `14dea37` (27/11/2026 17:05); nguồn gốc `790277a` (12:07, AI Lab) và `5be60a2` (12:49, bộ đề/ảnh). Bản CP2 nộp trên nhánh `feat/t16-t17-cp2-data-eval`. Repo: `https://github.com/LeHongQuanMarble/K5-L3-Day15-AI-Product-Hackathon-4ChangLinhNguLam`.
> Cập nhật CP3 (28/11/2026): khóa Catalog Snapshot tại commit `79822a4` (nhánh TV3 `feat/t12-catalog-composer-tv3`, PR #7 chờ merge) và mở rộng benchmark lên 20 câu trên nhánh `feat/t16-t17-cp3-update`. **Không đổi** `eval/metric_spec.yaml` hay `spec.md` §7 đã freeze CP2.
> Lát cắt A3: giáo viên mô tả nhu cầu → AI chọn tổ hợp `Model + Player + Question Set` → giáo viên duyệt. **Không có bước chia train/val/test** cho cả 4 dataset dưới đây: bản chạy thử không huấn luyện mô hình. Không commit dữ liệu cá nhân thật, API key hay nguyên file data BTC cấp.

## Dataset 1 · Catalog AI Lab — Model / Player / Question Set

| | |
|---|---|
| Dùng để làm gì | Nguồn lựa chọn tổ hợp cho quyết định AI; là "sự thật" để benchmark kiểm tra ghép nối đúng / hỏi lại / từ chối. |
| Từ đâu | `ailab/store.py` (`init`, `SEED_IMAGES`, `clean_model`, `clean_app`), `ailab/contract.py`, `ailab/llm.py` (2 template player); snapshot đọc qua `ailab/composer.py` + `ailab/export_catalog.py` → `data/catalog_snapshot.json`; mô tả ở `ailab/staging.md` mục 3, 5. |
| Xử lý những bước gì | `store.init()` tạo 1 model built-in + 2 player mẫu; `contract.parse()` đọc manifest `jl-camera`, `contract.scan()` quét 6 luật cờ, `contract.secure()` chèn CSP; `clean_app()` / `composer.validate_compatibility()` kiểm tương thích `kinds`/`accepts`/mapping. Snapshot **cố định, không đóng dấu thời gian**: chạy `python ailab/export_catalog.py` ghi `data/catalog_snapshot.json`. Không lọc, không ẩn danh, không chia tập: không có dữ liệu người dùng. |
| Số dòng / số đoạn | **17 mục** = 1 model `Bàn tay (MediaPipe)` (3 lớp `fist`/`open`/`none`) + 2 player (`Quiz ABCD bằng cử chỉ`, `Vòng quay chọn tên`) + 6 bộ đề/90 câu + 8 ảnh. 90 câu và 8 ảnh được tách ở dataset 2/3, **không cộng lại lần hai**. Snapshot ghi 2 players / 1 model / 6 exams. |
| Phiên bản / ngày lấy | Mã nguồn @ `14dea37` 17:05 (cập nhật sau commit), gốc `790277a` 12:07 và `5be60a2` 12:49. **Catalog Snapshot version: `79822a4`** (28/11/2026, nhánh `feat/t12-catalog-composer-tv3`, PR #7). Dùng đúng hash này cho Evaluation Run 1 và Run 2; không export lại sau khi DB thay đổi. |
| Nhãn | `synthetic`. Cách sinh: do AI Lab tạo từ mã nguồn (`store.init`, template `llm.py`), **không phải AI sinh nội dung có seed**; seed: không áp dụng; người kiểm: TV3 tạo, TV4 đối soát bằng script snapshot; **số mục kiểm tay: 0/17**. |
| Giới hạn | Chưa thử webcam thật; mô hình Âm thanh chỉ lưu, chưa chạy (`composer.runtime_static_checks()` mới kiểm tĩnh); chưa đo tải nhiều người dùng. `staging.md` mục 5 ghi "không có mô hình Bàn tay dựng sẵn" nhưng `store.py init()` có tạo và snapshot xác nhận → TV3 chỉ cần thống nhất lại văn bản. |

## Dataset 2 · Sáu bộ đề — `ailab/seed_exams.json`

| | |
|---|---|
| Dùng để làm gì | Nguồn câu hỏi ghép vào player (`questions: "exam"`); đầu vào câu thử "dùng bộ đề có sẵn" và kiểm nội dung/lớp học. |
| Từ đâu | `ailab/seed_exams.json`, do **AI soạn** (`staging.md`: "do AI soạn, thầy cô cần kiểm lại trước khi dùng thật"). Không phải đề BTC, không phải câu của giáo viên ngoài nhóm. |
| Xử lý những bước gì | `store.seed_exams()` đọc JSON → `parse_questions()` kiểm từng dòng (`Câu hỏi ∣ Đáp án A ∣ … ∣ =B`; 2–6 đáp án hoặc Đúng/Sai), lỗi thì không lưu; ghi bảng `exams` với `owner_id=0`. Không ẩn danh, không chia tập. |
| Số dòng / số đoạn | **6 bộ × 15 = 90 dòng câu hỏi** (Toán 12 · Tiếng Anh 12 · Tin học 12, mỗi môn 2 bộ). Đếm bằng `parse_questions()` tại `14dea37`, khớp snapshot `79822a4`. |
| Phiên bản / ngày lấy | `ailab/seed_exams.json` @ `5be60a2` (27/11/2026 12:49). |
| Nhãn | `synthetic`. Cách sinh: AI viết theo mô tả trong `staging.md`; prompt gốc và seed **không lưu trong repo** → ghi "không có seed", không suy diễn; người kiểm: chưa có; **số dòng kiểm tay: 0/90**. |
| Giới hạn | Chưa có giáo viên kiểm nội dung/đáp án → **không dùng làm bằng chứng pain**, không làm chuẩn chấm nội dung khi chưa kiểm; có thể lệch chương trình/độ khó. |

## Dataset 3 · Ảnh nền — `ailab/seed_images/*.jpg`

| | |
|---|---|
| Dùng để làm gì | Ảnh đại diện cho model/player/app/bộ đề; chỉ để nhận diện khi chọn, không phải đầu vào quyết định của AI. |
| Từ đâu | 8 file `.jpg` ánh xạ theo `store.SEED_IMAGES`; 6 ảnh chụp màn hình game thật + 2 ảnh minh hoạ (Vòng quay, Bàn tay) theo `staging.md`; chép từ JULY Learning. |
| Xử lý những bước gì | `_data_uri()` → `data:image/jpeg;base64`; `clean_image()` kiểm định dạng và ≤300 KB; `seed_images()` chỉ điền khi mục chưa có ảnh (ảnh tự đổi thì giữ nguyên). Không lọc, không ẩn danh, không chia tập. |
| Số dòng / số đoạn | **8 file** (640×360): `badminton, penalty, rescue, voiceflap, tet, quiz` (chụp màn hình) + `wheel, hands` (minh hoạ). |
| Phiên bản / ngày lấy | `ailab/seed_images/` @ `5be60a2` (27/11/2026 12:49). |
| Nhãn | 6 ảnh chụp màn hình thật; 2 ảnh minh hoạ `synthetic`. Cách sinh: chụp màn hình/vẽ minh hoạ, không có script sinh hay seed; seed: không áp dụng; người kiểm: TV3 nhập, TV4 chưa kiểm; **số ảnh kiểm tay: 0/8**. Không chứa ảnh học sinh/giáo viên. |
| Giới hạn | Ảnh game mẫu, không phản ánh lớp học thật; không dùng để suy luận tương thích thiết bị; không có metadata ngày chụp. |

## Dataset 4 · Bộ câu thử CP3 — `eval/benchmark.csv`

| | |
|---|---|
| Dùng để làm gì | Chấm 4 nhóm metric đã freeze trong `eval/metric_spec.yaml`; đo routing/catalog, chất lượng bộ đề, an toàn HTML/tương thích và HITL/từ chối. |
| Từ đâu | 12 câu CP2 (`feat/t16-t17-cp2-data-eval`) giữ nguyên + 8 câu TV4 tự soạn CP3 (`B13`–`B20`) đối chiếu snapshot `79822a4` và các luật trong `ailab/contract.py`, `ailab/composer.py`. Không có câu phỏng vấn/khảo sát thật. |
| Xử lý những bước gì | `python run.py check` đọc CSV (6 cột, đếm type/source, kiểm metric); `python run.py eval` tạo `eval/run-N.csv` + `traces/run-N.jsonl`; chấm bằng `python run.py score`. Không sửa `expected` của 12 câu CP2. |
| Số dòng / số đoạn | **20 câu** = thuong 6 · kho 10 · tu_choi 4 (trong đó 4 câu tấn công an toàn/HITL). Nguồn: `tu_viet` 20 · `nguoi_dung` 0 · `data_that` 0 → **0/20 từ người dùng hoặc data thật**. |
| Phiên bản / ngày lấy | CP2 @ PR #6 (`6af9bc2`); mở rộng CP3 28/11/2026 trên nhánh `feat/t16-t17-cp3-update`, chờ TV4 xác nhận. |
| Nhãn | `synthetic` / `tu_viet`. Cách sinh: TV4 soạn theo Catalog Snapshot và 4 lớp chỗ khó trong `spec.md` §5; seed không áp dụng; người kiểm chéo: chưa có (T18). |
| Giới hạn | Chưa thay 4 câu bằng lời giáo viên hoặc dữ liệu thật (T03/TV1); không dùng làm bằng chứng pain; metric đã freeze CP2 nên chỉ bổ sung expected/pass_criterion, không đổi định nghĩa. |

## Chưa có — không tính vào Data Card CP2/CP3

- `eval/benchmark.csv`: đã đạt **20 câu** trước CP3 nhưng vẫn **0/20 từ nguồn thật** → chờ T03 (TV1) thay 4 câu bằng `nguoi_dung`/`data_that`.
- `eval/metric_spec.yaml` 4 metric + `spec.md` §7: bản T17 đã freeze CP2, **không sửa**.
- Phỏng vấn giáo viên: `evidence/interviews/` mới có `TEMPLATE.md` → **0 phỏng vấn, 0 trích dẫn** (T03 · TV1).
- `ApplicationPlan` JSON mẫu/contract: `codebase/agent.py` hiện vẫn luồng "mô tả game → viết HTML", chưa khớp lát cắt chọn tổ hợp (T06/T08 · TV2; T02 · TV1). Bản nháp Composer TV3 ở PR #7 chờ tích hợp.
- Catalog Snapshot: đã có tại commit `79822a4` và file `data/catalog_snapshot.json` trên nhánh TV3; **chưa merge vào `main`**. Evaluation Run 1/2 phải dùng đúng hash này sau khi merge, không export lại với DB đã đổi.
- `data/preclass/`, `data/training-ops/` (data BTC): đã xoá ở HEAD `14dea37`, **không dùng** cho A3, không commit lại.

> Dữ liệu `synthetic` ở trên là tài sản/Câu do AI soạn, **không phải bằng chứng pain**. Không xoá các dòng "chưa có"; cập nhật khi TV1/TV2/TV3 bàn giao.
