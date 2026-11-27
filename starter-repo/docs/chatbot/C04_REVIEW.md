# C04 — Gửi lại review sau sửa hai P2

Ngày 2026-11-27, Asia/Bangkok. **DONE trong phạm vi module**: agent review độc lập đã chạy 216/216 test đạt và kiểm lại hai lỗi P2 (metadata nguồn/aiGenerated qua public reply, xung đột gameKind/manifest hai hướng). Không phát hiện lỗi chặn mới trong phạm vi đã kiểm. Người dùng cho phép commit khi đạt; chưa cho phép push chatbot. Nội dung bên dưới giữ lịch sử gói bàn giao trước nghiệm thu. Sinh đề AI, web, lưu artifact và xác minh kiến thức chưa được nghiệm thu.

## Trạng thái repo và phân công

Git root là thư mục K5-L3-Day15-AI-Product-Hackathon-4ChangLinhNguLam; chạy lệnh từ đó. HEAD `42ce3dc5fb9df48c0c981d3785e1c236078fa8ff` đã merge cập nhật main, mã hiện ở `ailab/`; docs vẫn ở `starter-repo/docs/chatbot/`. Việc chuyển đường dẫn là cập nhật main do người dùng thực hiện, không phải thay đổi coder C04. DB cũ giữ tại `starter-repo/ailab/data/ailab.db`. Không dùng/di chuyển DB, không apply/drop stash, không merge/reset/clean trong lượt này.

| File bàn giao | Chủ sở hữu độc quyền | Thay đổi |
|---|---|---|
| ailab/chatbot/schemas.py | c04_metadata_fix | Bản sửa metadata từ lượt trước đã khôi phục; kiểm lại và giữ nguyên, không ghi đè |
| starter-repo/docs/chatbot/AI_INTEGRATION_CONTRACT.md | c04_metadata_fix | Hợp đồng mới/cũ đã khôi phục; kiểm lại, không sửa thêm |
| ailab/chatbot/exams.py | c04_business | Sửa nhánh phát hiện xung đột trước not_needed |
| ailab/test_chatbot_exams.py | c04_tests | Thêm 7 test hồi quy, giữ 35 test trước |
| starter-repo/docs/chatbot/C04_SPEC.md | Điều phối | Hợp đồng lỗi, metadata và đường dẫn sau merge |
| starter-repo/docs/chatbot/AI_PROGRESS.md | Điều phối | Tiến độ/bằng chứng, C04 giữ REVIEW |
| starter-repo/docs/chatbot/AI_IMPLEMENTATION_PLAN.md | Điều phối | Theo dõi TODO sinh câu hỏi bằng AI từ lượt trước, đã khôi phục |
| starter-repo/docs/chatbot/C04_REVIEW.md | Điều phối | Gói review hiện tại |

Điều phối chỉ chốt hợp đồng, đọc mã và kiểm tra; không viết mã chức năng. Coder kiểm thử được giao sau khi interface ổn định; không có hai coder sửa cùng file.

## A. Metadata nguồn qua phản hồi công khai

Bản sửa schemas.py đã có khi tiếp tục: whitelist sourceRefs giữ sourceId (chuỗi được che bí mật), start/end (int không bool, không âm), quote; ExamQuestion giữ aiGenerated boolean. Sai kiểu thành null theo bộ lọc hiện có. Giữ metadata nguồn cũ documentId/kind/page/paragraph/locator, không tự suy offset từ nguồn cũ. Trường lạ/nội bộ bị bỏ, chuỗi bí mật được che; draft và state không đổi. Quote vẫn bị cắt tối đa 500 ký tự và che bí mật, không dùng bản công khai để kiểm lại offset.

Điều phối chạy chuỗi thật `prepare_exam → state.proposal.exam → to_public_reply` sau merge. Ví dụ kết quả:

```json
{"aiGenerated":false,"sourceRefs":[{"sourceId":"s1","start":0,"end":3,"quote":"1+1"}]}
```

Draft không đổi, trường internal không xuất hiện. Hồi quy kiểm cả aiGenerated=false/true, nguồn cũ, alias độc lập, sai kiểu, redaction và quote dài 700 ký tự (giữ offset 0..700, quote công khai dài 500).

## B. gameKind xung đột manifest

Trước sửa, hai yêu cầu `{gameKind:list,manifest:{questions:exam}}` và `{gameKind:questions,manifest:{content:{kind:texts}}}` đều trả `not_needed`, không issue. Điều phối đã tái hiện trên bản khôi phục tại Git root trước khi giao sửa.

Sau sửa, prepare_exam nhận diện loại manifest trước, so gameKind tường minh rồi mới xét bỏ qua Exam/đòi câu hỏi. Xung đột hai hướng trả:

```json
{"status":"needs_revision","exam":null,"issues":[{"code":"incompatible_exam","field":"gameKind","message":"Loại game yêu cầu không khớp Player đã chọn; cần giáo viên chọn cách xử lý."}],"validation":{"examFormat":"not_checked","contentGrounding":"not_checked","answerReview":"not_checked","compatibility":"failed"}}
```

Issue thực tế còn questionIndex=null. Không tự thay Player hoặc bỏ đề âm thầm. Khi thiếu gameKind thì suy theo manifest; questions=exam ưu tiên content.kind=texts như nền tảng. Game danh sách thật và list không manifest vẫn not_needed, không ép có Exam. Hồi quy bao phủ xung đột có/không questions, cả questions=exam và content.kind=questions, cùng các đường bình thường.

## Kiểm thử và bằng chứng trước/sau

Chạy từ Git root:

