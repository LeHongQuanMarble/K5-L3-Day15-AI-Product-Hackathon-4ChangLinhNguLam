# Hợp đồng đầu vào, đầu ra và tích hợp

Tất cả trường/endpoint **mới** dưới đây là đề xuất cần chốt G0. Dùng camelCase ở API cho nhất quán repo. Không đổi tên khóa cũ đột ngột.

## 1. Đầu vào công khai

API hiện tại: `POST /api/chat` nhận `{chatId?, text}`; text 3–2000 ký tự. Giữ tương thích này.

Đề xuất mở rộng yêu cầu:

```json
{
  "chatId": 8,
  "text": "Phép cộng lớp 2, 10 câu",
  "requestId": "uuid-do-client-tao",
  "expectedVersion": 2,
  "action": "message",
  "documentIds": []
}
```

`chatId` chỉ dùng khi thuộc người đăng nhập. `requestId` chống xử lý trùng; `expectedVersion` chống ghi đè lượt mới. Không nhận userId, danh mục, quyền hoặc teacherApproved do client tự gán.

Xác nhận dùng thao tác tường minh gắn proposalId + version, không dùng việc LLM đoán chữ “đồng ý” làm thẩm quyền ghi DB. Người dùng vẫn có thể nói đồng ý; UI phải đưa hành động xác nhận đúng bản và máy chủ xác thực lại.

Các thao tác đề xuất: `confirm_plan`, `accept_result`, `reject_result`. G0 chọn endpoint riêng hoặc route proposal hiện tại mở rộng; phải giữ các proposal cũ hoạt động, không tái diễn giải accept HTML cũ thành tạo App mới.

## 2. Ngữ cảnh nội bộ do máy chủ cung cấp

```text
ChatContext:
  user: danh tính đã xác thực, không chứa mật khẩu/token
  state: ConversationState hiện tại
  catalog: players/models/exams đã lọc quyền
  documents: văn bản chuẩn hóa + nguồn, có giới hạn dung lượng
  capabilities: runtimeKinds=[image,pose,hands], audio=false
```

Không gửi toàn bộ database vào LLM. Chỉ lấy nội dung Exam/HTML chi tiết khi cần; không lộ tài liệu người khác. Danh mục và khả năng runtime phải đọc/đối chiếu mã hiện tại, không cố định ID.

## 3. Trạng thái yêu cầu

```text
TeacherRequirements:
  subject, gradeOrAudience, topic: string|null
  learningGoal: string|null
  questionCount: int|null (1..200 khi dùng Exam)
  difficulty: string|null
  contentSource: {kind: topic|document|existing_exam|provided_questions,
                  documentIds: [], examId: int|null}
  gamePreference: {mode: auto|reuse_existing|generate_new,
                   playerId: int|null, description: string|null}
  interaction: {mouse: true, requestedKinds: [], useModel: boolean|null}
  constraints: {durationSeconds: int|null, scoring: string|null, other: []}
```

Những trường không áp dụng được phép null, không ép game danh sách phải có câu hỏi. AI có thể đề xuất mặc định nhưng phải ghi assumptions (giả định) để xác nhận. Trích xuất chỉ cập nhật trường được nói đến, không xóa dữ liệu cũ vì lượt mới không nhắc lại.

## 4. Đầu ra cho giao diện

```text
ChatResponse:
  chatId: int
  reply:
    role: bot
    text: string
    status: clarifying|awaiting_confirmation|awaiting_review|
            needs_revision|ready|error
    simulated: boolean
    model: string                 # LLM, khác model điều khiển
    stateVersion: int
    requirements: TeacherRequirements
    missingFields: string[]
    questions: [{field, text}]    # câu hỏi bổ sung, không phải Exam
    proposal: GameProposal|null
    validation: ValidationResult|null
    result: GameResult|null
    error: ChatError|null
```

G0 quyết định cách tương thích `error` cũ đang là string và proposal cũ; không thay kiểu rồi làm UI cũ crash. Có thể dùng trường mới `failure` cho lỗi có cấu trúc trong giai đoạn chuyển tiếp.

`GameProposal`:

```text
  proposalId, version, status
  generationMode: reuse_existing|generate_new
  reason, assumptions[], changes[]
  player: {playerId:int|null, name, plan, manifest?}
  exam: {examId:int|null, name, questions:ExamQuestion[], content:string|null}
  interactionModel: {modelId:int|null, kind:string|null, mapping:object,
                     sure:number, holdMs:int, mouse:true}
  warnings[], validation
```

