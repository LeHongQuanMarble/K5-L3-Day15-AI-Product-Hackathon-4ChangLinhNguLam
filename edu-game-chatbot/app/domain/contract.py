"""Game contract (docs/GAME_CONTRACT.md). (T04)"""

from __future__ import annotations

import json
import re

REQUIRED_TESTIDS = ("start-button", "question", "score", "result-screen", "final-score", "restart-button")
MAX_HTML_BYTES = 2_000_000
QUESTION_BANK_ID = "question-bank"

# Tóm tắt GAME_CONTRACT §1–4 để chèn vào prompt codegen/fix qua {{CONTRACT}}
CONTRACT_TEXT = """\
GAME CONTRACT (bắt buộc):
C1. Một file HTML tự chứa, CSS/JS inline. KHÔNG dùng src/href tới http(s):// hoặc // (không CDN, font, ảnh ngoài).
C2. Có <!DOCTYPE html>, <html lang="vi">, <meta name="viewport" content="width=device-width, initial-scale=1">.
C3. Có <div id="game-root"> và ít nhất một <canvas> hoặc <svg> làm đồ hoạ. Bố cục co giãn, không tràn ngang ở 375px.
C4. Có <script type="application/json" id="question-bank"></script> để TRỐNG; hệ thống tự nhúng câu hỏi.
    Game chỉ đọc câu hỏi từ thẻ này (JSON: {"questions":[{id,type,question,options,answer,accept,explanation,points}]}).
    Đặt script game ở cuối <body>.
C5. Không dùng alert/confirm/prompt, fetch/XMLHttpRequest/WebSocket.
C6. Kích thước <= 2 MB.
data-testid bắt buộc: start-button (hiện khi idle), question (khi playing), score (khi playing),
result-screen (CHỈ hiện khi finished, ẩn bằng display:none), final-score (trong result-screen, dạng "80/80"),
restart-button (trong result-screen).
Màn hình kết quả: điểm/điểm tối đa; số câu đúng/tổng số câu; nhận xét (>=80%: "Xuất sắc", 50-79%: "Khá",
<50%: "Cần ôn thêm"); danh sách câu sai kèm đáp án đúng và giải thích; nút chơi lại.
API window.__GAME__ = { ready, start(), getState(), answer(choice), getCorrectAnswer(), getResult() }:
- ready: true sau khi đọc câu hỏi và dựng UI.
- start(): bắt đầu/chơi lại, reset toàn bộ (score, wrong, questionIndex).
- getState(): {status:"idle"|"playing"|"finished", score, maxScore, correctCount, questionIndex, totalQuestions}.
- answer(choice): mcq = chỉ số 0-based, true_false = boolean, fill_blank = chuỗi. Trả về true/false (đúng/sai).
  Phải nhận ngay khi status==="playing" (kể cả khi đang chạy hiệu ứng); questionIndex tăng trong <= 600 ms.
- getCorrectAnswer(): đáp án đúng của câu hiện tại.
- getResult(): {score, maxScore, correctCount, totalQuestions, wrong:[{id,question,yourAnswer,correctAnswer,explanation}]}.
Chấm điểm: đúng được points của câu, sai được 0, maxScore = tổng points.
fill_blank: không phân biệt hoa/thường, bỏ khoảng trắng thừa, chấp nhận cả accept[].
CHIỀU SÂU TƯƠNG TÁC (di chuyển, kéo thả, ngắm, combo, mạng, màn chơi...):
- Cơ chế phụ KHÔNG được chặn API: answer() nhận ngay khi status==="playing" (kể cả lúc đang di chuyển/hiệu ứng),
  câu hỏi hiện tại luôn hiện trong data-testid="question" và luôn có đáp án bấm/chạm được.
- Điểm chỉ từ points của câu hỏi (combo/vật phẩm chỉ là thưởng trực quan); hết mạng không kết thúc sớm,
  vẫn đi hết mọi câu; start() reset cả mạng, combo, màn chơi, vị trí nhân vật.
- Sai: hiện đáp án đúng + explanation ngắn, không chặn câu kế tiếp quá 600 ms.
ĐIỀU KHIỂN (mã mouse|keyboard|motion|voice|custom do giáo viên chọn):
- LUÔN chơi được bằng chuột/chạm và giữ mọi data-testid ở trên (kiểm thử tự động bấm chuột).
  Bàn phím/camera/micro là THÊM VÀO, không thay thế.
- keyboard: phím 1-4 hoặc A-D chọn đáp án, mũi tên để di chuyển, Enter để xác nhận; hiện chú thích phím trên màn hình.
- motion: nút "Bật camera" (KHÔNG tự xin quyền khi tải trang) -> navigator.mediaDevices.getUserMedia({video:true});
  phát hiện chuyển động bằng so sánh khung hình (frame differencing trên canvas) theo vùng trái/phải/trên...
  để chọn đáp án hoặc di chuyển; KHÔNG dùng thư viện/CDN; hiện ô camera nhỏ + hướng dẫn.
- voice: nút "Bật micro" -> SpeechRecognition/webkitSpeechRecognition (lang "vi-VN") để nói đáp án
  (A/B/C/D, "đúng"/"sai" hoặc nội dung đáp án); không có API thì đo âm lượng micro (AnalyserNode),
  "vỗ tay để xác nhận".
- Bị từ chối quyền / không có thiết bị / API không hỗ trợ: chỉ console.warn (TUYỆT ĐỐI không console.error,
  không throw), hiện thông báo thân thiện trên màn hình và tiếp tục chơi bằng chuột.
- custom: làm đúng mô tả của giáo viên theo các quy tắc trên.
"""