```powershell
python -m unittest discover -s ailab -p 'test_chatbot_exams.py'
python -m unittest discover -s ailab -p 'test_*.py'
git diff --check
git diff HEAD --name-status
git diff origin/main --name-status --diff-filter=MDRT
git ls-files --others --exclude-standard
```

- Điều phối: **42/42 C04 OK**, 0.158 giây; **216/216 toàn bộ OK**, 24.728 giây (174 trước C04 + 35 C04 cũ + 7 hồi quy).
- Coder kiểm thử: **216/216 OK**, 24.370 giây. Coder metadata: **36/36 schema OK**, 0.024 giây; không ghi đè bản khôi phục.
- Điều phối và coder kiểm thử đều chạy 7 test mới trong ExamReviewOneTests với schemas.py/exams.py trước sửa, nạp bằng importlib từ `%TEMP%/codex-c04-review1-before`, chỉ thay tham chiếu module trong process, không ghi đè repo: **6 FAIL + 6 ERROR tính theo subtest**, 7 test methods. Sáu ca xung đột trả not_needed; các lỗi metadata là thiếu aiGenerated/sourceId/start. Hai methods legacy/đường bình thường vẫn đạt. Với bản hiện tại 7 methods đều đạt trong bộ 42.
- Snapshot chỉ là bản tạm local; reviewer có thể tái hiện bản schema cũ từ HEAD, bản exams trước sửa không có trong Git vì file vẫn untracked. Không bịa đã có commit trước/sau. Bản tạm sau merge còn tại `%TEMP%/codex-c04-postmerge-before` (schema ở đó đã có bản sửa khôi phục).

Các test mới: test_review1_provenance_survives_full_public_reply_for_both_ai_flags; test_review1_legacy_refs_survive_without_inventing_offsets; test_review1_unknown_internal_and_secrets_filtered_without_mutation; test_review1_malformed_new_fields_are_null; test_review1_public_quote_cap_does_not_change_original_offsets; test_review1_explicit_game_kind_conflict_precedes_missing_questions; test_review1_compatible_and_unspecified_kinds_preserve_normal_paths.

## Đối chiếu Git và bảo toàn

HEAD không đổi trong lượt. Ref local origin/main khi kiểm là `96982f5cae5a0c624f6becd51773e25cc414a4c8` (mới hơn 4ae3b8f nêu trong bàn giao); phiên này không fetch hoặc nhập thêm main.

`git diff HEAD --name-status` có schemas.py, spec.md, AI_IMPLEMENTATION_PLAN.md, AI_INTEGRATION_CONTRACT.md, AI_PROGRESS.md. Trong đó **spec.md là thay đổi có sẵn ngoài C04**, giữ nguyên; không đưa vào danh sách coder sửa. Các file mã/spec/test C04 mới phải đọc riêng vì untracked không nằm trong diff.

So working tree với origin/main local: các khác biệt tracked là phần bổ sung chatbot đã có từ trước; `--diff-filter=MDRT` rỗng, không có file nền tảng tracked bị sửa/xóa/đổi tên so với ref đó. Điều này không thay cho việc review các file mới. C04 không di chuyển file nào; chuyển mã ra root đã nằm trong merge HEAD.

Danh sách untracked riêng lúc kiểm:

- ailab/chatbot/exams.py
- ailab/test_chatbot_exams.py
- starter-repo/ailab/data/ailab.db — DB thật cũ, không phải artifact C04, tuyệt đối không add
- starter-repo/docs/chatbot/C04_REVIEW.md
- starter-repo/docs/chatbot/C04_SPEC.md
- starter-repo/docs/chatbot/COORDINATOR_HANDOFF_CODEX.md
- starter-repo/docs/chatbot/COORDINATOR_HANDOFF_CURRENT.md

`git diff --check` đạt; Git chỉ cảnh báo chuyển LF/CRLF theo cấu hình. Không chạy git add -A, commit/push hay thao tác stash.

SHA-256 đầu/cuối lượt tiếp tục không đổi:

- TEAMS.md: `1F0D5573ECD1EA269742D902B09A28055C470FBFF17782722007CBE36B3EFCA5`
- spec.md: `7FD9F5AD30304AE17DF2037E62D85AE15EC088412A8A99FD0E5FB783EB30560B`
- starter-repo/ailab/data/ailab.db: `7059447DA279E7241E6B8815AD307D17B0B018385A28A9777608AE97D84F5C2F`

SHA-256 mã bàn giao:

- exams.py: `5C4BFC2B553E2E2DC09FD253C867758601344D3A93DDB1C1236266B33F282CE1`
- schemas.py: `C6AAE5E5336395013444FE12A63F7CBB01AAE6BA575D0794B726B0AEB884BE47`
- test_chatbot_exams.py: `78C0D8183F1FF944D5F59A4D1739901174D87B58CC586D201544F4445D2ABE0C`

## Giới hạn còn nguyên

C04 chỉ chuẩn bị và kiểm câu hỏi có cấu trúc được cấp/chọn Exam có quyền. **Sinh câu hỏi bằng AI chưa triển khai**; O17 và kế hoạch C04 theo dõi interface/provider/provenance/giới hạn lỗi/duyệt giáo viên/bằng chứng AI thật trong các đợt sau. Không tuyên bố Exam Generator tổng thể hoàn thành.

Chưa upload PDF/DOCX/OCR, chưa tích hợp web/preview/lưu Exam/App; không xác minh kiến thức bằng parser hoặc LLM. Source do adapter lọc quyền trước khi cấp, I02 phải kiểm lại quyền khi accept. Metadata không lưu được trong định dạng Exam văn bản gốc. answerReview vẫn not_checked. Nguồn fixture/AI tự sinh vẫn cần giáo viên xem lại. C04 giữ REVIEW tới khi agent review độc lập hiện tại xác nhận đạt.
