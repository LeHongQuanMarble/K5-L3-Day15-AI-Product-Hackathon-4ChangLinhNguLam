"""Real AI UAT chấp nhận Model-aware GENERATE — CHẤP NHẬN CHẠY KHI CÓ --confirm-paid.

Mục đích: chứng minh giáo viên có thể yêu cầu AI tạo Player MỚI với từng Model thật của team
(Lái Xe pose / Âm thanh ABCD audio / Bàn tay MediaPipe hands) — không REUSE giả GENERATE,
không rơi về mouse-only, chạy trọn luồng Chat → GENERATE → Preview → HITL → Publish → Play → Reload.

Chạy (cần server đang chạy với .env Real AI; audio case cần AILAB_ENABLE_AUDIO=1 khi khởi động server):
    python ailab/accept_real_ai_uat.py --confirm-paid --cases driving,audio,hands

Mức kiểm chứng: STATIC + PROTOCOL (srcdoc/manifest/mapping/số câu/persistence).
Inference camera/microphone THẬT là phần Human UAT của PM — script không đánh PASS thay.
"""
import argparse
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8800"

CASES = {
    "driving": {
        "prompt": (
            "Tạo một trò chơi mới đua xe chọn làn dùng Model \"Lái Xe\": học sinh nghiêng người trái/phải "
            "để xe chạy vào làn chứa đáp án đúng, nút Nitro tăng tốc sau khi chọn. "
            "Chủ đề phép nhân lớp 3, gồm 4 câu hỏi mới. Có chuột dự phòng."
        ),
        "kind": "pose", "questions": 4, "model_name": "Lái Xe",
    },
    "audio": {
        "prompt": (
            "Tạo một trò chơi mới chủ đề Hệ Mặt Trời gồm 4 câu hỏi mới: học sinh phát âm A, B, C, D vào micro "
            "dùng Model \"Âm thanh A B C D\" để chọn đáp án. Có chuột dự phòng."
        ),
        "kind": "audio", "questions": 4, "model_name": "Âm thanh A B C D",
    },
    "hands": {
        "prompt": (
            "Tạo một trò chơi mới thu hoạch táo ôn tập phép nhân lớp 3 gồm 5 câu hỏi mới. "
            "Học sinh di chuyển bàn tay để chọn quả táo mang đáp án đúng, nắm tay để hái và có chuột dự phòng. "
            "Sử dụng Model Bàn tay MediaPipe có sẵn. Không sử dụng Player có sẵn."
        ),
        "kind": "hands", "questions": 5, "model_name": "Bàn tay (MediaPipe)",
    },
    "mouse": {
        "prompt": (
            "Tạo một trò chơi mới kéo thả phân loại động vật có xương sống và không xương sống gồm 4 câu hỏi mới, "
            "chơi bằng chuột. Game cần có sinh động: ổ động vật, hiệu ứng kéo thả, phản hồi đúng sai vui mắt."
        ),
        "kind": None, "questions": 4, "model_name": None,  # mouse-only: không gắn model
    },
}


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def call(self, method, path, body=None, timeout=300):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(BASE + path, data=data, method=method)
        if data:
            req.add_header("Content-Type", "application/json")
        t0 = time.time()
        try:
            with self.opener.open(req, timeout=timeout) as r:
                raw = r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return {"_http_error": e.code, "_ms": 0, "message": "HTTP %s" % e.code}
        try:
            payload = json.loads(raw)
        except ValueError:
            return {"_http_error": 200, "_non_json": True, "_ms": 0, "message": "phản hồi không phải JSON (%d bytes)" % len(raw)}
        payload["_ms"] = int((time.time() - t0) * 1000)
        return payload


