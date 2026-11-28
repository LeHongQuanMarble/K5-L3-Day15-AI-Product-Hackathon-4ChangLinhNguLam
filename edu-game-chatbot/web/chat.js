// Giao diện chat (T20). JS thuần, không framework, không CDN.
"use strict";

const state = { sessionId: null, sessionState: null, eventSource: null, seen: new Set() };
const BUSY = ["BUILDING_QUESTIONS", "READY_TO_DESIGN", "PIPELINE_RUNNING", "EXPORTING"];
const TERMINAL = ["DONE", "REJECTED", "CANCELLED"];
const KEY = "edu_game_session";

const $ = (id) => document.getElementById(id);
const api = (path) => "/api/sessions" + path;
const JSON_HEADERS = { "Content-Type": "application/json" };

function storeGet() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
function storeSet(v) { try { localStorage.setItem(KEY, v); } catch (e) { /* bỏ qua */ } }

function scrollDown() { const c = $("chat"); c.scrollTop = c.scrollHeight; }

/** Khởi động: lấy ?session= hoặc localStorage; không có thì createSession(). Gắn sự kiện form/attach. */
async function init() {
  $("composer").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = $("text-input");
    const text = input.value.trim();
    if (!text || input.disabled) return;
    input.value = "";
    sendText(text);
  });
  $("attach-btn").addEventListener("click", () => $("file-input").click());
  $("file-input").addEventListener("change", (e) => {
    if (e.target.files.length) uploadFiles(e.target.files);
    e.target.value = "";
  });
  const id = new URLSearchParams(location.search).get("session") || storeGet();
  if (id) await loadSession(id); else await createSession();
}

function useSession(id) {
  state.sessionId = id;
  storeSet(id);
  const url = new URL(location.href);
  url.searchParams.set("session", id);
  history.replaceState(null, "", url);
}

function showError(text) { renderMessage({ id: "local-err" + Date.now(), role: "system", text }); }

/** POST /api/sessions -> lưu id vào localStorage + URL, render lời chào. */
async function createSession() {
  try {
    const r = await fetch(api(""), { method: "POST" });
    if (!r.ok) throw new Error(r.status);
    const data = await r.json();
    useSession(data.id);
    $("messages").innerHTML = "";
    state.seen.clear();
    (data.messages || []).forEach(renderMessage);
    setState(data.state || "AWAIT_REQUEST");
    connectEvents(data.id);
  } catch (e) {
    showError("Không thể tạo phiên mới. Vui lòng tải lại trang.");
  }
}

/** GET /api/sessions/{id} -> render toàn bộ messages + setState. 404 -> createSession(). */
async function loadSession(sessionId) {
  try {
    const r = await fetch(api("/" + encodeURIComponent(sessionId)));
    if (r.status === 404) return createSession();
    if (!r.ok) throw new Error(r.status);
    const data = await r.json();
    useSession(sessionId);
    $("messages").innerHTML = "";
    state.seen.clear();
    (data.messages || []).forEach(renderMessage);
    setState(data.state);
    connectEvents(sessionId);
  } catch (e) {
    showError("Không thể tải phiên trò chuyện. Vui lòng thử lại.");
  }
}

function handleEvent(d) {
  if (d.type === "message" && d.message) { renderProgress(""); renderMessage(d.message); }
  else if (d.type === "progress") renderProgress(d.text || "");
  else if (d.type === "state") setState(d.state);
}

/** Mở EventSource /api/sessions/{id}/events; xử lý type message/progress/state; tự kết nối lại khi lỗi. */
function connectEvents(sessionId) {
  if (state.eventSource) state.eventSource.close();
  const es = new EventSource(api("/" + encodeURIComponent(sessionId) + "/events"));
  state.eventSource = es;
  const parse = (fallbackType) => (ev) => {
    let d;
    try { d = JSON.parse(ev.data); } catch (e) { return; }
    if (!d.type) d.type = fallbackType;
    handleEvent(d);
  };
  es.onmessage = parse(null);
  for (const t of ["message", "progress", "state"]) es.addEventListener(t, parse(t));
  es.onerror = () => {
    es.close();
    setTimeout(() => {
      if (state.eventSource === es && state.sessionId === sessionId) connectEvents(sessionId);
    }, 2000);
  };
}

