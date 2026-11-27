"""I01 - kiểm tra trình duyệt thật (Chrome headless + CDP tự viết bằng thư viện chuẩn).
Chạy: python evidence/chatbot/I01/browser_check.py   (từ thư mục gốc repo). Ghi PNG + RESULTS.md cạnh file này.
"""
import base64, json, os, socket, struct, subprocess, sys, tempfile, time, urllib.request, datetime, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PASSWORD = "password-test-123"  # mật khẩu giả cho DB tạm
TMP = tempfile.mkdtemp(prefix="i01_browser_")


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


class WS:
    def __init__(self, url):
        assert url.startswith("ws://")
        hostport, path = url[5:].split("/", 1)
        host, port = hostport.split(":")
        self.s = socket.create_connection((host, int(port)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(("GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (path, hostport, key)).encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(1)
        assert b" 101 " in buf.split(b"\r\n")[0], buf
        self.id = 0
        self.events = []
        self.on_event = None

    def _rx(self, n):
        b = b""
        while len(b) < n:
            c = self.s.recv(n - len(b))
            if not c:
                raise EOFError
            b += c
        return b

    def _frame(self):
        msg = b""
        while True:
            b1, b2 = self._rx(2)
            ln = b2 & 0x7F
            if ln == 126: ln = struct.unpack(">H", self._rx(2))[0]
            elif ln == 127: ln = struct.unpack(">Q", self._rx(8))[0]
            data = self._rx(ln)
            op = b1 & 0x0F
            if op == 8: raise EOFError
            if op in (9, 10): continue
            msg += data
            if b1 & 0x80: return msg.decode("utf-8")

    def send(self, obj):
        data = json.dumps(obj).encode()
        mask = os.urandom(4)
        n = len(data)
        hdr = bytes([0x81])
        if n < 126: hdr += bytes([0x80 | n])
        elif n < 65536: hdr += bytes([0x80 | 126]) + struct.pack(">H", n)
        else: hdr += bytes([0x80 | 127]) + struct.pack(">Q", n)
        self.s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def call(self, method, params=None, timeout=30):
        self.id += 1
        mid = self.id
        self.send({"id": mid, "method": method, "params": params or {}})
        end = time.time() + timeout
        self.s.settimeout(timeout)
        while time.time() < end:
            m = json.loads(self._frame())
            if m.get("id") == mid:
                if "error" in m: raise RuntimeError(m["error"])
                return m.get("result", {})
            if "method" in m:
                self.events.append(m)
                if self.on_event: self.on_event(m)
        raise TimeoutError(method)

    def pump(self, secs=0.2):
        self.s.settimeout(secs)
        try:
            while True:
                m = json.loads(self._frame())
                if "method" in m:
                    self.events.append(m)
                    if self.on_event: self.on_event(m)
        except (socket.timeout, TimeoutError):
            pass


class Browser:
    def __init__(self, ws):
        self.ws = ws

    def js(self, expr):
        r = self.ws.call("Runtime.evaluate", {"expression": expr, "awaitPromise": True, "returnByValue": True})
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"].get("text", "") + str(r["exceptionDetails"].get("exception", {}).get("description", "")))
        return r["result"].get("value")

    def wait(self, expr, timeout=15):
        end = time.time() + timeout
        while time.time() < end:
            try:
                v = self.js('!!(' + expr + ')')
                if v: return v
            except Exception:
                pass
            time.sleep(0.25)
        return False

    def shot(self, name):
        r = self.ws.call("Page.captureScreenshot", {"format": "png"})
        with open(os.path.join(HERE, name), "wb") as f:
            f.write(base64.b64decode(r["data"]))

    def nav(self, url):
        self.ws.call("Page.navigate", {"url": url})
        time.sleep(0.8)


def click_text(txt):
    return ("(()=>{var b=[...document.querySelectorAll('[data-chatbot-v2] button')].find(x=>x.textContent.indexOf(%s)>=0&&!x.disabled);"
            "if(!b)return false;b.click();return true})()" % json.dumps(txt, ensure_ascii=False))


LOG = "(document.querySelector('[data-chatbot-v2] .msgs')||{}).innerText||''"
results = []
FRESH = [0]


def step(n, title, ok, img, note=""):
    results.append((n, title, "PASS" if ok else "FAIL", img, note))
    print("%s  %s  %s %s" % ("PASS" if ok else "FAIL", n, title, note))


def send_msg(b, text, expect):
    ok = b.js("(()=>{var t=document.querySelector('[data-chatbot-v2] textarea');t.value=%s;"
              "[...document.querySelectorAll('[data-chatbot-v2] button')].find(x=>x.textContent.trim()==='Gửi').click();return true})()"
              % json.dumps(text, ensure_ascii=False))
    return ok and b.wait("(()=>{var t=%s;return %s})()" % (LOG, expect), 20)


def base_steps(b, ws, base):
    # 1
    b.nav(base + "/")
    b.wait("document.querySelector('form.ail-form')")
    r = b.js("fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'hocsinh01',password:%s})}).then(r=>r.status)" % json.dumps(PASSWORD))
    b.nav(base + "/#/models"); ws.call("Page.reload")
    ok = b.wait("document.querySelector('a[href=\"#/chat\"]')")
    b.shot("01_login.png")
    step(1, "Mở /, đăng ký bằng fetch('/api/register') rồi reload (không qua form) -> thấy thanh tab", ok and r == 200, "01_login.png", "register status %s" % r)
    # 2
    b.js("document.querySelector('a[href=\"#/chat\"]').click()")
    ok = b.wait("document.querySelector('[data-chatbot-v2]')")
    b.shot("02_chat_tab.png")
    step(2, "Bấm tab Trợ lý game -> có [data-chatbot-v2]", ok, "02_chat_tab.png")
    # 3
    ok = send_msg(b, "Tạo game ôn toán", "t.indexOf('Cần làm rõ thêm')>=0 && t.indexOf('Chế độ giả')>=0")
    txt = b.js(LOG); b.shot("03_clarify1.png")
    step(3, "Gửi 'Tạo game ôn toán' -> câu hỏi bổ sung + nhãn chế độ giả", ok and "lớp" in txt.lower(), "03_clarify1.png")
    # 4
    ok = send_msg(b, "lớp 2", "t.split('Chế độ giả').length>=3 && t.indexOf('Cần làm rõ thêm')>=0")
    qs = b.js("[...document.querySelectorAll('[data-chatbot-v2] .msgs li')].map(x=>x.textContent)")
    b.shot("04_clarify2.png")
    step(4, "'lớp 2' -> chỉ hỏi chủ đề", ok and len(qs) == 1 and "lớp" not in qs[0].lower(), "04_clarify2.png", "câu hỏi còn lại: %s" % qs)
    # 5
    ok = send_msg(b, "phép cộng có nhớ, 10 câu", "t.indexOf('Phương án (phiên bản 1)')>=0")
    btns = b.js("[...document.querySelectorAll('[data-chatbot-v2] button')].map(x=>x.textContent)")
    b.shot("05_plan_v1.png")
    step(5, "Thẻ phương án phiên bản 1 + nút Xác nhận/Hủy", ok and any("Xác nhận phương án (phiên bản 1)" in x for x in btns) and "Hủy phương án" in btns, "05_plan_v1.png")
    # 6
    ws.call("Page.reload")
    ok = b.wait("(()=>{var t=%s;return t.indexOf('Phương án (phiên bản 1)')>=0})()" % LOG)
    h = b.js("location.hash"); txt = b.js(LOG)
    b.shot("06_reload.png")
    step(6, "Reload -> hash #/chat/<id>, đủ tin nhắn + thẻ phương án v1", ok and h.startswith("#/chat/") and all(k in txt for k in ("Tạo game ôn toán", "lớp 2", "phép cộng có nhớ")), "06_reload.png", "hash=%s" % h)
    # 7
    b.js(click_text("Xác nhận phương án"))
    ok = b.wait("(()=>{var t=%s;return t.indexOf('Đã xác nhận')>=0})()" % LOG)
    b.shot("07_confirmed.png")
    step(7, "Bấm Xác nhận -> trạng thái đã xác nhận", ok, "07_confirmed.png")
    # 8
    ok = send_msg(b, "đổi thành 15 câu", "t.indexOf('Phương án (phiên bản 2)')>=0")
    chip = b.js("(()=>{var t=%s;return t.indexOf('Chờ xác nhận')>=0})()" % LOG)
    cid = b.js("location.hash.split('/')[2]")
    pid = b.js("fetch('/api/chats/%s').then(r=>r.json()).then(d=>d.state.proposal.proposalId)" % cid)
    st409 = b.js("fetch('/api/chats/%s/actions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'confirm_plan',proposalId:'%s',version:1})}).then(r=>r.status)" % (cid, pid))
    b.shot("08_plan_v2.png")
    step(8, "'đổi thành 15 câu' -> phương án v2 chờ xác nhận; confirm version 1 -> 409", ok and chip and st409 == 409, "08_plan_v2.png", "confirm v1 status %s" % st409)
    # 9
    b.js(click_text("Hủy phương án"))
    ok = b.wait("(()=>{var t=%s;return t.indexOf('Đã hủy')>=0})()" % LOG)
    b.shot("09_cancelled.png")
    step(9, "Bấm Hủy phương án -> trạng thái đã hủy", ok, "09_cancelled.png")
    # 10
    b.js("document.querySelector('a[href=\"#/models\"]').click()")
    b.wait("!document.querySelector('[data-chatbot-v2]') && location.hash==='#/models'")
    b.js("document.querySelector('a[href=\"#/chat\"]').click()")
    ok = b.wait("document.querySelector('[data-chatbot-v2] textarea')")
    b.shot("10_switch_tab.png")
    step(10, "Đổi tab Mô hình rồi quay lại -> giao diện mới hoạt động", ok, "10_switch_tab.png")
    # 11
    FRESH[0] += 1; b.nav(base + "/?v=%d#/chat" % FRESH[0])
    ok = b.wait("document.querySelector('[data-chatbot-v2] textarea')")
    b.shot("11_direct_chat.png")
    step(11, "Mở thẳng /#/chat -> giao diện mới", ok, "11_direct_chat.png")
    # --- ca phản hồi chậm ---
    SLOW = (r"(()=>{var f=window.fetch.__orig||window.fetch;var g=function(u,o){return /\/api\/chat$|\/actions$/.test(String(u))?new Promise(function(r){setTimeout(function(){r(f(u,o))},3000)}):f(u,o)};g.__orig=f;window.fetch=g;return true})()")
    def side_click(title):
        return b.js("(()=>{var x=[...document.querySelectorAll('[data-chatbot-v2] .list button')].find(y=>y.textContent.trim()==%s);if(!x)return false;x.click();return true})()" % json.dumps(title, ensure_ascii=False))
    def open_a():
        FRESH[0] += 1; b.nav(base + "/?v=%d#/chat/%s" % (FRESH[0], cid))
        b.wait("document.querySelector('[data-chatbot-v2] textarea')")
        b.wait("(()=>{var t=%s;return t.indexOf('đổi thành 15 câu')>=0})()" % LOG)
        b.js(SLOW)
    def fire(text):
        return b.js("(()=>{var t=document.querySelector('[data-chatbot-v2] textarea');t.value=%s;[...document.querySelectorAll('[data-chatbot-v2] button')].find(x=>x.textContent.trim()==='Gửi').click();return true})()" % json.dumps(text, ensure_ascii=False))
    # chat B tạo qua API (cùng phiên đăng nhập)
    bid = b.js("fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:'Tạo game ôn lịch sử',requestId:'chatB-0001-abc'})}).then(r=>r.json()).then(d=>d.chatId)")
    # 12 (i)
    open_a(); fire("đổi thành 12 câu"); time.sleep(0.5)
    clicked = side_click("Tạo game ôn lịch sử")
    time.sleep(4.5)
    h = b.js("location.hash"); txt = b.js(LOG)
    usable = b.js("(()=>{var t=document.querySelector('[data-chatbot-v2] textarea');var s=[...document.querySelectorAll('[data-chatbot-v2] button')].find(x=>x.textContent.trim()==='Gửi');return !t.disabled&&!s.disabled})()")
    b.shot("12_slow_switch_chat.png")
    step(12, "(i) A gửi chậm 3s, bấm sang chat B -> hash vẫn #/chat/B, log B không có tin của A, ô nhập dùng được",
         clicked and h == "#/chat/%s" % bid and "12 câu" not in txt and "ôn lịch sử" in txt and usable, "12_slow_switch_chat.png", "hash=%s" % h)
    # 13 (ii)
    open_a(); fire("đổi thành 13 câu"); time.sleep(0.5)
    clicked = b.js(click_text("Cuộc trò chuyện mới"))
    time.sleep(4.5)
    h = b.js("location.hash"); txt = b.js(LOG)
    usable = b.js("(()=>{var t=document.querySelector('[data-chatbot-v2] textarea');var s=[...document.querySelectorAll('[data-chatbot-v2] button')].find(x=>x.textContent.trim()==='Gửi');return !t.disabled&&!s.disabled})()")
    b.shot("13_slow_new_chat.png")
    step(13, "(ii) A gửi chậm, bấm 'Cuộc trò chuyện mới' -> hash #/chat, log trống không có tin của A, dùng được",
         clicked and h == "#/chat" and "13 câu" not in txt and usable, "13_slow_new_chat.png", "hash=%s" % h)
    # 14 (iii)
    open_a(); fire("đổi thành 14 câu"); time.sleep(0.5)
    b.js("document.querySelector('a[href=\"#/models\"]').click()")
    time.sleep(4.5)
    away = b.js("!document.querySelector('[data-chatbot-v2]') && location.hash==='#/models'")
    b.shot("14a_slow_on_models.png")
    b.js("document.querySelector('a[href=\"#/chat\"]').click()")
    back = b.wait("document.querySelector('[data-chatbot-v2] textarea')")
    usable = b.js("(()=>{var t=document.querySelector('[data-chatbot-v2] textarea');return !!t&&!t.disabled})()")
    b.shot("14b_slow_back_to_chat.png")
    step(14, "(iii) gửi chậm rồi bấm tab Mô hình -> không lỗi, quay lại tab Trợ lý game vẫn dùng được",
         away and back and usable, "14a_slow_on_models.png, 14b_slow_back_to_chat.png")
    # 15 (iv)
    FRESH[0] += 1; b.nav(base + "/?v=%d#/chat" % FRESH[0])
    b.wait("document.querySelector('[data-chatbot-v2] textarea')"); b.js(SLOW)
    fire("Tạo game ôn địa lý"); time.sleep(0.5)
    clicked = side_click("Tạo game ôn lịch sử")
    time.sleep(4.5)
    h = b.js("location.hash")
    titles = b.js("[...document.querySelectorAll('[data-chatbot-v2] .list button')].map(x=>x.textContent.trim())")
    b.shot("15_slow_new_unsaved_switch.png")
    step(15, "(iv) chat mới chưa có id gửi chậm rồi chuyển B -> URL không đổi sang chat mới; danh sách có thêm chat mới",
         clicked and h == "#/chat/%s" % bid and "Tạo game ôn địa lý" in titles, "15_slow_new_unsaved_switch.png", "hash=%s; titles=%s" % (h, titles))
    # 16
    ws.pump(0.5)
    errs = []
    for e in ws.events:
        if e["method"] == "Runtime.exceptionThrown":
            d = e["params"]["exceptionDetails"]
            errs.append("exception: " + str(d.get("exception", {}).get("description", d.get("text"))))
        elif e["method"] == "Runtime.consoleAPICalled" and e["params"].get("type") == "error":
            errs.append("console.error: " + str([a.get("value", a.get("description")) for a in e["params"]["args"]]))
    step(16, "Không có lỗi console JS / exception trong toàn bộ kịch bản", not errs, "-", "; ".join(errs[:5]) if errs else "0 lỗi")
    return cid, bid


HOOK = r"""(()=>{if(window.__hooked)return true;var f=window.fetch;window.__cfg={delay:0,fail:0,mode:'send'};window.__posts=[];
window.fetch=function(u,o){var s=String(u),m=((o&&o.method)||'GET').toUpperCase();
if(m==='POST'&&/\/api\/chat$|\/actions$/.test(s))window.__posts.push(s);
if(m==='GET'&&/\/api\/chats\/[A-Za-z0-9_-]+$/.test(s)){var c=window.__cfg;
if(c.fail>0){c.fail--;return Promise.resolve(new Response('{"error":"server","message":"loi gia lap"}',{status:500,headers:{'Content-Type':'application/json'}}))}
if(c.delay>0){if(c.mode==='resp'){return f(u,o).then(function(r){return new Promise(function(ok){setTimeout(function(){ok(r)},c.delay)})})}
return new Promise(function(ok){setTimeout(function(){ok(f(u,o))},c.delay)})}}
return f(u,o)};window.__f=f;window.__hooked=true;return true})()"""


def serve_old_js(ws, path):
    with open(path, "rb") as f:
        body = base64.b64encode(f.read()).decode()

    def handler(m):
        if m.get("method") == "Fetch.requestPaused":
            ws.id += 1
            ws.send({"id": ws.id, "method": "Fetch.fulfillRequest", "params": {
                "requestId": m["params"]["requestId"], "responseCode": 200,
                "responseHeaders": [{"name": "Content-Type", "value": "application/javascript; charset=utf-8"}], "body": body}})
    return handler


def console_errs(ws):
    ws.pump(0.5)
    errs = []
    for e in ws.events:
        if e["method"] == "Runtime.exceptionThrown":
            d = e["params"]["exceptionDetails"]
            errs.append("exception: " + str(d.get("exception", {}).get("description", d.get("text"))))
        elif e["method"] == "Runtime.consoleAPICalled" and e["params"].get("type") == "error":
            errs.append("console.error: " + str([a.get("value", a.get("description")) for a in e["params"]["args"]]))
    return errs


UI = ("(()=>{var t=document.querySelector('[data-chatbot-v2] textarea'),s=[...document.querySelectorAll('[data-chatbot-v2] button')].find(x=>x.textContent.trim()==='Gửi');"
      "return {ta:t?t.disabled:null,send:s?s.disabled:null,loading:!!document.querySelector('.chatbot-loading'),"
      "err:!!document.querySelector('[data-chatbot-v2] .msgs .err'),retry:!!document.querySelector('.chatbot-retry'),"
      "posts:(window.__posts||[]).length,txt:%s,hash:location.hash}})()" % LOG)


def slow_get_steps(b, ws, base, ph):
    TC, TD = "Tạo game ôn vật lý", "Tạo game ôn hóa học"

    def png(n):
        return "%s_%s.png" % (ph, n)

    def mk(body):
        return b.js("fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(%s)}).then(r=>r.json())" % json.dumps(body, ensure_ascii=False))

    c = mk({"text": TC, "requestId": "slowC-0001-" + ph})
    cidC = c["chatId"]
    mk({"chatId": cidC, "text": "lớp 6", "requestId": "slowC-0002-" + ph, "expectedVersion": 1})
    cidD = mk({"text": TD, "requestId": "slowD-0001-" + ph})["chatId"]

    def fresh():
        FRESH[0] += 1
        b.nav(base + "/?v=%d#/chat" % FRESH[0])
        b.wait("document.querySelector('[data-chatbot-v2] textarea')")
        b.js(HOOK)

    def cfg(delay=0, fail=0, mode="send"):
        b.js("window.__cfg={delay:%d,fail:%d,mode:'%s'};window.__posts=[];true" % (delay, fail, mode))

    def side_click(title):
        b.wait("[...document.querySelectorAll('[data-chatbot-v2] .list button')].find(y=>y.textContent.trim()==%s)" % json.dumps(title, ensure_ascii=False))
        return b.js("(()=>{var x=[...document.querySelectorAll('[data-chatbot-v2] .list button')].find(y=>y.textContent.trim()==%s);if(!x)return false;x.click();return true})()" % json.dumps(title, ensure_ascii=False))

    def ui():
        return b.js(UI)

    def try_send(text):
        b.js("(()=>{var t=document.querySelector('[data-chatbot-v2] textarea');t.value=%s;"
             "[...document.querySelectorAll('[data-chatbot-v2] button')].find(x=>x.textContent.trim()==='Gửi').click();"
             "t.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',ctrlKey:true,bubbles:true}));return true})()" % json.dumps(text, ensure_ascii=False))

    def safe(n, title, img, fn):
        try:
            ok, note = fn()
            step(n, title, ok, img, note)
        except Exception as ex:
            step(n, title, False, img, "ngoại lệ: %r" % ex)

    def s17():
        fresh(); cfg(4000); side_click(TC); time.sleep(1)
        st = ui(); try_send("gõ thử khi đang tải"); time.sleep(0.5)
        st_b = ui(); b.shot(png("17_loading"))
        b.wait("(()=>{var t=%s;return t.indexOf('lớp 6')>=0 && !document.querySelector('.chatbot-loading')})()" % LOG, 12)
        st2 = ui(); b.shot(png("17_loaded"))
        ok = bool(st["loading"] and st["ta"] and st["send"] and st_b["posts"] == 0 and st2["ta"] is False and st2["send"] is False
                  and TC in st2["txt"] and "lớp 6" in st2["txt"])
        return ok, "khi chờ: loading=%s ta_disabled=%s send_disabled=%s; POST đã gửi=%s; sau tải: ta_disabled=%s send_disabled=%s đủ tin=%s" % (
            st["loading"], st["ta"], st["send"], st_b["posts"], st2["ta"], st2["send"], TC in st2["txt"] and "lớp 6" in st2["txt"])
    safe(17, "GET chậm 4s, mở chat có sẵn: thấy 'Đang tải', ô nhập + Gửi disabled, gõ/Gửi/Ctrl+Enter không POST; tải xong mở khóa, đủ tin", png("17_loading") + ", " + png("17_loaded"), s17)

    def srv_state():
        return b.js("window.__f('/api/chats/%s').then(r=>r.json()).then(d=>({v:d.state.stateVersion,n:d.messages.length}))" % cidC)

    def s18():
        fresh(); cfg(4000); side_click(TC); time.sleep(1)
        v0 = srv_state()
        b.js("window.__f('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({chatId:%s,text:'phép cộng có nhớ, 20 câu',requestId:'direct-18-%s-xyz',expectedVersion:%d})}).then(r=>r.status)" % (cidC, ph, v0["v"]))
        v1 = srv_state()
        b.wait("(()=>{var t=%s;return t.indexOf('20 câu')>=0 && !document.querySelector('.chatbot-loading')})()" % LOG, 12)
        st = ui(); b.shot(png("18_after_get"))
        try_send("ôn chương cơ học")
        b.wait("(()=>{var t=%s;return t.indexOf('ôn chương cơ học')>=0 && !document.querySelector('.chatbot-loading')})()" % LOG, 10)
        time.sleep(1)
        st3 = ui(); b.shot(png("18_next_send"))
        v2 = srv_state()
        ok = bool("20 câu" in st["txt"] and v1["v"] == v0["v"] + 1 and v2["n"] == v1["n"] + 2
                  and "bản mới hơn" not in st3["txt"] and not st3["err"])
        return ok, "server v%s->v%s (POST trực tiếp trong lúc GET chờ); sau GET UI có tin mới=%s; gửi tiếp: server v%s, tin %s->%s, không 409/err=%s" % (
            v0["v"], v1["v"], "20 câu" in st["txt"], v2["v"], v1["n"], v2["n"], not st3["err"] and "bản mới hơn" not in st3["txt"])
    safe(18, "POST trực tiếp trong lúc GET chậm đang chờ: sau GET UI không lùi (thấy tin mới), gửi tiếp OK không 409", png("18_after_get") + ", " + png("18_next_send"), s18)

    def s18b():
        fresh(); cfg(4000, 0, "resp"); side_click(TC); time.sleep(1)
        try_send("tin gửi khi đang tải 18b"); time.sleep(1.5)
        st_mid = ui(); b.shot(png("18b_waiting"))
        b.wait("!document.querySelector('.chatbot-loading') && (()=>{var t=%s;return t.indexOf('lớp 6')>=0})()" % LOG, 12)
        time.sleep(1)
        st = ui(); b.shot(png("18b_after_get"))
        if st_mid["posts"] > 0:
            ok = "tin gửi khi đang tải 18b" in st["txt"]
            note = "UI cho gửi trong lúc chờ (POST=%d); sau khi GET (ảnh chụp cũ) về, tin vừa gửi còn trong log=%s" % (st_mid["posts"], ok)
        else:
            ok = st["ta"] is False and "lớp 6" in st["txt"]
            note = "UI khóa gửi trong lúc chờ (POST=0); sau GET mở khóa=%s, đủ tin=%s" % (st["ta"] is False, "lớp 6" in st["txt"])
        return ok, note
    safe("18b", "GET chậm trả bản chụp CŨ: cố gửi trong lúc chờ -> không có tin nào bị ghi đè/mất", png("18b_waiting") + ", " + png("18b_after_get"), s18b)

    def s19():
        fresh(); cfg(0, 1); side_click(TC)
        got = b.wait("document.querySelector('.chatbot-retry')", 6)
        st = ui(); b.shot(png("19_error"))
        if got:
            b.js("window.__cfg.fail=0;document.querySelector('.chatbot-retry').click();true")
        b.wait("(()=>{var t=%s;return t.indexOf('lớp 6')>=0 && !document.querySelector('.chatbot-loading')})()" % LOG, 8)
        st2 = ui(); b.shot(png("19_retried"))
        ok = bool(got and st["err"] and st["ta"] and st2["ta"] is False and st2["send"] is False and "lớp 6" in st2["txt"])
        return ok, "sau GET 500: nút 'Thử tải lại'=%s, div.err=%s, ô nhập khóa=%s; sau thử lại: mở khóa=%s, đủ tin=%s" % (got, st["err"], st["ta"], st2["ta"] is False, "lớp 6" in st2["txt"])
    safe(19, "GET trả 500 một lần: div.err + 'Thử tải lại', ô nhập khóa; bấm thử lại -> mở khóa, đủ tin", png("19_error") + ", " + png("19_retried"), s19)

    def s20():
        notes = []
        fresh(); cfg(4000); side_click(TC); time.sleep(0.7)
        b.js(click_text("Cuộc trò chuyện mới")); time.sleep(0.3)
        a1 = ui(); b.shot(png("20a_new_during_load"))
        time.sleep(5); a2 = ui()
        oka = a1["ta"] is False and a1["send"] is False and not a1["loading"] and a2["hash"] == "#/chat" and TC not in a2["txt"] and a2["ta"] is False
        notes.append("a(chat mới)=%s [ta_disabled=%s loading=%s hash=%s]" % (oka, a1["ta"], a1["loading"], a2["hash"]))
        fresh(); cfg(4000); side_click(TC); time.sleep(0.7); side_click(TD)
        b.wait("(()=>{var t=%s;return t.indexOf('ôn hóa học')>=0 && !document.querySelector('.chatbot-loading')})()" % LOG, 14)
        time.sleep(1); bb = ui(); b.shot(png("20b_switch_chat"))
        okb = bb["hash"] == "#/chat/%s" % cidD and TD in bb["txt"] and "vật lý" not in bb["txt"] and bb["ta"] is False
        notes.append("b(chuyển chat)=%s [hash=%s]" % (okb, bb["hash"]))
        fresh(); cfg(4000); side_click(TC); time.sleep(0.7)
        b.js("document.querySelector('a[href=\"#/models\"]').click()"); time.sleep(5)
        away = b.js("!document.querySelector('[data-chatbot-v2]') && location.hash==='#/models'")
        b.js("document.querySelector('a[href=\"#/chat\"]').click()")
        back = b.wait("document.querySelector('[data-chatbot-v2] textarea')", 8)
        cc = ui(); b.shot(png("20c_tab_back"))
        okc = bool(away and back and cc["ta"] is False and "vật lý" not in cc["txt"])
        notes.append("c(rời tab/quay lại)=%s" % okc)
        return oka and okb and okc, "; ".join(notes)
    safe(20, "Trong lúc GET chậm: 'Cuộc trò chuyện mới' dùng được ngay, chuyển chat khác không bị đè, rời tab Mô hình rồi quay lại", png("20a_new_during_load") + ", " + png("20b_switch_chat") + ", " + png("20c_tab_back"), s20)


def main(old_js=None):
    port = free_port(); dport = free_port()
    env = dict(os.environ, AILAB_DB=os.path.join(TMP, "b.db"), AILAB_PORT=str(port), AILAB_HOST="127.0.0.1",
               MODEL_PROVIDER="fake", AILAB_ADMIN_PASSWORD=PASSWORD, PYTHONIOENCODING="utf-8")
    srv = subprocess.Popen([sys.executable, os.path.join(REPO, "ailab", "chatbot_server.py")], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    chrome = None
    version = "?"
    base = "http://127.0.0.1:%d" % port
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(base + "/", timeout=2).read(); break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("server không lên")
        chrome = subprocess.Popen([CHROME, "--headless=new", "--remote-debugging-port=%d" % dport, "--user-data-dir=" + os.path.join(TMP, "prof"),
                                   "--window-size=1280,900", "--no-first-run", "--disable-gpu", "about:blank"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        tgt = None
        for _ in range(60):
            try:
                version = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json/version" % dport, timeout=2))["Browser"]
                tgt = [t for t in json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % dport, timeout=2)) if t["type"] == "page"][0]
                break
            except Exception:
                time.sleep(0.5)
        if not tgt: raise RuntimeError("không kết nối được Chrome CDP")
        ws = WS(tgt["webSocketDebuggerUrl"]); b = Browser(ws)

        ws.call("Page.enable"); ws.call("Runtime.enable")
        if old_js:
            ws.on_event = serve_old_js(ws, old_js)
            ws.call("Network.enable"); ws.call("Network.setCacheDisabled", {"cacheDisabled": True})
            ws.call("Fetch.enable", {"patterns": [{"urlPattern": "*chatbot.js*"}]})
            b.nav(base + "/")
            b.wait("document.querySelector('form.ail-form')")
            b.js("fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'hocsinh01',password:%s})}).then(r=>r.status)" % json.dumps(PASSWORD))
        else:
            base_steps(b, ws, base)
        slow_get_steps(b, ws, base, "old" if old_js else "new")
        errs = console_errs(ws)
        step(21, "Không có lỗi console JS / exception trong toàn bộ kịch bản", not errs, "-", "; ".join(errs[:5]) if errs else "0 lỗi")
    except Exception as ex:
        results.append(("-", "Ngoại lệ script: %r" % ex, "FAIL", "-", ""))
        print("LỖI:", repr(ex))
    finally:
        for p in (chrome, srv):
            if p:
                p.terminate()
                try: p.wait(10)
                except Exception: p.kill()
        shutil.rmtree(TMP, ignore_errors=True)
    write_results(version, "old" if old_js else "new")
    return 0 if all(r[2] == "PASS" for r in results) and results else 1


def write_results(version, ph):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(os.path.join(HERE, "results_%s.json" % ph), "w", encoding="utf-8") as f:
        json.dump({"time": now, "chrome": version, "python": sys.version.split()[0], "rows": results}, f, ensure_ascii=False, indent=1)
    L = ["# I01 - Kết quả kiểm tra trình duyệt thật", "",
         "- Lệnh (bản mới trong repo): `python evidence/chatbot/I01/browser_check.py`",
         "- Lệnh (bản cũ để so sánh): `python evidence/chatbot/I01/browser_check.py --old-js <đường dẫn chatbot.js cũ>` (CDP `Fetch.fulfillRequest` phục vụ bản cũ thay bản repo, KHÔNG sửa file repo)",
         "- Chạy bằng Chrome headless 1280x900 (CDP tự viết, thư viện chuẩn); server `python ailab/chatbot_server.py`, DB tạm, `MODEL_PROVIDER=fake` (fake-rules, không phải AI thật); Windows 11",
         "- Đăng nhập: `fetch('/api/register')` trong trang rồi reload. 'Mở thẳng URL' = navigate tới `/?v=N#/chat...` (tải trang mới).",
         "- Ca GET chậm: ghi đè `window.fetch` (sau khi trang tải, trước khi bấm chọn chat) trễ 4s cho `GET /api/chats/<id>`; GET 500: trả Response 500 giả một lần; bước 18b trễ PHẢN HỒI (bản chụp cũ), các ca khác trễ trước khi gửi request.", ""]
    for ph2, label in (("old", "Trước sửa (chatbot.js cũ)"), ("new", "Sau sửa (chatbot.js trong repo)")):
        p = os.path.join(HERE, "results_%s.json" % ph2)
        if not os.path.exists(p):
            continue
        d = json.load(open(p, encoding="utf-8"))
        L += ["## " + label, "", "Ngày giờ: %s; Chrome %s; Python %s" % (d["time"], d["chrome"], d["python"]), "",
              "| Bước | Nội dung | Kết quả | Ảnh | Ghi chú |", "|---|---|---|---|---|"]
        for n, t, r, img, note in d["rows"]:
            L.append("| %s | %s | %s | %s | %s |" % (n, t, r, img, str(note).replace("|", "/")))
        L += ["", "Tổng: %d/%d PASS" % (sum(1 for r in d["rows"] if r[2] == "PASS"), len(d["rows"])), ""]
    with open(os.path.join(HERE, "RESULTS.md"), "w", encoding="utf-8") as f:
        f.write(chr(10).join(L) + chr(10))


if __name__ == "__main__":
    old = None
    if "--old-js" in sys.argv:
        old = os.path.abspath(sys.argv[sys.argv.index("--old-js") + 1])
    sys.exit(main(old))
