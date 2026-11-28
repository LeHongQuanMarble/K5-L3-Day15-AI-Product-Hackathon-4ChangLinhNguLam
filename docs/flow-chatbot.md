# Luồng hoạt động chatbot tạo game (AI Game Composer)

## Luồng Soạn trò chơi trên Web (mới, `ailab/game_flow.py` · `/api/flow`)

Chỉ hỏi **hai ý chính**, không hỏi môn học (trình chơi dùng lại được cho mọi môn):
1. Mỗi câu hỏi có mấy đáp án: 2 (Đúng/Sai), 3 hoặc 4 (A–D).
2. Học sinh điều khiển bằng gì: hình ảnh, tư thế, âm thanh hay chỉ chuột. **Không bắt buộc đã có model**: tạo sau ở "Mô hình tương tác", gắn khi tạo ứng dụng.

```mermaid
flowchart TD
    M["Lời giáo viên"] --> S["T09 guardrails (từ chối tấn công)"]
    S --> X["Đọc ý chính (model hoặc từ khoá)<br/>gộp vào brief đã có"]
    X --> I{"Là yêu cầu soạn game?"}
    I -- không --> L["Lõi AI cũ trả lời như tin nhắn thường"]
    I -- có --> A1{"Biết số đáp án?"}
    A1 -- chưa --> Q1["Hỏi 1 câu + gợi ý nhanh"]
    A1 -- rồi --> A2{"Biết cách điều khiển?"}
    A2 -- chưa --> Q2["Hỏi 1 câu + gợi ý nhanh"]
    A2 -- rồi --> P["Lập KẾ HOẠCH (khung bên phải mới hiện)<br/>chưa tốn lượt sinh game"]
    P --> D{"Giáo viên duyệt?"}
    D -- chỉnh lại --> M
    D -- duyệt --> B["Tạo game ngay:<br/>dùng lại trình chơi khớp manifest, hoặc AI viết game mới<br/>(check_game + 0 cờ an toàn, bản nháp)"]
    B --> T["Giáo viên chơi thử (iframe sandbox)"]
    T --> F{"Muốn sửa?"}
    F -- có, nói ý muốn --> FX["AI sửa bản nháp (tối đa 5 lần)"] --> T
    F -- ưng --> SV["Lưu thành trình chơi Nháp<br/>→ gửi Admin duyệt công khai / ghép ứng dụng"]
```

- Trạng thái (`brief`) do trình duyệt giữ; máy chủ tính lại kế hoạch từ brief, không tin kế hoạch từ máy khách.
- Chọn trình chơi có sẵn theo manifest (có bộ câu hỏi, đủ ô đáp án, hỗ trợ loại model đã chọn), không theo môn học.
- Luồng lõi cũ (`/api/agent`, `python run.py`, eval) giữ nguyên; bên dưới là sơ đồ của nó.

---

## Luồng lõi cũ (`codebase/agent.py`, dùng cho `python run.py`/eval và `/api/agent`)

Nguồn: `codebase/agent.py` (`run_agent`), `codebase/guardrails.py`, `codebase/tools.py`.

```mermaid
flowchart TD
    U["Giáo viên nhập yêu cầu<br/>(Web ailab/server.py hoặc CLI run.py)"] --> RA["run_agent(request)"]

    RA --> G1{"T09 · Pre-LLM Guardrails<br/>validate_request_input<br/>(injection, PII, mạng, bypass HITL)"}
    G1 -- vi phạm --> REF0["REFUSE / ERROR<br/>từ chối + hướng dẫn dùng hợp lệ"]
    G1 -- sạch --> CAT["T08 · Catalog Discovery (@tool thật)<br/>list_players · list_models · list_exams<br/>get_player · get_exam"]

    CAT --> ROUTE["LLM Routing<br/>Reuse-first, Generate-if-needed<br/>trả JSON decision"]
    ROUTE --> D{decision}

    D -- ASK_CLARIFY --> ASK["Hỏi đúng 1 câu<br/>enforce_single_question"]
    ASK -. giáo viên trả lời .-> U
    D -- REFUSE --> REF1["Từ chối"]
    D -- INFO --> INFO["Tư vấn Catalog / soạn câu hỏi<br/>(không tạo game)"]

    D -- REUSE --> R1["Xác thực ID player/model/exam<br/>có thật trong Catalog"]
    R1 -- ID bịa --> ERR["ERROR forbidden_resource"]
    R1 -- ok --> R2{"Player cần bộ đề?"}
    R2 -- dùng đề có sẵn --> R3["exam_row từ Catalog<br/>+ cảnh báo kiểm duyệt kiến thức"]
    R2 -- sinh đề mới --> R4["validate_exam"]
    R4 -- lỗi cú pháp --> R5["Sửa bằng LLM<br/>tối đa 1 lần"]
    R5 --> R4
    R4 -- đạt --> R6
    R3 --> R6["validate_compatibility<br/>(kinds, mapping, role, audio chưa hỗ trợ)"]
    R6 -- không tương thích --> ERR2["ERROR + gợi ý chơi bằng chuột"]
    R6 -- tương thích --> PLAN

    D -- GENERATE --> G2["Sinh HTML nháp theo contract.BRIEF"]
    G2 --> G3{"validate_html_draft<br/>check_game + 0 cờ an toàn"}
    G3 -- lỗi, còn lượt --> G2
    G3 -- "hết MAX_STEPS = 2" --> ERR3["ERROR không tạo được bản nháp"]
    G3 -- đạt --> GEX["Sinh bộ đề (nếu cần)<br/>validate_exam"]
    GEX --> PLAN

    PLAN["validate_application_plan<br/>schema + mouse_always_enabled = true"] --> COMP["compose_application<br/>chỉ tạo DRAFT"]
    COMP --> OUT["validate_output_envelope + redact_text<br/>Envelope v1.0: status = pending_approval"]

    OUT --> HITL{"Giáo viên duyệt (HITL)"}
    HITL -- sửa / từ chối --> U
    HITL -- duyệt --> APP["APPROVED → xem thử iframe sandbox<br/>→ xuất bản vào Catalog"]

    REF0 --> END(["Trả message cho giáo viên"])
    REF1 --> END
    INFO --> END
    ASK --> END
    ERR --> END
    ERR2 --> END
    ERR3 --> END
    OUT --> END
```

## Điểm chính
- **Bảo vệ 2 lớp:** guardrails trước LLM chặn tấn công; sau LLM kiểm bằng luật cứng (ID thật, tương thích, schema, `check_game`).
- **Ưu tiên REUSE:** chỉ `GENERATE` khi Catalog không có cơ chế phù hợp; tối đa 2 lượt (`MAX_STEPS`).
- **Giới hạn sửa lỗi:** sửa bộ đề tối đa 1 lần (`MAX_EXAM_RETRIES`).
- **AI không tự duyệt:** kết quả luôn là `DRAFT` / `pending_approval`; chỉ giáo viên chuyển sang `APPROVED`; Mouse Fallback luôn bật.

> Lưu ý: phần giữa `agent.py` (`_handle_reuse` → `run_agent`) dựng từ docstring và các hàm đã đọc; các nhánh lỗi chi tiết có thể lệch đôi chút.
