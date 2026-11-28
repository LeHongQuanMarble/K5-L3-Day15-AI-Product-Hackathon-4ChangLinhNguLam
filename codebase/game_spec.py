"""Phase 1 — Minimal Spec-driven GameSpec & Validator for Model-aware GENERATE.

GameSpec là hợp đồng trung gian ràng buộc cả Player Generator lẫn Validator (L1–L4):
- Không hardcode ID hay tên Model/Player/Exam; mọi tài nguyên đều resolve động từ `active_registry`.
- Tận dụng 100% Runtime Adapter sẵn có (`ailab/web/play.js` + `ailab/contract.py`) cho `hands` (21 điểm landmark
  `camera.hand` + `fist`/`open` `camera.result`), `image` và `pose` (Teachable Machine), cùng Mouse Fallback.
- Bảo toàn tuyệt đối public `ApplicationPlan` Contract v1.0.
"""
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, os.path.join(_ROOT, "ailab")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from chatbot import catalog as chatbot_catalog  # noqa: E402
import contract  # noqa: E402
import guardrails  # noqa: E402

_KEY_CLEAN_RE = re.compile(r"[^A-Za-z0-9_-]+")
_EXPLICIT_NEW_GAME_RE = re.compile(
    r"(?:"
    r"khong\s+(?:su\s+dung|dung)\s+(?:player|trinh\s+choi|game)\s+co\s+san"
    r"|khong\s+reuse"
    r"|(?:tao|thiet\s+ke|sinh|viet|xay\s+dung)\s+(?:mot\s+)?(?:tro\s+choi|game|mini\s*game|player|trinh\s+choi)\s+moi"
    r"|co\s+che\s+(?:choi\s+)?moi"
    r"|chua\s+co\s+trong\s+(?:thu\s+vien|catalog)"
    r")",
    re.I,
)


def is_explicit_new_game_request(user_msg: str) -> bool:
    """Nhận diện khi giáo viên yêu cầu rõ ràng tạo một trò chơi / cơ chế chơi MỚI (không ép về REUSE)."""
    folded = guardrails.fold_text(user_msg or "")
    return bool(_EXPLICIT_NEW_GAME_RE.search(folded))


def _sanitize_key(raw: str, fallback: str, used: set) -> str:
    folded = guardrails.fold_text(raw or "")
    key = _KEY_CLEAN_RE.sub("_", folded).strip("_")[:18] or fallback
    cand = key
    idx = 2
    while cand in used or not contract.KEY_RE.match(cand):
        cand = ("%s_%d" % (key[:14], idx))
        idx += 1
    used.add(cand)
    return cand


def derive_model_inputs_and_mapping(model_row: dict):
    """Dẫn xuất danh sách `inputs` chuẩn `jl-camera` và `mapping` từ `outputs` thật của `model_row`.

    Trả về `(inputs: list[dict], mapping: dict, uses_hand_landmarks: bool)`.
    """
    if not isinstance(model_row, dict):
        return [], {}, False
    kind = model_row.get("kind")
    outputs = [
        o for o in (model_row.get("outputs") or [])
        if isinstance(o, dict) and isinstance(o.get("key"), str) and o.get("key").strip()
    ]
    action_outs = [o for o in outputs if (o.get("role") or "action") == "action"]
    if not action_outs:
        action_outs = [o for o in outputs if (o.get("role") or "action") != "empty"]

    inputs = []
    mapping = {}
    used = set()

    if kind == "hands":
        keys_by_lower = {o["key"].lower(): o["key"] for o in action_outs}
        if "fist" in keys_by_lower:
            inputs.append({"key": "grab", "label": "Nắm tay chọn", "required": True, "accepts": ["action"]})
            mapping["grab"] = keys_by_lower["fist"]
            used.add("grab")
        if "open" in keys_by_lower:
            inputs.append({"key": "release", "label": "Xòe tay thả", "required": False, "accepts": ["action"]})
            mapping["release"] = keys_by_lower["open"]
            used.add("release")
        if not inputs:
            for idx, o in enumerate(action_outs[:4]):
                k = _sanitize_key(o["key"], "act_%d" % (idx + 1), used)
                inputs.append({"key": k, "label": o["key"][:40], "required": idx == 0, "accepts": ["action"]})
                mapping[k] = o["key"]
        return inputs, mapping, True

    # image / pose: ánh xạ trực tiếp từ các lớp action thật của model
    for idx, o in enumerate(action_outs[:8]):
        k = _sanitize_key(o["key"], "cls_%d" % (idx + 1), used)
        inputs.append({"key": k, "label": o["key"][:40], "required": idx < min(len(action_outs), 4), "accepts": ["action"]})
        mapping[k] = o["key"]
    return inputs, mapping, False


