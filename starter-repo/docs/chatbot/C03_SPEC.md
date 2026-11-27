# C03 — Danh mục, định tuyến game và chọn model (chốt trước khi giao coder)

Nền: commit `500a718` (C01, C02, I01 DONE). Chỉ thêm file mới; không sửa file gốc `faa44a8`.
C03 là module nghiệp vụ thuần + một hàm đọc DB. **Chưa** nối vào `workflow.py`/`chatbot_server.py` (việc của I02).
Không sinh HTML, không tạo Player/Exam/App, không ghi DB.

## 1. File và chủ sở hữu

| File | Coder | Ghi chú |
|---|---|---|
| `ailab/chatbot/catalog.py` (mới) | Coder nghiệp vụ | Toàn bộ logic C03 |
| `ailab/test_chatbot_catalog.py` (mới) | Coder kiểm thử | Viết theo interface dưới đây; chạy song song, đối chiếu khi nghiệp vụ bàn giao |
| `docs/chatbot/C03_SPEC.md` | Điều phối | Tài liệu này |

Không ai khác sửa `catalog.py`/file test. Cần đổi interface → báo điều phối, cập nhật spec trước.

## 2. Dữ liệu thực tế (đã đọc ở `faa44a8`)

- Player: `manifest` qua `contract.parse`. Có `inputs` → **game camera**: `inputs[{key,label,required,accepts[action|rest|empty]}]`, `kinds` (mặc định `[image,pose]`), có thể `questions:"exam"`. Không `inputs` → **game thường**: `questions:"exam"` hoặc `content{kind: texts|questions, label, min, max}`.
- Quyền dùng Player: `store.player_usable(row, user)` (admin; của mình; hoặc `approved`+`public`; `hidden` chỉ admin).
- Model: `kind ∈ image|pose|audio|hands`, `outputs[{key, role∈action|rest|empty}]`, quyền `store.model_visible(row, user)` (admin; của mình; `public`).
- Runtime `play.js` chạy được `image`, `pose`, `hands`; **audio không chạy** (chỉ lưu).
- Luật tạo App `store.clean_app`: Player có `inputs` **bắt buộc** có model (kind ∈ `manifest.kinds`), mapping mỗi ô bắt buộc → một lớp tồn tại, không dùng một lớp hai lần, role ∈ `accepts`. Player không `inputs` → không model.
- Mặc định DB mới: "Quiz ABCD bằng cử chỉ" (4 ô A–D bắt buộc, `kinds=[image,pose]`, `questions:"exam"`), "Vòng quay chọn tên" (`content.kind=texts`), model "Bàn tay (MediaPipe)" (`hands`, lớp `fist`/`open` action + `none` empty).

## 3. Interface `ailab/chatbot/catalog.py`

Hằng: `RUNTIME_KINDS = ("image","pose","hands")`. Mọi xung đột dùng mã có trong `schemas.ERROR_CODES`.

### 3.1 `load_catalog(c, user) -> catalog`
Đọc DB bằng kết nối `c` (không commit, không ghi). Chỉ Player `store.player_usable` và Model `store.model_visible`. Không trả `html`, `url`, `flags` hay dữ liệu người khác ngoài các trường dưới.
```
{"players": [{"id","name","description","ownerId","mine","sample","status","visibility","manifest"}],
 "models":  [{"id","name","kind","outputs":[{"key","role"}],"mine","builtin","visibility"}]}
```
Sắp xếp ổn định theo `id` tăng dần.

### 3.2 `describe_player(manifest) -> info`
```
{"gameKind": "questions"|"list"|"other",   # questions: questions=="exam" hoặc content.kind=="questions"; list: content.kind=="texts"
 "needsModel": bool,                        # có inputs
 "inputs": [{"key","label","required","accepts"}], "requiredCount": int,
 "kinds": [...] (rỗng nếu không inputs),
 "runtimeKinds": kinds ∩ RUNTIME_KINDS}
```

### 3.3 `select_model(manifest, models, interaction) -> selection`
`interaction` = `requirements["interaction"]` (`useModel`, `requestedKinds`, `mouse`).
```
{"status": "not_needed"|"selected"|"conflict",
 "modelId": int|None, "kind": str|None, "mapping": {inputKey: outputKey},
 "reason": str, "conflicts": [Conflict], "mouse": True}
```
Luật (theo thứ tự):
1. Player không `inputs`:
   - `useModel is False` → `not_needed`, `modelId=None`, `mapping={}` — **kể cả khi `requestedKinds` còn lưu từ lựa chọn cũ** (useModel=false thắng; sửa sau review C03 lần 1).
   - `useModel is True`, hoặc `useModel is None` mà `requestedKinds` khác rỗng → `conflict` `unsupported_interaction` ("game này không đọc camera/model"), kèm lựa chọn: chơi chỉ chuột / chọn game camera khác.
   - còn lại → `not_needed`, `modelId=None`, `mapping={}`.
