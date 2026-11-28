"""Real AI UAT chấp nhận cho blocker GENERATE (P0) — CHẤP NHẬN CHẠY KHI CÓ --confirm-paid.

Mục đích: chứng minh luồng Chat → GENERATE (player MỚI, model thật) → Preview → HITL Publish
→ Play → Reload hoạt động với model AI thật (không mock, không REUSE giả GENERATE).

Chạy (cần .env có MODEL_PROVIDER/API_KEY thật và server đang chạy):
    python ailab/accept_real_ai_uat.py --confirm-paid            # cả TC02 + TC01
    python ailab/accept_real_ai_uat.py --confirm-paid --cases tc02

Kiểm chứng ở đây là STATIC + PROTOCOL (srcdoc/manifest/mapping/questions/persistence).
Tương tác camera/media THẬT (landmark, chỉ tay, micro) là phần Human UAT của PM — không đánh PASS thay.

Exit code 0 = mọi case PASS. Không ghi vào DB catalog, không sửa benchmark/eval.
"""
import argparse
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8800"

TC02_PROMPT = (
    "Tạo một trò chơi mới chọn đáp án bằng cách chỉ ngón tay vào một trong bốn hành tinh trên màn hình. "
    "Chủ đề hệ Mặt Trời lớp 5, gồm 4 câu hỏi mới. Dùng MediaPipe Hands và chuột dự phòng."
)
TC01_PROMPT = (
    "Tạo một trò chơi mới thu hoạch táo ôn tập phép nhân lớp 3 gồm 5 câu hỏi mới. "
    "Học sinh di chuyển bàn tay để chọn quả táo mang đáp án đúng, nắm tay để hái và có chuột dự phòng. "
    "Sử dụng Model Bàn tay MediaPipe có sẵn. Không sử dụng Player có sẵn."
)

CASES = {
    "tc02": {"prompt": TC02_PROMPT, "questions": 4, "name_hint": "hành tinh"},
    "tc01": {"prompt": TC01_PROMPT, "questions": 5, "name_hint": "táo"},
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
        with self.opener.open(req, timeout=timeout) as r:
            payload = json.loads(r.read().decode("utf-8"))
        payload["_ms"] = int((time.time() - t0) * 1000)
        return payload


def collect_tokens(obj):
    """Đi toàn bộ trace/steps, cộng dồn tokens_in/tokens_out tìm thấy (không ước lượng)."""
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
    out = {"case": key.upper(), "checks": [], "ok": True}

    def check(label, cond, detail=""):
        out["checks"].append({"check": label, "ok": bool(cond), "detail": str(detail)[:300]})
        if not cond:
            out["ok"] = False

    # 1) Chat → /api/agent (Real AI)
    res = cl.call("POST", "/api/agent", {"text": cfg["prompt"]})
    check("decision == GENERATE", res.get("decision") == "GENERATE", res.get("decision"))
    check("draft_id được cấp", isinstance(res.get("draft_id"), int) and res["draft_id"] > 0, res.get("draft_id"))
    check("plan_hash được cấp", bool(res.get("plan_hash")))

    plan = res.get("application_plan") or {}
    player = plan.get("player") or {}
    model = plan.get("model") or {}
    exam = plan.get("exam") or {}
    check("player.mode == generate_new (không REUSE)", player.get("mode") == "generate_new", player.get("mode"))
    check("player.player_id is None (player MỚI)", player.get("player_id") is None, player.get("player_id"))
    check("model.kind == hands", model.get("kind") == "hands", model.get("kind"))
    check("model gắn model_id thật", isinstance(model.get("model_id"), int), model.get("model_id"))
    check("mapping có grab/open", isinstance(model.get("mapping"), dict) and "grab" in model.get("mapping", {}), model.get("mapping"))
    check("interaction.primary == hands", (plan.get("interaction") or {}).get("primary") == "hands", (plan.get("interaction") or {}).get("primary"))
    check("mouse_always_enabled", (plan.get("interaction") or {}).get("mouse_always_enabled") is True)
    check("exam mode generate_new", exam.get("mode") == "generate_new", exam.get("mode"))
    check("safety_flags == []", res.get("safety_flags") == [], res.get("safety_flags"))

    # 2) Preview (sandbox srcdoc)
    prev = cl.call("GET", res.get("preview_url") or "")
    src = prev.get("srcdoc") or ""
    check("preview 200 có srcdoc", len(src) > 200, len(src))
    check("srcdoc có CSP", "Content-Security-Policy" in src)
    check("srcdoc có manifest jl-camera", 'id="jl-camera"' in src)
    check("srcdoc có Runtime Wrapper", "window.JLRuntime" in src)
    check("srcdoc gửi hands-on khi cần", "type: 'hands', on: true" in src)
    check("srcdoc có ô camera", "data-jl-camera" in src)
    man_prev = prev.get("manifest") if isinstance(prev.get("manifest"), dict) else {}
    check("srcdoc manifest kinds chứa hands", "hands" in (man_prev.get("kinds") or []), man_prev.get("kinds"))
    sample = prev.get("sampleQuestions") or []
    check("preview có đúng số câu mẫu (%d)" % cfg["questions"], len(sample) == cfg["questions"], len(sample))

    # 3) HITL Publish
    pub = cl.call("POST", "/api/agent/publish", {
        "draft_id": res["draft_id"], "plan_hash": res["plan_hash"],
        "approved": True, "reviewed_knowledge": True,
    })
    check("publish 200 có app_id", isinstance(pub.get("app_id"), int) and pub["app_id"] > 0, pub.get("app_id") or pub.get("message"))
    check("publish share == 0 (private, không tự public)", pub.get("share") == 0, pub.get("share"))
    app_id = pub.get("app_id") or 0

    # 4) Play + Reload (persistence)
    play1 = cl.call("GET", "/api/apps/%d/play" % app_id)
    play2 = cl.call("GET", "/api/apps/%d/play" % app_id)
    check("play 200 có srcdoc", len(play1.get("srcdoc") or "") > 200)
    check("play model.kind == hands", (play1.get("model") or {}).get("kind") == "hands", (play1.get("model") or {}).get("kind"))
    check("play mapping giữ nguyên sau publish", play1.get("mapping") == model.get("mapping"), play1.get("mapping"))
    check("play có đúng số câu (%d)" % cfg["questions"], len(play1.get("questions") or []) == cfg["questions"], len(play1.get("questions") or []))
    check("reload (lần GET play thứ 2) nhất quán", len(play2.get("srcdoc") or "") == len(play1.get("srcdoc") or ""))

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
    ap.add_argument("--cases", default="tc02,tc01")
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

    tot_in = sum(r["usage"]["tokens_in"] for r in results)
    tot_out = sum(r["usage"]["tokens_out"] for r in results)
    print("\nTỔNG TOKEN (từ usage API, không ước lượng): in=%d out=%d" % (tot_in, tot_out))
    print("KẾT LUẬN:", "PASS — sẵn sàng UAT camera thật của PM" if all_ok else "FAIL — phân tích nguyên nhân trước khi retry")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
