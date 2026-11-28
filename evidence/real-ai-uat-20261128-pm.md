# Real AI UAT — 28/11 (chiều) — Blocker GENERATE đã hết

Chạy: `python ailab/accept_real_ai_uat.py --confirm-paid --cases tc02,tc01`
Server: http://127.0.0.1:8800 (branch `fix/p0-composer-capability` @ b1ed887, Real AI openai/gpt-4o-mini)
Ngân sách PM duyệt: $0.10 — **chi phí thực tế: ~$0.004** (11.600 token in + 3.796 token out, lấy từ trường usage của API, không ước lượng; đơn giá gpt-4o-mini $0.15/1M in, $0.60/1M out)

| Case | Prompt | Kết quả | Số câu sinh | Player | Model | Publish/Play/Reload |
|---|---|---|---|---|---|---|
| TC02 | Hệ Mặt Trời, chỉ tay 4 hành tinh (đúng prompt UAT thất bại trước đây) | **PASS 27/27** | 4 | generate_new (mới, không REUSE) | hands + mapping grab→fist, release→open | PASS (app_id thật, share=0, reload nhất quán) |
| TC01 | Thu hoạch táo phép nhân lớp 3, 5 câu | **PASS 27/27** | 5 | generate_new | hands | PASS |

Mức kiểm chứng: **STATIC + PROTOCOL** (srcdoc CSP/manifest/JLRuntime/hands-handshake/data-jl-camera, mapping, số câu, HITL publish có plan_hash, persistence reload).
Chưa kiểm chứng ở đây (để PM Human UAT): landmark thật khi chỉ tay, debounce khi tay đứng yên, micro (audio flag), browser console/network trên máy giáo viên.
Phạm vi synthetic-vs-real: các check dùng HTTP API + srcdoc (synthetic); runtime chuột/camera thật do trình duyệt — L5 headless smoke PASS riêng (evidence/runtime-smoke-20261128-pm.md).

Lưu ý chi phí: lần chạy đầu TC02 (trước khi sửa 1 lỗi check trong script UAT, không phải lỗi sản phẩm) tốn thêm ~7.4k token (~$0.002). Tổng cả buổi < $0.01.