2. Player có `inputs` mà `useModel is False` → `conflict` `incompatible_model`: "game này cần model để tạo App (luật nền tảng); chuột vẫn chơi được khi chạy" + lựa chọn: cho phép dùng model / chọn game không cần camera. **Không chọn model.**
3. `requestedKinds` chỉ có `audio` → `conflict` `unsupported_interaction` (audio chưa hỗ trợ), không hứa chạy.
4. Ứng viên = model trong `models` có `kind ∈ manifest.kinds ∩ RUNTIME_KINDS`, và nếu `requestedKinds` (bỏ audio) khác rỗng thì `kind ∈ requestedKinds`. Với mỗi ứng viên, tạo mapping tự động (3.4); hợp lệ khi `validate_mapping` không lỗi.
5. Có ứng viên hợp lệ → `selected`, chọn theo thứ tự: kind đúng `requestedKinds[0]` trước; của mình (`mine`) trước; `id` nhỏ trước.
6. Không có → `conflict` với lý do cụ thể nhất: không model nào cùng kind (`incompatible_model`, nêu kind game đọc và kind hiện có), hoặc thiếu lớp (`incompatible_model`, "model X có N lớp hành động, game cần M ô"). Không bịa lớp, không gắn một lớp vào nhiều ô.

### 3.4 `auto_mapping(manifest, model) -> mapping` (sửa sau review C03 lần 1)
Bài toán ghép cặp hai phía (ô ↔ lớp; cạnh khi role lớp ∈ `accepts` của ô; mỗi lớp tối đa một ô). Yêu cầu:
1. **Đầy đủ:** nếu tồn tại cách gán cho TOÀN BỘ ô bắt buộc thì phải tìm ra (dùng thuật toán ghép cặp cực đại, vd đường tăng/augmenting path — không kết luận thiếu lớp chỉ vì chọn tham lam thất bại).
2. **Ô bắt buộc trước:** ghép cực đại cho ô bắt buộc trước; ô tùy chọn chỉ được lấy lớp còn lại sau khi ô bắt buộc đã được ghép tối đa. Ô tùy chọn không được làm giảm số ô bắt buộc ghép được.
3. **Ưu tiên trùng key** (không phân biệt hoa thường) chỉ khi không làm giảm (1) và (2): trong các cách ghép cực đại, chọn cách có nhiều cặp trùng key nhất (vd thử cạnh trùng key trước trong thứ tự duyệt, rồi kiểm lại bằng đường tăng).
4. Kết quả xác định (deterministic) theo thứ tự ô trong manifest và lớp trong model; không dùng lại lớp; không sửa đầu vào.
5. Nếu ô bắt buộc không thể ghép hết thì trả mapping tốt nhất có được; `validate_mapping` sẽ báo thiếu và `select_model` báo `conflict` thiếu lớp (ca thực sự không đủ lớp vẫn phải bị chặn).

### 3.5 `validate_mapping(manifest, model, mapping) -> result`
Áp đúng luật `store.clean_app` + runtime:
```
{"ok": bool, "errors": [{"input": key|None, "code", "message"}], "check": schemas.make_check("compatibility", ...)}
```
Lỗi: model `kind ∉ manifest.kinds`; kind không chạy được (audio); ô bắt buộc thiếu; lớp không tồn tại; lớp dùng hai lần; role không thuộc `accepts`; key mapping không phải ô của game.

### 3.6 `route_game(requirements, catalog) -> route`
```
{"mode": "reuse_existing"|"generate_new"|None,
 "playerId": int|None, "reason": str,
 "selection": selection|None,              # select_model cho Player đã chọn (reuse)
 "alternatives": [{"playerId","name","reason"}],   # tối đa 3, chỉ từ catalog
 "conflicts": [Conflict], "questions": [{"field","text"}]}
```
Luật:
1. `gamePreference.playerId` có giá trị:
   - Không có trong `catalog.players` (không tồn tại hoặc không có quyền) → `mode=None`, conflict `forbidden_resource` với câu chung "Không thấy game này hoặc bạn không có quyền dùng" (không phân biệt hai trường hợp, không lộ tên/chủ), hỏi chọn game khác. **Không tự thay.**
   - Có: **giữ playerId**, `mode=reuse_existing`. Kiểm loại game (`conversation.game_kind(requirements)` khi có mô tả/tín hiệu, so với `describe_player`) và `select_model`. Không hợp → `conflicts` + `questions` (giữ game và đổi yêu cầu / chọn game khác), `alternatives` gợi ý Player hợp từ catalog; vẫn không đổi playerId.
2. `gamePreference.mode == "generate_new"` → `mode=generate_new`, `playerId=None`, lý do "giáo viên yêu cầu tạo game mới". (Chưa sinh HTML.)
3. `mode` `auto` hoặc `reuse_existing`, chưa chọn Player → lọc ứng viên: `gameKind` khớp loại cần (`conversation.game_kind`; `None` → chưa rõ: trả `questions` hỏi loại game, `mode=None`); `select_model` không `conflict`. Sắp xếp: `sample`/AI Lab và `approved` trước, rồi của mình, rồi `id`.
   - Có ứng viên → `reuse_existing`, `playerId` ứng viên đầu, `selection`, lý do nêu vì sao hợp (loại game, điều khiển).
   - Không có, `mode=auto` → `generate_new`, lý do liệt kê vì sao không game có sẵn nào hợp (vd "Quiz ABCD cần model ≥ 4 lớp image/pose; bạn chọn chỉ chuột").
   - Không có, `mode=reuse_existing` → `mode=None`, conflict + hỏi: cho phép tạo game mới / đổi yêu cầu. Không tự chuyển sang generate_new.