def collect_tokens(obj):
    """Đi toàn bộ trace/steps, cộng dồn tokens_in/tokens_out + số lần gọi model (không ước lượng)."""
    total = {"tokens_in": 0, "tokens_out": 0, "calls": 0}
    if isinstance(obj, dict):
        ti, to = obj.get("tokens_in"), obj.get("tokens_out")
        if isinstance(ti, int) and isinstance(to, int):
            total["tokens_in"] += ti
            total["tokens_out"] += to
            total["calls"] += 1
        for v in obj.values():
            for k2, v2 in collect_tokens(v).items():
                total[k2] += v2
    elif isinstance(obj, list):
        for v in obj:
            for k2, v2 in collect_tokens(v).items():
                total[k2] += v2
    return total


def run_case(cl, key, cfg, results):
    out = {"case": key, "checks": [], "ok": True}

    def check(label, cond, detail=""):
        out["checks"].append({"check": label, "ok": bool(cond), "detail": str(detail)[:300]})
        if not cond:
            out["ok"] = False

    res = cl.call("POST", "/api/agent", {"text": cfg["prompt"]})
    check("decision == GENERATE", res.get("decision") == "GENERATE", res.get("decision"))
    check("draft_id được cấp", isinstance(res.get("draft_id"), int) and res["draft_id"] > 0, res.get("draft_id"))
    if not res.get("draft_id"):
        # Không có nháp: dừng case, in lý do thật từ envelope để phân tích nguyên nhân
        out["reason"] = res.get("message") or res.get("error") or json.dumps({k: res.get(k) for k in ("decision", "errors")}, ensure_ascii=False)
        out["usage"] = collect_tokens(res.get("trace"))
        results.append(out)
        return False
    check("plan_hash được cấp", bool(res.get("plan_hash")))

    plan = res.get("application_plan") or {}
    player = plan.get("player") or {}
    model = plan.get("model") or {}
    exam = plan.get("exam") or {}
    kind = cfg.get("kind")
    check("player.mode == generate_new (không REUSE)", player.get("mode") == "generate_new", player.get("mode"))
    check("player.player_id is None (player MỚI)", player.get("player_id") is None, player.get("player_id"))
    if kind:
        check('model.kind == "%s"' % kind, model.get("kind") == kind, model.get("kind"))
        check("model gắn model_id thật", isinstance(model.get("model_id"), int), model.get("model_id"))
        check("mapping không rỗng", isinstance(model.get("mapping"), dict) and len(model.get("mapping") or {}) > 0, model.get("mapping"))
        check('interaction.primary == "%s"' % kind, (plan.get("interaction") or {}).get("primary") == kind, (plan.get("interaction") or {}).get("primary"))
    else:
        # mouse-only: KHÔNG gắn model, KHÔNG bị ép vào template cố định
        check("mouse-only: model là None", model in (None, {}) or model.get("kind") in (None, "mouse"), model)
        check("mouse-only: interaction.primary == mouse", (plan.get("interaction") or {}).get("primary") == "mouse", (plan.get("interaction") or {}).get("primary"))
    check("mouse_always_enabled", (plan.get("interaction") or {}).get("mouse_always_enabled") is True)
    check("exam mode generate_new", exam.get("mode") == "generate_new", exam.get("mode"))
    check("safety_flags == []", res.get("safety_flags") == [], res.get("safety_flags"))

    prev = cl.call("GET", res.get("preview_url") or "")
    src = prev.get("srcdoc") or ""
    check("preview 200 có srcdoc", len(src) > 200, len(src))
    check("srcdoc có CSP", "Content-Security-Policy" in src)
    check("srcdoc có manifest jl-camera", 'id="jl-camera"' in src)
    if kind:
        check("srcdoc có Runtime Wrapper", "window.JLRuntime" in src)
    cam_attr = len(__import__("re").findall(r"(?<=\s)data-jl-camera(?=[\s=><])", src))
    check("srcdoc có đúng 1 ô camera (attribute)", cam_attr == (1 if kind else 0), cam_attr)
    man_prev = prev.get("manifest") if isinstance(prev.get("manifest"), dict) else {}
    if kind:
        check("manifest kinds chứa %s" % kind, kind in (man_prev.get("kinds") or []), man_prev.get("kinds"))
    if kind == "hands":
        check("srcdoc gửi hands-on handshake", "type: 'hands', on: true" in src and "var USES_HANDS = true;" in src)
    elif kind and "window.JLRuntime" in src:
        check("không gửi hands-on cho kind %s" % kind, "var USES_HANDS = false;" in src)
    sample = prev.get("sampleQuestions") or []
    check("preview đúng số câu mẫu (%d)" % cfg["questions"], len(sample) == cfg["questions"], len(sample))

    pub = cl.call("POST", "/api/agent/publish", {
        "draft_id": res["draft_id"], "plan_hash": res["plan_hash"],
        "approved": True, "reviewed_knowledge": True,
    })
    check("publish 200 có app_id", isinstance(pub.get("app_id"), int) and pub["app_id"] > 0, pub.get("app_id") or pub.get("message"))
    check("publish share == 0 (private, không tự public)", pub.get("share") == 0, pub.get("share"))
    app_id = pub.get("app_id") or 0

    play1 = cl.call("GET", "/api/apps/%d/play" % app_id)
    play2 = cl.call("GET", "/api/apps/%d/play" % app_id)
    check("play 200 có srcdoc", len(play1.get("srcdoc") or "") > 200)
    check("play model.kind == %s" % kind, (play1.get("model") or {}).get("kind") == kind, (play1.get("model") or {}).get("kind"))
    check("play mapping giữ nguyên sau publish", play1.get("mapping") == model.get("mapping"), play1.get("mapping"))
    check("play đúng số câu (%d)" % cfg["questions"], len(play1.get("questions") or []) == cfg["questions"], len(play1.get("questions") or []))
    check("reload (GET play lần 2) nhất quán", len(play2.get("srcdoc") or "") == len(play1.get("srcdoc") or ""))

    out["app_id"] = app_id
    out["draft_id"] = res.get("draft_id")
    out["usage"] = collect_tokens(res.get("trace"))
    out["ms"] = res.get("_ms")
    results.append(out)
    return out["ok"]