def build_game_spec(parsed: dict, req: dict, registry: dict, explicit_model=None, explicit_exam=None) -> dict:
    """Dựng GameSpec tối giản (12 trường bắt buộc) làm nguồn ràng buộc cho Generator và Validator."""
    user_msg = (req.get("message") or "").strip()
    game_idea = (parsed.get("game_idea") or user_msg).strip()
    title = (parsed.get("app_name") or "").strip()[:60] or "Trò chơi tương tác mới"
    exp_cnt = parsed.get("expected_question_count")
    if not isinstance(exp_cnt, int) or isinstance(exp_cnt, bool) or exp_cnt <= 0:
        # Thử bắt số câu hỏi người dùng nêu rõ (vd "gồm 5 câu hỏi")
        m_cnt = re.search(r"\b(\d{1,2})\s+cau\b", guardrails.fold_text(user_msg))
        exp_cnt = int(m_cnt.group(1)) if m_cnt and 1 <= int(m_cnt.group(1)) <= 50 else None

    model_caps = None
    inputs = []
    mapping = {}
    uses_landmarks = False
    if isinstance(explicit_model, dict):
        inputs, mapping, uses_landmarks = derive_model_inputs_and_mapping(explicit_model)
        model_caps = {
            "model_id": explicit_model["id"],
            "model_name": explicit_model.get("name", ""),
            "kind": explicit_model.get("kind"),
            "outputs": explicit_model.get("outputs") or [],
            "uses_hand_landmarks": uses_landmarks,
            "runtime_events": (
                ["camera.hand", "camera.result", "camera.frame", "camera.image"]
                if uses_landmarks
                else ["camera.result", "camera.frame", "camera.image"]
            ),
        }

    exam_mode = "reuse_existing" if explicit_exam is not None else "generate_new"
    exam_id = explicit_exam["id"] if explicit_exam is not None else None
    content_source = {
        "mode": exam_mode,
        "exam_id": exam_id,
        "exam_name": explicit_exam.get("name", "") if explicit_exam is not None else None,
        "questions_format": "exam",
    }

    return {
        "title": title,
        "learning_objective": user_msg[:200],
        "game_mechanic": game_idea[:240],
        "game_rules": (
            "Hiển thị câu hỏi động từ camera.init, người chơi tương tác bằng %s hoặc chuột/chạm/bàn phím để chọn đáp án; "
            "phản hồi đúng/sai ngay, có debounce tránh chọn lặp liên tục, tính điểm, chuyển câu, kết thúc gửi finish và có nút Chơi lại."
            % (model_caps["model_name"] if model_caps else "chuột/chạm/bàn phím")
        ),
        "game_states": ["ready", "playing", "feedback", "finished"],
        "scoring": {"correct_points": 1, "wrong_points": 0, "emit_finish": True},
        "model_capabilities": model_caps,
        "interaction_requirements": {
            "primary": model_caps["kind"] if model_caps else "mouse",
            "fallback": "mouse",
            "mouse_always_enabled": True,
            "uses_hand_landmarks": uses_landmarks,
            "inputs": inputs,
        },
        "input_mapping": mapping,
        "mouse_fallback": "Mọi thao tác chọn/hái/chỉ/kéo-thả bắt buộc hoạt động trọn vẹn bằng chuột, cảm ứng hoặc bàn phím khi không có camera.",
        "content_source": content_source,
        "question_requirements": {
            "needs_exam": True,
            "expected_count": exp_cnt,
            "format": "AI Lab pipe syntax (Câu hỏi | A | B | ... | =A hoặc Câu hỏi | =Đúng/=Sai)",
        },
        "acceptance_conditions": [
            "Manifest jl-camera hợp lệ, không xung đột exam/texts",
            "0 cờ an toàn (contract.scan == [])",
            "Khởi tạo động từ camera.init và gửi ready",
            "Chơi được bằng chuột/chạm/phím và bằng event Model (nếu có Model)",
            "Có chấm điểm, phản hồi đúng/sai, kết thúc (finish) và nút Chơi lại (Reset)",
        ],
    }