`Conflict = {"code", "message", "options": [str]}`.

## 4. Kiểm thử (`ailab/test_chatbot_catalog.py`)

Phần thuần: dùng catalog dựng tay. Phần `load_catalog` + `clean_app`: DB tạm riêng (gán `store.DB_PATH` trong `setUpClass`, khôi phục ở `tearDownClass`, như `test_chatbot_api.py`), tạo user/Player/Model bằng hàm `store`/SQL trên DB tạm.

| ID | Tình huống | Kỳ vọng | Map |
|---|---|---|---|
| C03-01 | `load_catalog` admin vs user thường vs user khác | Player draft/private của người khác và `hidden` không xuất hiện; model private người khác không xuất hiện; không có `html`/`url` | T07 |
| C03-02 | `describe_player` Quiz / Vòng quay / game exam không inputs | gameKind/needsModel/requiredCount đúng | — |
| C03-03 | Quiz ABCD + model image 4 lớp action | `selected`, mapping A–D đủ, đi qua `store.clean_app` thật | — |
| C03-04 | Quiz ABCD + chỉ có Bàn tay | `conflict` `incompatible_model` (kind hands không thuộc image/pose) | T08 |
| C03-05 | Game camera `kinds` có hands, 4 ô bắt buộc + Bàn tay | `conflict` thiếu lớp (2 action < 4) | T08 |
| C03-06 | `validate_mapping` lớp trùng / lớp không tồn tại / sai role / thiếu ô bắt buộc / key lạ | từng lỗi đúng mã, `ok=False` | T09 |
| C03-07 | `useModel=False` + Quiz camera | `conflict`, `modelId=None`, mapping rỗng | — |
| C03-08 | `useModel=False` + game không inputs | `not_needed` | — |
| C03-09 | `requestedKinds=["audio"]` | `conflict` `unsupported_interaction`; không chọn model audio dù có | T10 |
| C03-10 | `route_game` playerId không tồn tại / private người khác | `forbidden_resource`, cùng message, không tên; không thay playerId | T07 |
| C03-11 | `route_game` playerId Vòng quay nhưng yêu cầu game câu hỏi | giữ playerId, conflict + câu hỏi, alternatives từ catalog | T05 |
| C03-12 | Toán lớp 2, `useModel=False`, mode auto, catalog mặc định | `generate_new`, lý do nêu Quiz cần model | — |
| C03-13 | Như trên nhưng `mode=reuse_existing` | `mode=None`, conflict + hỏi, không tự generate | — |
| C03-14 | Vòng quay chọn tên, mode auto | `reuse_existing` Vòng quay, `not_needed` | — |
| C03-15 | Quiz + model image 4 lớp có sẵn, mode auto | `reuse_existing` Quiz, `selected` | — |
| C03-16 | `mode=generate_new` | `generate_new`, playerId None | — |
| C03-17 | Loại game chưa rõ (`game_kind` None) | `mode=None`, hỏi loại game | — |
| C03-18 | Hàm không sửa đầu vào (requirements, catalog, manifest) | dump trước/sau bằng nhau | — |
| C03-20 | Game không inputs + `useModel=False` + `requestedKinds=["hands"]` còn lưu | `not_needed`, `modelId=None`, mapping `{}`; game có inputs + `useModel=False` vẫn `conflict` | review C03 #1 |
| C03-21 | Ô tùy chọn `X` trùng key lớp `x` duy nhất, ô bắt buộc `A` cũng cần lớp đó | `A→x`, `X` trống; `validate_mapping` ok; `selected` | review C03 #2 |
| C03-22 | Ô `A` accepts action/rest, ô `B` chỉ action; lớp `act`(action), `rst`(rest) | `A→rst`, `B→act`; `validate_mapping` ok; qua `store.clean_app` thật | review C03 #2 |
| C03-23 | Trùng key vẫn ưu tiên khi không làm mất ghép đầy đủ (vd ô A/B, lớp `b`,`a` cùng role) | `A→a`, `B→b` | review C03 #2 |
| C03-24 | Thực sự không đủ lớp (3 ô bắt buộc action, 2 lớp action) | `conflict` thiếu lớp, không bịa lớp | T08 |
| C03-19 | Bộ test cũ | `python -m unittest discover -s ailab -p "test_*.py"` OK | — |

## 5. Ngoài phạm vi C03

Nối route/selection vào phương án và UI (I02), sinh HTML (C05), bộ đề (C04), runtime/sandbox (C06), AI thật.
