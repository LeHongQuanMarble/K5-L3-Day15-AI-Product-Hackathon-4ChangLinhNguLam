# QUESTION SCHEMA

## 1. JSON chuẩn

```json
{
  "title": "Ôn tập phân số",
  "subject": "Toán", "grade": "Lớp 4",
  "questions": [
    {"id": "q1", "type": "mcq", "question": "1/2 + 1/4 = ?",
     "options": ["3/4", "2/6", "1/6", "2/4"], "answer": 0,
     "explanation": "Quy đồng: 2/4 + 1/4 = 3/4", "points": 10},
    {"id": "q2", "type": "true_false", "question": "3/5 > 1/2", "answer": true,
     "explanation": "3/5 = 0,6 > 0,5", "points": 10},
    {"id": "q3", "type": "fill_blank", "question": "Phân số 4/8 rút gọn là ___",
     "answer": "1/2", "accept": ["1 / 2"], "explanation": "Chia cả tử và mẫu cho 4", "points": 10}
  ]
}
```

## 2. Quy tắc hợp lệ (`validate_bank` trả về list lỗi tiếng Việt, rỗng = hợp lệ)

| Trường | Quy tắc |
|---|---|
| `questions` | list, 3 ≤ len ≤ 50 |
| `id` | chuỗi không rỗng, duy nhất |
| `type` | `mcq` \| `true_false` \| `fill_blank` |
| `question` | chuỗi không rỗng sau strip |
| mcq `options` | 2–6 chuỗi không rỗng, không trùng nhau |
| mcq `answer` | **int** (không phải bool) trong `[0, len(options))` |
| true_false `answer` | bool |
| fill_blank `answer` | chuỗi không rỗng; `accept` (tuỳ chọn) là list chuỗi |
| `points` | int > 0 (không phải bool), mặc định 10 |
| `explanation` | chuỗi, mặc định `""` |

`normalize_bank`: điền `id` (`q1…`), `points=10`, `explanation=""`, `title="Bộ câu hỏi"`.
Hàm này **không** sửa nội dung câu hỏi/đáp án.
`max_score(bank) = Σ points`.

Chú ý: `isinstance(True, int)` là `True` trong Python, nên phải loại bool trước khi kiểm int.

## 3. Nhập từ file người dùng

- `.json`: object như trên, hoặc một list câu hỏi (sẽ bọc thành `{"questions": [...]}`).
- `.csv` (UTF-8, có thể có BOM), header:
  `type,question,options,answer,explanation,points`
  - `options` ngăn cách bằng `|`
  - mcq `answer`: chữ cái `A`–`F` hoặc chỉ số 0-based
  - true_false `answer`: `true/false/đúng/sai/1/0`
  - Lỗi dòng nào thì báo `"Dòng <n>: …"` (n tính cả header, tức dòng dữ liệu đầu tiên là dòng 2).
- File không hợp lệ: bot liệt kê tối đa 10 lỗi đầu tiên, giữ state `AWAIT_SOURCE_INPUT` để người dùng tải lại.

## 4. Nguồn `user`: không được sửa câu hỏi

Bộ câu hỏi của giáo viên được giữ nguyên văn. AI chỉ được sửa khi giáo viên yêu cầu rõ ràng ở vòng
chỉnh sửa (N2 trả `question_edit`).
