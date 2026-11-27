# T14 — Web/Backend Integration & HITL (bằng chứng)

> Ngày kiểm chứng: 28/11/2026 · Model thật `gpt-4o-mini` (`.env` cục bộ, không commit) ·
> Người thực hiện: TV4 hỗ trợ TV3 theo yêu cầu "hoàn thành Task của TV3 và TV4" — chờ TV3 review chéo.

## 1. Shared Core Web/CLI

| Entry point | Gọi tới | Ghi chú |
|---|---|---|
| `python run.py` / `run.py eval` | `codebase.agent.answer()` → `_run_agent_core()` | CLI/eval giữ nguyên |
| `POST /api/agent` (Web mới) | `ailab/agent_bridge.call()` → `codebase.agent.run_agent()` | `registry=None` để dùng cùng `@tool` Catalog như CLI |
| `POST /api/chat` (UI hiện hành) | `ailab/llm.generate()` → `codebase.agent.run_agent()` | Bỏ prompt/routing riêng của `llm.py`; chỉ giữ khuôn fake offline |

`ailab/llm.py` giờ **không tự dựng prompt/routing khi model thật** — chỉ chuyển envelope sang
dạng `{text, html, simulated, model}` mà UI legacy cần. Khối HTML của `GENERATE` vẫn qua
`contract.parse()`; bản `REUSE` không trả HTML thô (`html=None`) đúng Contract.

## 2. UI projection an toàn & cảnh báo kiến thức

`agent_bridge.call()` trả `application_contract.to_ui_response(envelope)`:

- `html_omitted: true` — không đẩy HTML thô vào tin nhắn chat.
- `knowledge_review_required` lấy từ `warnings[].code == "knowledge_review_required"`.
- `hitl: {"status": "draft", "can_publish": false}` — mọi output của AI ở dạng nháp.
- `trace`: `{"model_calls", "tool_calls", "tokens_in", "tokens_out", "models", "errors"}`.

Giao diện (nhánh `feat/ui-ux-refactor`, lấy riêng `ailab/web/` để giữ bản docs freeze của `main`)
đã có: inline HITL, nút Phê duyệt / Từ chối / Chỉnh sửa, khung preview `iframe sandbox="allow-scripts"`,
cảnh báo "Kiểm duyệt kiến thức: BẮT BUỘC trước khi dùng trên lớp".

## 3. Cổng HITL — kết quả HTTP thật

Server chạy `python ailab/server.py` từ **gốc repo** (`127.0.0.1:8800`), đăng nhập rồi gọi endpoint:

| Request | HTTP | Kết quả |
|---|---|---|
| `POST /api/agent` (câu REUSE Toán 12) | 200 | `decision=REUSE`, `html_omitted=true`, `hitl.status=draft`, trace `model_calls=1`, `tokens_in=1777`, `tokens_out=152`, `models=['gpt-4o-mini']` |
| `POST /api/agent/publish` (không `approved`) | **403** | `error=hitl_required` |
| `POST /api/agent/publish` (payload cố `status=APPROVED`) | **400** | `error=hitl_forbidden` |
| `POST /api/agent/publish` (envelope `draft`/`rejected`/`REFUSE`) | **403** | `error=hitl_not_ready` |
| `POST /api/agent/publish` (`approved=true`, plan qua validate) | 200 | `status=approved`, `bypass_count=0`, có `plan_hash` |
| `POST /api/agent/review` (plan giữ nguyên) | 200 | `status=approved, can_publish=true` |
| `POST /api/agent/review` (đổi `name` sau duyệt) | 200 | `status=draft, can_publish=false` — phải duyệt lại |

**HITL Bypass Count = 0** (mọi cố gắng tự duyệt/đăng bị chặn ở Backend, không phải chỉ ở UI).

## 4. ProviderError → HTTP 502/503

`agent_bridge.PROVIDER_HTTP` ánh xạ `ProviderError.kind`; server `_handle()` bắt `BridgeError`
và trả `{error, message}` không chứa key/body thô:

- `rate_limit`, `timeout`, `network`, HTTP `429`/`5xx` → **503**.
- `auth`, `config`, `bad_response`, `usage_missing`, HTTP `4xx` khác → **502**.

Trace vẫn `end()` trước khi ném lỗi để `run.py eval`/Web ghi trung thực lỗi và token.

## 5. Unit test

```
python -m unittest discover -s codebase -p "test_*.py"        → 113/113 OK
$env:MODEL_PROVIDER='fake'; python -m unittest discover -s ailab -p "test_*.py" → 159/159 OK
```

Trong đó `ailab/test_agent_bridge.py` (10 test mới) phủ: ánh xạ 502/503, chặn tự `APPROVED`,
từ chối `draft`/`rejected`/`REFUSE`, bắt buộc kiểm duyệt kiến thức, quay về `draft` khi sửa sau duyệt,
và UI projection `html_omitted`.

## 6. Ghi chú môi trường

Đã thêm `sys.stdout.reconfigure(encoding="utf-8")` ở đầu `ailab/server.py`: PowerShell Windows
dùng `cp1252` sẽ crash ngay lúc khởi động khi in tiếng Việt (`UnicodeEncodeError`). Sau sửa,
`python ailab/server.py` chạy thẳng không cần đặt `PYTHONIOENCODING` (đã kiểm `/health` = 200).

## 7. Giới hạn đã biết

- Bản ghi phê duyệt do client giữ (`plan_hash`); server không lưu trạng thái `approved` vào DB.
  Đây là ranh giới HITL tối thiểu: mọi xuất bản đều phải qua `POST /api/agent/publish` với phê duyệt
  rõ ràng của giáo viên. Cần TV3 quyết định có thêm bảng `approvals` trong CP4 hay không.
- `/api/apps` legacy vẫn là thao tác trực tiếp của người dùng đã đăng nhập (không phải AI tự ghi).

## 8. Handoff sang T15

Chạy demo: `python ailab/server.py` → `http://127.0.0.1:8800` → đăng nhập → "Soạn trò chơi" →
chế độ Mock (4 preset REUSE/GENERATE/ASK_CLARIFY/REFUSE) để quay video 30s, hoặc "Chế độ thật"
để gọi `/api/chat` → Shared Core Real AI.
