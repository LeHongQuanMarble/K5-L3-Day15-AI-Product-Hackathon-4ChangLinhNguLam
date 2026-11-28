// Giao diện chat (T20). JS thuần, không framework, không CDN.
"use strict";

const state = { sessionId: null, sessionState: null, eventSource: null, seen: new Set(), versions: new Map(), current: null };
const BUSY = ["BUILDING_QUESTIONS", "READY_TO_DESIGN", "PIPELINE_RUNNING", "EXPORTING"];
const TERMINAL = ["DONE", "REJECTED", "CANCELLED"];
const KEY = "edu_game_session";
const PIPELINE = ["READY_TO_DESIGN", "PIPELINE_RUNNING"];
const STEP_OF = {
  AWAIT_REQUEST: 0, REJECTED: 0, AWAIT_SOURCE: 1, AWAIT_SOURCE_INPUT: 1, BUILDING_QUESTIONS: 1,
  AWAIT_QUESTION_APPROVAL: 1, READY_TO_DESIGN: 2, PIPELINE_RUNNING: 2, AWAIT_REVIEW: 3,
  AWAIT_REVISION_TEXT: 3, EXPORTING: 4, DONE: 5,
};

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
  initGamePane();
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
    resetUi();
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
    resetUi();
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
  es.onopen = () => resync(sessionId);
  es.onmessage = parse(null);
  for (const t of ["message", "progress", "state"]) es.addEventListener(t, parse(t));
  es.onerror = () => {
    es.close();
    setTimeout(() => {
      if (state.eventSource === es && state.sessionId === sessionId) connectEvents(sessionId);
    }, 2000);
  };
}

