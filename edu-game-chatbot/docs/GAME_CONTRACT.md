# GAME CONTRACT

Mọi file HTML do N3 sinh ra **phải** đạt contract này. `app/domain/contract.py` chứa
`CONTRACT_TEXT` (đưa vào prompt N3/FIX) và `static_check()`. N4 kiểm tra lại bằng Playwright.

## 1. Cấu trúc

| # | Yêu cầu | Kiểm bằng |
|---|---|---|
| C1 | Một file HTML tự chứa (CSS/JS inline). Không `src`/`href` tới `http(s)://` hoặc `//` | static + Playwright chặn mạng |
| C2 | Có `<!DOCTYPE html>`, `<html lang="vi">`, `<meta name="viewport" …>` | static |
| C3 | Có `<div id="game-root">` và ít nhất một `<canvas>` hoặc `<svg>` (đồ hoạ) | static |
| C4 | `<script type="application/json" id="question-bank">` chứa bộ câu hỏi; game đọc câu hỏi **chỉ** từ thẻ này | static + so khớp id |
| C5 | Không dùng `alert/confirm/prompt`, không `fetch/XMLHttpRequest/WebSocket` | static + Playwright |
| C6 | Kích thước ≤ 2 MB | static |

## 2. Phần tử bắt buộc (`data-testid`)

| testid | Vai trò | Hiển thị khi |
|---|---|---|
| `start-button` | Bắt đầu | `idle` |
| `question` | Nội dung câu hiện tại | `playing` |
| `score` | Điểm hiện tại | `playing` |
| `result-screen` | **Màn hình kết quả cuối game** | chỉ `finished` |
| `final-score` | Trong result-screen, dạng `"<điểm>/<tối đa>"` | `finished` |
| `restart-button` | Trong result-screen, chơi lại | `finished` |

## 3. Màn hình kết quả cuối game (bắt buộc)

Phải hiển thị: tổng điểm / điểm tối đa; số câu đúng / tổng số câu; nhận xét theo mức
(≥ 80 %: "Xuất sắc", 50–79 %: "Khá", < 50 %: "Cần ôn thêm"); danh sách câu sai kèm đáp án đúng
và giải thích; nút chơi lại.

## 4. API kiểm thử `window.__GAME__`

```ts
window.__GAME__ = {
  ready: boolean,                       // true sau khi đọc câu hỏi + dựng UI
  start(): void,                        // bắt đầu / chơi lại; reset toàn bộ
  getState(): { status: "idle"|"playing"|"finished", score: number, maxScore: number,
                correctCount: number, questionIndex: number, totalQuestions: number },
  answer(choice: number|boolean|string): boolean,   // trả lời câu hiện tại, trả về đúng/sai
  getCorrectAnswer(): number|boolean|string,        // đáp án đúng câu hiện tại
  getResult(): { score, maxScore, correctCount, totalQuestions,
                 wrong: { id, question, yourAnswer, correctAnswer, explanation }[] }
}
```

- `choice`: mcq là chỉ số 0-based, true_false là boolean, fill_blank là chuỗi.
- `answer()` phải nhận ngay khi `status === "playing"` (kể cả đang chạy hiệu ứng). Sau khi trả lời,
  `questionIndex` tăng trong ≤ 600 ms.
- Chấm điểm: câu đúng cộng `points` của câu đó, câu sai được 0. `maxScore = Σ points`.
- fill_blank: không phân biệt hoa/thường, bỏ khoảng trắng thừa, chấp nhận cả `accept[]`.

## 5. Kịch bản Playwright của N4 (chạy ở 1280×800 và 375×740)

1. Mở file, chờ `__GAME__.ready === true` (timeout `PLAYWRIGHT_TIMEOUT_MS`).
2. id câu hỏi trong `#question-bank` == id trong bộ câu hỏi của phiên (đúng thứ tự).
3. `scrollWidth <= innerWidth + 2` (không tràn ngang).
4. Click `start-button`: `status === "playing"`, `question` hiển thị, `result-screen` ẩn,
   `totalQuestions` và `maxScore` đúng.
5. Trả lời **đúng hết** qua `answer(getCorrectAnswer())`: `finished`, `result-screen` hiển thị,
   `getResult().score === maxScore`, `final-score` chứa `maxScore`. Chụp ảnh.
6. Click `restart-button`, trả lời **sai hết**: `score === 0`, `wrong.length === totalQuestions`. Chụp ảnh.
7. Không có `pageerror`, `console.error`, dialog, request mạng.

Mỗi lỗi là một chuỗi tiếng Việt có tiền tố viewport, ví dụ `"[375px] Bố cục bị tràn ngang"`.
Danh sách lỗi này được đưa nguyên văn cho FIX.

## 6. Bộ câu hỏi do hệ thống nhúng, không do LLM

N3 yêu cầu model để thẻ `#question-bank` rỗng. Sau khi model trả HTML, hàm `inject_bank()` thay nội
dung thẻ bằng JSON bộ câu hỏi thật (escape `</` thành `<\/`). FIX cũng gọi lại `inject_bank()`.
Nhờ đó model không thể bịa thêm hay bỏ bớt câu.

## 7. Điều khiển theo yêu cầu giáo viên

Giáo viên chọn cách điều khiển trước khi tạo game (SPEC §2 mục 7); N3 nhận mã
`mouse | keyboard | motion | voice | custom` và mô tả.

- **Luôn chơi được bằng chuột/chạm** và giữ mọi `data-testid` ở §2 (N4 bấm bằng chuột).
  Các kiểu điều khiển khác là **thêm vào**, không thay thế.
- `keyboard`: phím `1–4` / `A–D` chọn đáp án, mũi tên di chuyển, `Enter` xác nhận; hiện chú thích phím trên màn hình.
- `motion`: nút "Bật camera" (không tự xin quyền khi tải trang) → `navigator.mediaDevices.getUserMedia({video:true})`;
  phát hiện chuyển động bằng so sánh khung hình (frame differencing trên canvas) theo vùng trái/phải/trên…
  để chọn đáp án hoặc di chuyển. Không thư viện/CDN. Hiện ô camera nhỏ + hướng dẫn.
- `voice`: nút "Bật micro" → `SpeechRecognition`/`webkitSpeechRecognition` (`lang="vi-VN"`) để nói đáp án
  (A/B/C/D, "đúng"/"sai" hoặc nội dung đáp án). Không có API thì đo âm lượng micro (`AnalyserNode`): "vỗ tay để xác nhận".
- Từ chối quyền / không có thiết bị / API không hỗ trợ: chỉ `console.warn` (**không** `console.error`, không throw —
  N4 bắt `console.error`/`pageerror`), hiện thông báo thân thiện và tiếp tục chơi bằng chuột.
- `custom`: làm đúng mô tả của giáo viên theo các quy tắc trên.

Preview: iframe có `allow="camera; microphone; autoplay"` và CSP thêm `media-src … mediastream:`. Iframe vẫn
`sandbox="allow-scripts"` (không `allow-same-origin`) nên trên Chromium `getUserMedia` trong iframe bị chặn
(`SecurityError: Invalid security origin`); game rơi về chơi bằng chuột. Camera/micro dùng được khi mở game
toàn màn hình (tab riêng) hoặc file đã xuất chạy trên `localhost`/HTTPS.
