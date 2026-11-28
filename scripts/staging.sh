#!/usr/bin/env bash
# Staging của AI Lab: một lệnh để chạy, dừng, kiểm. Chạy từ bất cứ đâu trong repo:
#   bash scripts/staging.sh all       MỘT LỆNH CHO CẢ DỰ ÁN: .env → unittest → chạy server → smoke → in địa chỉ + mật khẩu
#   bash scripts/staging.sh up        chạy nền, chờ /health, in địa chỉ (lần đầu: in mật khẩu admin nếu chưa đặt)
#   bash scripts/staging.sh down      dừng
#   bash scripts/staging.sh restart   dừng rồi chạy lại
#   bash scripts/staging.sh status    đang chạy chưa, model giả hay thật
#   bash scripts/staging.sh test      unittest (không cần server)
#   bash scripts/staging.sh smoke     bộ kiểm 24 bước trên server đang chạy (cần AILAB_ADMIN_PASSWORD)
#   bash scripts/staging.sh logs      xem log
#   bash scripts/staging.sh backup    sao lưu file DB sang ailab/data/backup-<giờ>.db
#   bash scripts/staging.sh reset     chuyển dữ liệu cũ sang ailab/data/old-<giờ>/ (KHÔNG xoá), lần chạy sau là DB mới
#   bash scripts/staging.sh deps      (tuỳ chọn) tạo .venv và cài Playwright cho tính năng Train mô hình; staging.sh tự dùng .venv nếu có
#   bash scripts/staging.sh check     kiểm máy: Python, curl, Chrome, Playwright, .env, model thật hay giả (không chạy gì)
# Biến môi trường: AILAB_HOST (127.0.0.1) · AILAB_PORT (8800) · AILAB_DB · AILAB_ADMIN_PASSWORD · AILAB_COOKIE_SECURE · AILAB_DEMO · AILAB_CHROME · MODEL_PROVIDER/MODEL_NAME/API_KEY (.env).
# Lõi chỉ dùng thư viện chuẩn Python 3.10+; chỉ tính năng Train mô hình cần Playwright (bash scripts/staging.sh deps). Không ghi mật khẩu hay key vào file nào của repo.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1
HOST="${AILAB_HOST:-127.0.0.1}"; PORT="${AILAB_PORT:-8800}"
DATA="$ROOT/ailab/data"; PIDF="$DATA/staging.pid"; LOG="$DATA/staging.log"
URL="http://$HOST:$PORT"
[ "$HOST" = "0.0.0.0" ] && URL="http://127.0.0.1:$PORT"

if [ -x "$ROOT/.venv/bin/python" ]; then PY="$ROOT/.venv/bin/python"; else PY="$(command -v python3 || command -v python || true)"; fi
[ -n "$PY" ] || { echo "Không thấy python3. Cần Python 3.10+." >&2; exit 1; }
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' || { echo "Cần Python 3.10 trở lên (máy có $("$PY" -V 2>&1))." >&2; exit 1; }