def validate_game_spec(spec: dict, registry: dict = None) -> list:
    """Kiểm tra GameSpec theo L1/L2 trước khi sinh HTML. Trả về danh sách lỗi (rỗng = hợp lệ)."""
    errors = []
    if not isinstance(spec, dict):
        return ["GameSpec phải là dict."]
    inter = spec.get("interaction_requirements") or {}
    if inter.get("mouse_always_enabled") is not True or inter.get("fallback") != "mouse":
        errors.append("GameSpec bắt buộc bật Mouse Fallback (mouse_always_enabled=true, fallback='mouse').")

    mc = spec.get("model_capabilities")
    if mc is not None:
        kind = mc.get("kind")
        if kind not in chatbot_catalog.RUNTIME_KINDS:
            errors.append("Runtime hiện chưa hỗ trợ model loại '%s' (chỉ hỗ trợ %s)." % (kind, ", ".join(chatbot_catalog.RUNTIME_KINDS)))
        inputs = inter.get("inputs") or []
        mapping = spec.get("input_mapping") or {}
        if not inputs:
            errors.append("GameSpec có Model nhưng thiếu danh sách inputs.")
        else:
            synth_man = {
                "name": spec.get("title") or "Draft",
                "description": "",
                "kinds": [kind],
                "inputs": inputs,
                "questions": "exam",
            }
            model_obj = {
                "id": mc.get("model_id"),
                "name": mc.get("model_name") or "",
                "kind": kind,
                "outputs": mc.get("outputs") or [],
            }
            if registry is not None:
                reg_m = next((m for m in (registry.get("models") or []) if m.get("id") == mc.get("model_id")), None)
                if reg_m is None:
                    errors.append("Model #%s không tồn tại trong registry được cấp quyền." % mc.get("model_id"))
            mcheck = chatbot_catalog.validate_mapping(synth_man, model_obj, mapping)
            if not mcheck.get("ok"):
                errors.extend(e.get("message", "Mapping không hợp lệ.") for e in (mcheck.get("errors") or []))

    cs = spec.get("content_source") or {}
    if cs.get("mode") == "reuse_existing" and registry is not None:
        eid = cs.get("exam_id")
        if not any(e.get("id") == eid for e in (registry.get("exams") or [])):
            errors.append("Exam #%s không tồn tại trong registry được cấp quyền." % eid)
    return errors


def validate_html_against_spec(html: str, spec: dict) -> list:
    """Kiểm tra HTML do LLM sinh ra có tuân thủ chặt GameSpec (manifest kinds/inputs/questions & hand protocol)."""
    errors = []
    man, err = contract.parse(html or "")
    if err:
        return ["HTML sai hợp đồng jl-camera: %s" % err[1]]
    mc = spec.get("model_capabilities")
    inter = spec.get("interaction_requirements") or {}
    if mc is not None:
        kind = mc.get("kind")
        if "inputs" not in man:
            errors.append("GameSpec yêu cầu gắn Model '%s' nhưng manifest HTML thiếu trường 'inputs'." % mc.get("model_name"))
        else:
            if kind not in (man.get("kinds") or []):
                errors.append("Manifest HTML thiếu kind='%s' trong trường 'kinds'." % kind)
            mapped_keys = set((spec.get("input_mapping") or {}).keys())
            expected_keys = {i["key"] for i in (inter.get("inputs") or []) if i.get("required")} | mapped_keys
            actual_keys = {i.get("key") for i in (man.get("inputs") or []) if isinstance(i, dict)}
            missing = sorted(expected_keys - actual_keys)
            if missing:
                errors.append("Manifest HTML thiếu input bắt buộc/đã ánh xạ theo GameSpec: %s." % ", ".join(missing))
            # Kiểm tra mapping thật trên manifest vừa sinh
            mcheck = chatbot_catalog.validate_mapping(man, {"id": mc.get("model_id"), "name": mc.get("model_name"), "kind": kind, "outputs": mc.get("outputs") or []}, spec.get("input_mapping") or {})
            if not mcheck.get("ok"):
                errors.extend(e.get("message", "Mapping không khớp manifest sinh mới.") for e in (mcheck.get("errors") or []))
        if mc.get("uses_hand_landmarks"):
            js_blocks = [
                (m.group("body") or "")
                for m in guardrails._SCRIPT_BLOCK_RE.finditer(html or "")
                if "application/json" not in (m.group("attrs") or "").lower()
            ]
            js_text = "\n".join(js_blocks)
            if "camera.hand" not in js_text or "'hands'" not in js_text.replace('"', "'") or ".hands" not in js_text:
                errors.append("Game dùng MediaPipe Hands phải gửi {type:'hands', on:true} và đọc dữ liệu landmark từ 'd.hands' trong 'camera.hand'.")
    if (spec.get("question_requirements") or {}).get("needs_exam"):
        if man.get("questions") != "exam":
            errors.append("GameSpec yêu cầu bộ câu hỏi nhưng manifest HTML thiếu '\"questions\": \"exam\"'.")
    return errors


