---
name: edu-game-contract
description: Dùng khi sửa contract game học tập, sinh HTML (N3), kiểm thử Playwright (N4), FIX, reference_game.html hoặc prompt codegen/fix — tóm tắt các điểm contract hay làm hỏng và cách kiểm nhanh.
---

# Edu game contract — checklist nhanh

Nguồn đầy đủ: `docs/GAME_CONTRACT.md`. Chỉ đọc mục cần thiết.

## 6 testid bắt buộc
`start-button` · `question` · `score` · `result-screen` · `final-score` · `restart-button`

## `window.__GAME__`
`ready`, `start()`, `getState()` → `{status, score, maxScore, correctCount, questionIndex, totalQuestions}`,
`answer(choice)` → bool, `getCorrectAnswer()`, `getResult()` → `{score, maxScore, correctCount, totalQuestions, wrong[]}`.

## Hay hỏng nhất (kiểm khi viết reference_game hoặc prompt)
1. `answer()` bị khoá trong lúc hiệu ứng: N4 timeout ở `questionIndex`.
2. `start()`/restart không reset `wrong[]` hoặc `score`: lượt "sai hết" ra điểm ≠ 0.
3. `result-screen` dùng `opacity:0` thay vì `display:none` khi đang chơi: Playwright coi là visible.
4. Đọc câu hỏi trước khi DOM có `#question-bank`: đặt script game ở cuối `<body>`.
5. `final-score` không chứa `maxScore` dạng số: phải là `"80/80"` hoặc `"80 / 80 điểm"`.
6. Canvas cố định `width=500`: tràn ở 375px. Dùng `max-width:100%` + resize theo container.
7. Font/ảnh từ CDN: bị chặn mạng, sinh `console.error`.

## Kiểm nhanh không cần pipeline
```
python -c "from app.domain.contract import static_check;import sys;print(static_check(open(sys.argv[1],encoding='utf-8').read()))" tests/fixtures/reference_game.html
pytest tests/integration/test_n4.py -q -x -m browser -k reference
```

## Quy tắc
- Không bao giờ để LLM viết nội dung `#question-bank`. Luôn gọi `inject_bank` sau N3 và sau FIX.
- Lỗi của N4 phải là chuỗi tiếng Việt, có tiền tố `[1280px]`/`[375px]`, ngắn gọn, vì FIX đọc nguyên văn.
- Thêm kiểm tra mới vào N4 thì phải thêm vào cả `CONTRACT_TEXT`, prompt `codegen`, và `reference_game.html` phải vẫn pass.