HTML mới nằm phía server; lấy srcdoc được secure qua route xem thử có kiểm quyền. Không nhúng HTML/key vào text câu trả lời hoặc public metadata. Nhánh reuse phải có Player thật và giữ nguyên hash HTML.

`ExamQuestion` nội bộ: `{id,type,text,choices:[{key,text}],answer,explanation,sourceRefs:[]}`. `type` chỉ single hoặc truefalse theo runtime. `sourceRefs` trỏ documentId + vị trí đoạn/trang hoặc đánh dấu AI tự sinh, không bịa nguồn. Chuyển sang format văn bản repo bằng hàm duy nhất; ký tự `|`, xuống dòng, lựa chọn rỗng và lựa chọn trùng phải được phát hiện/xử lý rõ, không làm mất nghĩa.

`GameResult`:

```text
  generationMode, playerId, examId|null, modelId|null, appId, playUrl
  controls: {mouse:true, modelKind:string|null}
  approval: {teacher:accepted, proposalVersion:int,
             playerModeration:draft|pending|approved|refused|hidden}
```

Các ID của result do server ghi/lấy từ DB. Chỉ trả ready sau khi đủ cổng kiểm tra. Game thuần danh sách không bắt buộc Exam. Model null chỉ hợp lệ với Player/API cho phép; không giả định Player có inputs được bỏ model.

## 5. Kết quả kiểm tra và lỗi

```text
ValidationResult:
  overall: passed|failed|not_checked
  checks: [{name, status:passed|failed|not_checked,
            required:boolean, reason, evidenceRef:string|null}]
  warnings: [{code,message,line?,excerpt?}]
ChatError:
  code, stage, message, retryable:boolean, details:object
```

Tên checks: schema, permissions, examFormat, contentGrounding, answerReview, compatibility, htmlContract, codeSafety, runtime, mouseFallback, teacherApproval. LLM tự nói “đạt” không phải bằng chứng. Người duyệt kiến thức phải xem câu hỏi/đáp án và nguồn; phát hiện không chắc thì trả needs_revision, không chứng nhận đúng tuyệt đối.

Mã lỗi tối thiểu: invalid_input, stale_version, forbidden_resource, incompatible_model, incompatible_exam, unsupported_interaction, document_rejected, invalid_model_output, model_unavailable, validation_failed, persistence_failed.

## 6. Hợp đồng nền tảng phải giữ

- Tạo App dùng các trường hiện có `name, description, playerId, modelId, mapping, examId, content, sure, holdMs, share` và kiểm bằng `clean_app`.
- sure 0.5..0.99, holdMs 300..5000; không bịa lớp hoặc gắn một lớp vào nhiều input.
- Model điều khiển hỗ trợ chạy: image/pose/hands; audio chỉ lưu, chưa cho chọn như khả năng hoạt động.
- Game gửi ready; nhận camera.init/camera.result/camera.status; kết thúc gửi finish. HTML kiểm nguồn thông điệp từ parent.
- Câu hỏi truyền qua camera.init; không nhúng câu hỏi giảng dạy cố định vào HTML mới.
- App mới mặc định share=false. Giáo viên duyệt khác với Admin duyệt Player; không nâng draft thành approved.
- PUT App là cập nhật toàn cấu hình, không gửi riêng examId. Cần sửa lỗi JSON hóa mapping trước nghiệm thu chức năng revision.
- Khi sửa một Exam dùng chung, phải cho biết tác động; mặc định tạo/chọn Exam khác nếu người dùng chỉ muốn đổi đề của một App.

## 7. Tài liệu đính kèm

G0/đợt tài liệu phải công bố định dạng, giới hạn byte/trang/ký tự, thời hạn lưu và lỗi. Triển khai nội dung dán/TXT trước; PDF/DOCX tiếp theo, không đánh dấu hoàn thành nếu hai định dạng này bị bỏ mà chưa được người dùng chấp thuận.

Upload nằm trong phạm vi user, kiểm MIME/chữ ký và kích thước; không tự tải URL tùy ý, không thực thi macro/script. PDF scan cần OCR: nếu chưa có, báo rõ và đề nghị tài liệu có lớp chữ, không trả nội dung rỗng như đã đọc thành công.