_BANK_RE = re.compile(
    r"""<script\b[^>]*\bid\s*=\s*["']question-bank["'][^>]*>.*?</script\s*>""",
    re.IGNORECASE | re.DOTALL,
)
_EXT_TAG_RE = re.compile(
    r"""<(?:script|link|img|iframe|audio|video|source)\b[^>]*?\b(?:src|href)\s*=\s*["']?\s*((?:https?:)?//[^"'\s>]*)""",
    re.IGNORECASE,
)
_FORBIDDEN_RE = re.compile(
    r"(?<![\w.$])(alert|confirm|prompt|fetch)\s*\(|(?<![\w.$])(XMLHttpRequest|WebSocket)\b"
)


def _strip_bank(html: str) -> str:
    return _BANK_RE.sub("", html)


def static_check(html: str) -> list[str]:
    """Kiểm C1–C6 + đủ testid + có window.__GAME__. Trả về list lỗi tiếng Việt; [] = đạt."""
    errs: list[str] = []
    if len(html.encode("utf-8")) > MAX_HTML_BYTES:
        errs.append("C6: File HTML vượt quá 2 MB")
    for url in find_external_resources(html):
        errs.append(f"C1: Tài nguyên ngoài không được phép: {url}")
    if not re.search(r"<!doctype\s+html", html, re.IGNORECASE):
        errs.append("C2: Thiếu <!DOCTYPE html>")
    if not re.search(r"<html\b[^>]*\blang\s*=\s*[\"']vi[\"']", html, re.IGNORECASE):
        errs.append('C2: Thiếu <html lang="vi">')
    if not re.search(r"<meta\b[^>]*\bname\s*=\s*[\"']viewport[\"']", html, re.IGNORECASE):
        errs.append('C2: Thiếu thẻ <meta name="viewport">')
    if not re.search(r"""\bid\s*=\s*["']game-root["']""", html):
        errs.append('C3: Thiếu <div id="game-root">')
    if not re.search(r"<(canvas|svg)\b", html, re.IGNORECASE):
        errs.append("C3: Thiếu <canvas> hoặc <svg> làm đồ hoạ")
    m = _BANK_RE.search(html)
    if not m:
        errs.append('C4: Thiếu <script type="application/json" id="question-bank">')
    elif not re.search(
        r"""type\s*=\s*["']application/json["']""", m.group(0).split(">", 1)[0], re.IGNORECASE
    ):
        errs.append('C4: Thẻ question-bank phải có type="application/json"')
    for name in find_forbidden_calls(html):
        errs.append(f"C5: Không được dùng {name}")
    for tid in REQUIRED_TESTIDS:
        if not re.search(rf"""data-testid\s*=\s*["']{re.escape(tid)}["']""", html):
            errs.append(f'Thiếu phần tử data-testid="{tid}"')
    if "__GAME__" not in html:
        errs.append("Thiếu window.__GAME__")
    return errs


def find_external_resources(html: str) -> list[str]:
    """Các thẻ script/link/img/iframe/audio/video/source trỏ tới http(s):// hoặc //."""
    return _EXT_TAG_RE.findall(_strip_bank(html))


def find_forbidden_calls(html: str) -> list[str]:
    """alert/confirm/prompt/fetch/XMLHttpRequest/WebSocket (không bắt nhầm obj.alert, myalert)."""
    found: list[str] = []
    for m in _FORBIDDEN_RE.finditer(_strip_bank(html)):
        name = m.group(1) or m.group(2)
        if name not in found:
            found.append(name)
    return found


def inject_bank(html: str, bank: dict) -> str:
    """Thay nội dung thẻ #question-bank bằng JSON bank (escape '</'); chưa có thẻ thì chèn đầu <head>."""
    payload = json.dumps(bank, ensure_ascii=False).replace("</", "<" + chr(92) + "/")
    tag = f'<script type="application/json" id="{QUESTION_BANK_ID}">{payload}</script>'
    if _BANK_RE.search(html):
        return _BANK_RE.sub(lambda _m: tag, html, count=1)
    head = re.search(r"<head\b[^>]*>", html, re.IGNORECASE)
    if head:
        return html[: head.end()] + tag + html[head.end() :]
    return tag + html