def format_game_spec_for_generator(spec: dict) -> str:
    """Biên dịch GameSpec thành chỉ thị kỹ thuật rõ ràng + hợp đồng runtime `play.js` cho Player Generator."""
    mc = spec.get("model_capabilities")
    inter = spec.get("interaction_requirements") or {}
    lines = [
        "=== GAMESPEC BẮT BUỘC TUÂN THỦ ===",
        "- Tên game: %s" % spec.get("title"),
        "- Mục tiêu học tập: %s" % spec.get("learning_objective"),
        "- Cơ chế chơi (game_mechanic): %s" % spec.get("game_mechanic"),
        "- Luật chơi & vòng đời: %s" % spec.get("game_rules"),
        "- Mouse Fallback: %s" % spec.get("mouse_fallback"),
    ]
    if mc is not None:
        manifest_hint = {
            "name": spec.get("title", "Game mới")[:60],
            "description": spec.get("game_mechanic", "")[:120],
            "kinds": [mc["kind"]],
            "inputs": inter.get("inputs") or [],
            "questions": "exam",
        }
        lines.extend([
            "- MODEL GẮN KÈM: \"%s\" (kind=%s) · Ánh xạ lớp: %s"
            % (mc.get("model_name"), mc.get("kind"), json.dumps(spec.get("input_mapping") or {}, ensure_ascii=False)),
            "- KHỐI <script type=\"application/json\" id=\"jl-camera\"> PHẢI KHỚP CHÍNH XÁC CẤU TRÚC SAU:",
            json.dumps(manifest_hint, ensure_ascii=False),
            "- HỢP ĐỒNG RUNTIME ADAPTER (ailab/web/play.js — KHÔNG tự gọi getUserMedia hay tải MediaPipe/TFJS):",
            "  * Đặt <div data-jl-camera></div> để hiển thị khung camera gương nhỏ ở góc.",
            "  * Lắng nghe `window.addEventListener('message', e => { if (!e.data || e.source !== parent) return; ... })`:",
            "    - `camera.init`: nạp `d.questions` (mảng `{id, type, text, choices:[{key, text}], answer}`) và vẽ lại game sạch trạng thái.",
            "    - `camera.result`: nhận `{input, label, confidence}` khi giữ cử chỉ đủ lâu (debounce sẵn).",
            "    - `camera.frame`: nhận `{scores}` liên tục mỗi 120ms.",
        ])
        if mc.get("uses_hand_landmarks"):
            lines.extend([
                "    - `camera.hand`: BẮT BUỘC gửi `parent.postMessage({type:'hands', on:true}, '*')` ngay sau `ready`!",
                "      Runtime sẽ gửi `{type:'camera.hand', hands:[[{x,y,z}x21]], available:true}` (tọa độ x,y chuẩn hóa 0..1 đã lật gương).",
                "      Đầu ngón trỏ là `lm[8]` (`{x, y}`), tâm lòng bàn tay là `lm[9]` (`{x, y}`).",
                "      Dùng `lm[8]` hoặc `lm[9]` để di chuyển con trỏ/giỏ trên màn hình; dùng `camera.result` (`d.input === 'grab'`) HOẶC giữ con trỏ trên mục tiêu đủ ~600ms (kèm khóa cooldown / đổi trạng thái để KHÔNG tự chọn liên tục khi tay đứng yên!).",
            ])
    else:
        manifest_hint = {
            "name": spec.get("title", "Game mới")[:60],
            "description": spec.get("game_mechanic", "")[:120],
            "questions": "exam",
        }
        lines.extend([
            "- CHẾ ĐỘ CHUỘT / CẢM ỨNG / BÀN PHÍM (không gắn Model, KHÔNG khai `inputs` trong `#jl-camera`):",
            json.dumps(manifest_hint, ensure_ascii=False),
        ])
    lines.extend([
        "- KẾT THÚC & CHƠI LẠI:",
        "  * Khi trả lời xong tất cả câu hỏi: hiện màn hình kết quả + gửi `parent.postMessage({type:'finish', correct: score, total: total}, '*')`.",
        "  * BẮT BUỘC có nút 'Chơi lại' (Reset) xóa sạch điểm, chỉ số câu, trạng thái đã chọn và khởi động lại ván mới.",
        "  * Hiển thị chữ bằng `textContent` an toàn (tránh XSS), bố cục gọn đẹp, nút to rõ, có dữ liệu demo dự phòng nếu chưa nhận `camera.init`.",
    ])
    return "\n".join(lines)