running() { [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; }
healthy() { curl -fsS "$URL/health" 2>/dev/null | grep -q '"ok": true'; }

cmd_up() {
  if running; then echo "Đã chạy (pid $(cat "$PIDF")) → $URL"; return 0; fi
  if healthy; then echo "Cổng $PORT đã có server khác trả lời /health (không phải do script này chạy). Đổi AILAB_PORT hoặc dừng nó trước." >&2; return 1; fi
  mkdir -p "$DATA"
  # -u: log không bị đệm, để thấy mật khẩu admin tự sinh ngay
  nohup "$PY" -u ailab/server.py >"$LOG" 2>&1 &
  echo $! >"$PIDF"
  for _ in $(seq 1 40); do
    if healthy; then break; fi
    running || { echo "Server tắt ngay sau khi chạy. Log:" >&2; tail -n 20 "$LOG" >&2; rm -f "$PIDF"; return 1; }
    sleep 0.25
  done
  healthy || { echo "Quá 10 giây mà /health chưa trả lời. Log:" >&2; tail -n 20 "$LOG" >&2; return 1; }
  echo "Đã chạy (pid $(cat "$PIDF")) → $URL"
  grep -E "Model AI|mật khẩu|password" -i "$LOG" | sed 's/^/  /'
  echo "  Đăng nhập: admin. Mật khẩu: AILAB_ADMIN_PASSWORD bạn đặt, hoặc dòng in ở trên (chỉ in một lần, ở $LOG)."
}

cmd_down() {
  if ! running; then echo "Không có server do script này chạy."; rm -f "$PIDF"; return 0; fi
  kill "$(cat "$PIDF")" 2>/dev/null
  for _ in $(seq 1 20); do running || break; sleep 0.25; done
  running && { echo "Server chưa dừng, gửi kill -9."; kill -9 "$(cat "$PIDF")" 2>/dev/null; }
  rm -f "$PIDF"; echo "Đã dừng."
}

cmd_status() {
  if running; then echo "Đang chạy (pid $(cat "$PIDF")) → $URL"; else echo "Không chạy."; fi
  if healthy; then echo "/health: ok"; else echo "/health: không trả lời"; fi
  [ -f "$LOG" ] && grep -E "Model AI" "$LOG" | tail -n 1
  return 0
}

cmd_smoke() {
  : "${AILAB_ADMIN_PASSWORD:?Đặt AILAB_ADMIN_PASSWORD (mật khẩu tài khoản admin) rồi chạy lại}"
  healthy || { echo "Server chưa chạy: bash scripts/staging.sh up" >&2; return 1; }
  BASE="$URL" ADMIN_PASSWORD="$AILAB_ADMIN_PASSWORD" bash ailab/smoke.sh
}

cmd_backup() {
  [ -f "${AILAB_DB:-$DATA/ailab.db}" ] || { echo "Chưa có file DB để sao lưu." >&2; return 1; }
  OUT="$DATA/backup-$(date +%Y%m%d-%H%M%S).db"
  # dùng backup của SQLite (an toàn khi server đang ghi), không chép file thô
  "$PY" -c 'import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()' "${AILAB_DB:-$DATA/ailab.db}" "$OUT" && echo "Đã sao lưu → $OUT (nằm trong ailab/data/, không commit)"
}

cmd_reset() {
  running && { echo "Dừng server trước: bash scripts/staging.sh down" >&2; return 1; }
  [ -d "$DATA" ] || { echo "Chưa có dữ liệu."; return 0; }
  OLD="$DATA/old-$(date +%Y%m%d-%H%M%S)"; mkdir -p "$OLD"
  DBF="${AILAB_DB:-$DATA/ailab.db}"
  for f in "$DBF" "$DBF-journal" "$LOG"; do [ -e "$f" ] && mv "$f" "$OLD"/; done
  echo "Dữ liệu cũ chuyển sang $OLD. Lần chạy sau tạo DB mới và admin mới. Xoá hẳn thì tự xoá thư mục đó khi chắc chắn."
}

cmd_deps() {
  SYS="$(command -v python3 || command -v python)"
  [ -x "$ROOT/.venv/bin/python" ] || "$SYS" -m venv "$ROOT/.venv" || { echo "Không tạo được .venv (Debian/Ubuntu: sudo apt install python3-venv)." >&2; return 1; }
  "$ROOT/.venv/bin/python" -m pip install -q -r ailab/train_worker/requirements.txt && echo "Đã cài Playwright vào .venv (không cần 'playwright install', dùng Chrome có sẵn)."
}

cmd_check() {
  echo "Python:     $("$PY" -V 2>&1) ($PY)"
  command -v curl >/dev/null && echo "curl:       có" || echo "curl:       THIẾU (cần cho smoke và /health)"
  CH="${AILAB_CHROME:-$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)}"
  [ -n "$CH" ] && echo "Chrome:     $CH" || echo "Chrome:     không thấy (chỉ cần cho Train mô hình; đặt AILAB_CHROME)"
  "$PY" -c 'import playwright' 2>/dev/null && echo "Playwright: có (Train mô hình dùng được)" || echo "Playwright: chưa cài (Train mô hình báo 'chưa cài bộ train'; cài: bash scripts/staging.sh deps)"
  [ -f .env ] && echo ".env:       có" || echo ".env:       chưa có (staging.sh all sẽ tạo từ .env.example)"
  P="$(grep -E '^MODEL_PROVIDER=' .env 2>/dev/null | cut -d= -f2)"
  case "$P" in ""|fake) echo "Model:      GIẢ (chatbot dựng từ khuôn có sẵn)";; *) echo "Model:      $P (thật, cần API_KEY)";; esac
  return 0
}