async function post(path, opts) {
  try {
    const r = await fetch(api("/" + encodeURIComponent(state.sessionId) + path), opts);
    if (!r.ok) throw new Error(r.status);
    return true;
  } catch (e) {
    showError("Gửi không thành công. Vui lòng thử lại.");
    return false;
  }
}

/** POST /messages {text}; hiển thị ngay bong bóng người dùng. */
async function sendText(text) {
  renderMessage({ id: "local-" + Date.now(), role: "user", text });
  await post("/messages", { method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ text }) });
}

/** POST /messages {action}; vô hiệu hoá nhóm nút vừa bấm. */
async function sendAction(buttonId, label) {
  renderMessage({ id: "local-" + Date.now(), role: "user", text: label });
  await post("/messages", { method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ action: buttonId }) });
}

/** POST /files (multipart) với các file đã chọn. */
async function uploadFiles(fileList) {
  const fd = new FormData();
  const names = [];
  for (const f of fileList) { fd.append("files", f); names.push(f.name); }
  renderMessage({ id: "local-" + Date.now(), role: "user", text: "Đã đính kèm: " + names.join(", ") });
  await post("/files", { method: "POST", body: fd });
}

/** Vẽ 1 message (bot/user) + nút (renderButtons) + preview (renderPreview) nếu có. */
function renderMessage(message) {
  const id = message.id ? String(message.id) : "";
  if (id && !id.startsWith("local-")) {
    if (state.seen.has(id)) return;
    state.seen.add(id);
  }
  const role = message.role === "user" ? "user" : message.role === "system" ? "system" : "bot";
  const el = document.createElement("div");
  el.className = "msg msg--" + role;
  el.setAttribute("data-testid", "msg-" + role);
  const p = document.createElement("div");
  p.className = "msg__text";
  p.innerHTML = escapeHtml(message.text || "").replace(/\n/g, "<br>");
  el.appendChild(p);
  if (message.buttons && message.buttons.length) renderButtons(el, message.buttons);
  $("messages").appendChild(el);
  if (message.preview_url) renderPreview(message.preview_url);
  scrollDown();
}

/** Vẽ nhóm quick-reply; click -> sendAction. */
function renderButtons(container, buttons) {
  const box = document.createElement("div");
  box.className = "buttons";
  box.setAttribute("data-testid", "buttons");
  for (const b of buttons) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = b.label;
    btn.dataset.buttonId = b.id;
    btn.setAttribute("data-testid", "btn-" + b.id);
    btn.addEventListener("click", () => {
      box.querySelectorAll("button").forEach((x) => { x.disabled = true; });
      sendAction(b.id, b.label);
    });
    box.appendChild(btn);
  }
  container.appendChild(box);
}

/** Hiện iframe chơi thử với url, cập nhật link 'Mở toàn màn hình'. */
function renderPreview(url) {
  $("preview-frame").src = url;
  $("preview-open").href = url;
  $("preview").hidden = false;
}

/** Cập nhật thanh tiến độ (ẩn khi rỗng). */
function renderProgress(text) {
  const p = $("progress");
  p.textContent = text || "";
  p.hidden = !text;
}

/** Lưu state; bật/tắt nút đính kèm (chỉ AWAIT_SOURCE_INPUT), khoá ô nhập khi bận/kết thúc, hiện link zip khi DONE. */
function setState(newState) {
  state.sessionState = newState;
  const busy = BUSY.includes(newState);
  const locked = busy || TERMINAL.includes(newState);
  $("attach-btn").hidden = newState !== "AWAIT_SOURCE_INPUT";
  $("attach-btn").disabled = busy;
  $("text-input").disabled = locked;
  $("send-btn").disabled = locked;
  if (!busy) renderProgress("");
  let link = $("download-zip");
  if (newState === "DONE") {
    if (!link) {
      link = document.createElement("a");
      link.id = "download-zip";
      link.setAttribute("data-testid", "download-zip");
      link.textContent = "Tải về .zip";
      link.className = "download";
      $("messages").appendChild(link);
    }
    link.href = api("/" + encodeURIComponent(state.sessionId) + "/export.zip");
    scrollDown();
  } else if (link) {
    link.remove();
  }
}

/** Escape HTML trước khi chèn text vào DOM. */
function escapeHtml(text) {
  return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

document.addEventListener("DOMContentLoaded", init);