def main():
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm-paid", action="store_true", help="Xác nhận chạy API TRẢ PHÍ (bắt buộc)")
    ap.add_argument("--cases", default="driving,audio,hands")
    ap.add_argument("--base", default=BASE)
    args = ap.parse_args()
    if not args.confirm_paid:
        print("TỪ CHỐI: cần --confirm-paid vì script này gọi API trả phí.")
        return 2
    BASE = args.base.rstrip("/")

    cl = Client()
    user = "uat_real_%d" % int(time.time())
    reg = cl.call("POST", "/api/register", {"username": user, "password": "UatPassword123!"})
    if reg.get("error"):
        print("Đăng ký thất bại:", reg)
        return 2

    results = []
    all_ok = True
    for key in [k.strip().lower() for k in args.cases.split(",") if k.strip()]:
        t0 = time.time()
        ok = run_case(cl, key, CASES[key], results)
        all_ok = all_ok and ok
        print("== %s: %s (%.1fs) ==" % (key.upper(), "PASS" if ok else "FAIL", time.time() - t0))
        for c in results[-1]["checks"]:
            print("  [%s] %s%s" % ("OK " if c["ok"] else "SAI", c["check"], (" — " + c["detail"]) if (not c["ok"] and c["detail"]) else ""))
        if not ok and results[-1].get("reason"):
            print("  LÝ DO ENVELOPE: %s" % results[-1]["reason"][:500])

    tot_in = sum(r["usage"]["tokens_in"] for r in results)
    tot_out = sum(r["usage"]["tokens_out"] for r in results)
    tot_calls = sum(r["usage"]["calls"] for r in results)
    print("\nTỔNG TOKEN (usage API thật): in=%d out=%d | lượt gọi model=%d" % (tot_in, tot_out, tot_calls))
    print("KẾT LUẬN:", "PASS — sẵn sàng UAT camera/micro thật của PM" if all_ok else "FAIL — phân tích nguyên nhân trước khi retry")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