cmd_all() {
  cmd_check; echo
  # Một lệnh cho cả dự án: .env → unittest → chạy server → smoke → in cách vào.
  if [ ! -f .env ]; then cp .env.example .env && echo "Đã tạo .env từ .env.example (chưa có model thật → chatbot ở chế độ GIẢ). .env không bị commit."; fi
  DBF="${AILAB_DB:-$DATA/ailab.db}"; GEN=0
  if [ -z "${AILAB_ADMIN_PASSWORD:-}" ] && [ ! -f "$DBF" ]; then
    AILAB_ADMIN_PASSWORD="$("$PY" -c 'import secrets; print(secrets.token_urlsafe(9))')"; export AILAB_ADMIN_PASSWORD; GEN=1
  fi
  echo "== 1/3 unittest"
  UT="$("$PY" -m unittest discover -s ailab -p "test_*.py" 2>&1)" || { echo "$UT" | tail -n 25 >&2; echo "unittest trượt, dừng." >&2; return 1; }
  echo "$UT" | tail -n 3
  echo "== 2/3 chạy server"; cmd_up || return 1
  if [ -n "${AILAB_ADMIN_PASSWORD:-}" ] && [ -z "${SKIP_SMOKE:-}" ]; then
    echo "== 3/3 smoke (tạo vài tài khoản smoke_user_* trong DB staging; đặt SKIP_SMOKE=1 để bỏ qua)"
    BASE="$URL" ADMIN_PASSWORD="$AILAB_ADMIN_PASSWORD" bash ailab/smoke.sh | tail -n 3 || { echo "smoke trượt, xem log: bash scripts/staging.sh logs" >&2; return 1; }
  else
    echo "== 3/3 bỏ qua smoke (DB đã có sẵn và chưa đặt AILAB_ADMIN_PASSWORD, hoặc SKIP_SMOKE=1)"
  fi
  echo
  echo "AI Lab đang chạy: $URL"
  if [ "$GEN" = 1 ]; then echo "Đăng nhập: admin / $AILAB_ADMIN_PASSWORD   (mật khẩu tự sinh cho lần chạy đầu, chép lại, sẽ không in lại)"
  else echo "Đăng nhập: admin / mật khẩu bạn đã đặt"; fi
  grep -E "Model AI" "$LOG" | tail -n 1 | sed 's/^/  /'
  echo "Dừng: bash scripts/staging.sh down"
}

case "${1:-}" in
  all) cmd_all ;;
  up) cmd_up ;;
  down) cmd_down ;;
  restart) cmd_down; cmd_up ;;
  status) cmd_status ;;
  test) "$PY" -m unittest discover -s ailab -p "test_*.py" ;;
  smoke) cmd_smoke ;;
  logs) [ -f "$LOG" ] && tail -n 50 -f "$LOG" || echo "Chưa có log." ;;
  backup) cmd_backup ;;
  reset) cmd_reset ;;
  deps) cmd_deps ;;
  check) cmd_check ;;
  *) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; [ -z "${1:-}" ] || exit 2 ;;
esac