/** Sau khi SSE (re)connect: lấy lại phiên, vẽ message bot bị lỡ trong lúc chưa kết nối, cập nhật state. */
async function resync(sessionId) {
  try {
    const r = await fetch(api("/" + encodeURIComponent(sessionId)));
    if (!r.ok || state.sessionId !== sessionId) return;
    const data = await r.json();
    (data.messages || []).filter((m) => m.role !== "user").forEach(renderMessage);
    setState(data.state);
  } catch (e) { /* lần kết nối sau sẽ thử lại */ }
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
  if (message.preview_url) {
    renderPreview(message.preview_url);
    const go = document.createElement("button");
    go.type = "button";
    go.className = "msg__open-game";
    const n = versionOf(message.preview_url);
    go.textContent = "🎮 Xem game" + (n ? " v" + n : "");
    go.addEventListener("click", () => { selectVersion(n); setView("game"); });
    el.insertBefore(go, el.querySelector(".buttons"));
  }
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

/** Ghi nhận phiên bản mới từ preview_url và hiện nó trong khung Game demo. */
function renderPreview(url) {
  const n = versionOf(url) || state.versions.size + 1;
  const isNew = !state.versions.has(n);
  state.versions.set(n, url);
  renderVersionList();
  selectVersion(n);
  if (isNew && !isWide()) $("tab-game-dot").hidden = $("layout").dataset.view === "game";
}

function versionOf(url) { const m = /\/v(\d+)(?:[/?#]|$)/.exec(url || ""); return m ? Number(m[1]) : 0; }

function renderVersionList() {
  const box = $("version-list");
  box.innerHTML = "";
  [...state.versions.keys()].sort((a, b) => a - b).forEach((n) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = "v" + n;
    b.className = n === state.current ? "is-active" : "";
    b.addEventListener("click", () => selectVersion(n));
    box.appendChild(b);
  });
}

/** Hiện iframe của phiên bản n, cập nhật link 'Mở toàn màn hình'. */
function selectVersion(n) {
  const url = state.versions.get(n);
  if (!url) return;
  state.current = n;
  const frame = $("preview-frame");
  if (frame.getAttribute("src") !== url) frame.src = url;
  const open = $("preview-open");
  open.href = url;
  open.removeAttribute("aria-disabled");
  $("preview-reload").disabled = false;
  $("preview").hidden = false;
  $("game-empty").hidden = true;
  renderVersionList();
}

function isWide() { return window.matchMedia("(min-width: 901px)").matches; }

/** Màn hình hẹp: chuyển giữa khung chat và khung game. */
function setView(view) {
  $("layout").dataset.view = view;
  $("tab-chat").classList.toggle("is-active", view === "chat");
  $("tab-game").classList.toggle("is-active", view === "game");
  $("tab-chat").setAttribute("aria-selected", String(view === "chat"));
  $("tab-game").setAttribute("aria-selected", String(view === "game"));
  if (view === "game") $("tab-game-dot").hidden = true;
}

function setDevice(device) {
  $("device").className = "device device--" + device;
  $("device-desktop").classList.toggle("is-active", device === "desktop");
  $("device-mobile").classList.toggle("is-active", device === "mobile");
}

function initGamePane() {
  $("tab-chat").addEventListener("click", () => setView("chat"));
  $("tab-game").addEventListener("click", () => setView("game"));
  $("device-desktop").addEventListener("click", () => setDevice("desktop"));
  $("device-mobile").addEventListener("click", () => setDevice("mobile"));
  $("preview-reload").addEventListener("click", () => {
    const url = state.versions.get(state.current);
    if (url) $("preview-frame").src = url + (url.includes("?") ? "&" : "?") + "r=" + Date.now();
  });
  $("new-session").addEventListener("click", () => {
    const ended = TERMINAL.includes(state.sessionState) || state.sessionState === "AWAIT_REQUEST";
    if (!ended && !confirm("Bắt đầu phiên mới? Cuộc trò chuyện hiện tại vẫn được lưu và mở lại được bằng đường link cũ.")) return;
    startNewSession();
  });
}

/** Xoá giao diện về trạng thái trống trước khi vẽ một phiên. */
function resetUi() {
  $("messages").innerHTML = "";
  state.seen.clear();
  state.versions.clear();
  state.current = null;
  renderVersionList();
  const frame = $("preview-frame");
  frame.removeAttribute("src");
  $("preview").hidden = true;
  $("game-empty").hidden = false;
  $("preview-open").removeAttribute("href");
  $("preview-open").setAttribute("aria-disabled", "true");
  $("preview-reload").disabled = true;
  $("game-download").hidden = true;
  $("tab-game-dot").hidden = true;
  renderProgress("");
  setView("chat");
}

/** Phiên đã kết thúc (DONE/REJECTED/CANCELLED): hiện nút bắt đầu phiên mới ngay trong khung chat. */
function renderRestart(show) {
  let box = $("restart-box");
  if (!show) { if (box) box.remove(); return; }
  if (!box) {
    box = document.createElement("div");
    box.id = "restart-box";
    box.className = "restart";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn--primary";
    btn.setAttribute("data-testid", "restart-session");
    btn.textContent = "＋ Bắt đầu phiên mới";
    btn.addEventListener("click", startNewSession);
    box.appendChild(btn);
  }
  $("messages").appendChild(box);
  scrollDown();
}

function startNewSession() {
  if (state.eventSource) state.eventSource.close();
  state.eventSource = null;
  createSession();
}

function renderStepper(newState) {
  const step = STEP_OF[newState] ?? -1;
  document.querySelectorAll("#stepper li").forEach((li) => {
    const i = Number(li.dataset.step);
    li.classList.toggle("is-done", step > i);
    li.classList.toggle("is-current", step === i);
  });
}

/** Cập nhật thanh tiến độ (ẩn khi rỗng). */
function renderProgress(text) {
  const p = $("progress");
  p.textContent = text || "";
  p.hidden = !text;
  if (text) $("game-loading-text").textContent = text;
}

/** Lưu state; bật/tắt nút đính kèm (chỉ AWAIT_SOURCE_INPUT), khoá ô nhập khi bận/kết thúc, hiện link zip khi DONE. */
function setState(newState) {
  state.sessionState = newState;
  const busy = BUSY.includes(newState);
  const locked = busy || TERMINAL.includes(newState);
  $("attach-btn").hidden = newState !== "AWAIT_SOURCE_INPUT";
  $("attach-btn").disabled = busy;
  $("text-input").disabled = locked;
  $("text-input").placeholder = TERMINAL.includes(newState)
    ? "Phiên đã kết thúc — bấm “Bắt đầu phiên mới” để tạo game khác"
    : busy ? "Trợ lý đang xử lý, vui lòng chờ…" : "Nhập tin nhắn cho trợ lý…";
  renderRestart(TERMINAL.includes(newState));
  $("send-btn").disabled = locked;
  if (!busy) renderProgress("");
  renderStepper(newState);
  const building = PIPELINE.includes(newState);
  $("game-loading").hidden = !building;
  $("game-empty").hidden = building || state.versions.size > 0;
  $("game-pane").classList.toggle("game-pane--loading", building);
  if (!building) $("game-loading-text").textContent = "Đang tạo game…";
  const zip = api("/" + encodeURIComponent(state.sessionId) + "/export.zip");
  $("game-download").hidden = newState !== "DONE";
  if (newState === "DONE") $("game-download").href = zip;
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
