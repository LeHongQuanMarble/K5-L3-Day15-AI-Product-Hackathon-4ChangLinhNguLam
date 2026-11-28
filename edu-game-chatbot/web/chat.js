// Giao diện chat (T20). JS thuần, không framework, không CDN.
"use strict";

const state = { sessionId: null, sessionState: null, eventSource: null };

/** Khởi động: lấy ?session= hoặc localStorage; không có thì createSession(). Gắn sự kiện form/attach. */
async function init() { throw new Error("TODO"); }

/** POST /api/sessions -> lưu id vào localStorage + URL, render lời chào. */
async function createSession() { throw new Error("TODO"); }

/** GET /api/sessions/{id} -> render toàn bộ messages + setState. 404 -> createSession(). */
async function loadSession(sessionId) { throw new Error("TODO"); }

/** Mở EventSource /api/sessions/{id}/events; xử lý type message/progress/state; tự kết nối lại khi lỗi. */
function connectEvents(sessionId) { throw new Error("TODO"); }

/** POST /messages {text}; hiển thị ngay bong bóng người dùng. */
async function sendText(text) { throw new Error("TODO"); }

/** POST /messages {action}; vô hiệu hoá nhóm nút vừa bấm. */
async function sendAction(buttonId, label) { throw new Error("TODO"); }

/** POST /files (multipart) với các file đã chọn. */
async function uploadFiles(fileList) { throw new Error("TODO"); }

/** Vẽ 1 message (bot/user) + nút (renderButtons) + preview (renderPreview) nếu có. */
function renderMessage(message) { throw new Error("TODO"); }

/** Vẽ nhóm quick-reply; click -> sendAction. */
function renderButtons(container, buttons) { throw new Error("TODO"); }

/** Hiện iframe chơi thử với url, cập nhật link 'Mở toàn màn hình'. */
function renderPreview(url) { throw new Error("TODO"); }

/** Cập nhật thanh tiến độ (ẩn khi rỗng). */
function renderProgress(text) { throw new Error("TODO"); }

/** Lưu state; bật/tắt nút đính kèm (chỉ AWAIT_SOURCE_INPUT), khoá ô nhập khi bận/kết thúc, hiện link zip khi DONE. */
function setState(newState) { throw new Error("TODO"); }

/** Escape HTML trước khi chèn text vào DOM. */
function escapeHtml(text) { throw new Error("TODO"); }

document.addEventListener("DOMContentLoaded", init);
