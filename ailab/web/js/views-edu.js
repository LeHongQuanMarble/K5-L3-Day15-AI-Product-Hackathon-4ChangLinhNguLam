/* views-edu.js — nhúng Chatbot tạo game học tập (edu-game-chatbot) vào AI Lab.
   Địa chỉ lấy từ /api/me → edu_chatbot (biến môi trường AILAB_EDU_CHATBOT_URL, mặc định http://127.0.0.1:8000).
   Chatbot là một máy chủ riêng; trang này chỉ đặt nó trong iframe và có nút mở ở tab mới. */
import { h, ico } from './dom.js';

var DEFAULT_URL = 'http://127.0.0.1:8000';

export function eduView(c) {
  var url = c.eduUrl || DEFAULT_URL;
  var frame = h('iframe', {
    class: 'ail-edu-frame', src: url, title: 'Chatbot tạo game học tập',
    allow: 'camera; microphone; autoplay; clipboard-write; fullscreen',
    referrerpolicy: 'no-referrer'
  });
  var offline = h('div', { class: 'ail-edu-offline', hidden: true },
    h('strong', null, 'Chưa kết nối được Chatbot tạo game.'),
    h('p', null, 'Hãy chạy chatbot (trong thư mục edu-game-chatbot: ',
      h('code', null, 'uvicorn app.main:create_app --factory --port 8000'),
      ') rồi bấm Tải lại. Địa chỉ đang dùng: ', h('code', null, url)));
  /* iframe khác origin không báo lỗi tải; thử gọi nhẹ để hiện hướng dẫn khi chatbot chưa chạy */
  fetch(url, { mode: 'no-cors', cache: 'no-store' }).catch(function () { offline.hidden = false; });

  var bar = h('div', { class: 'ail-edu-bar' },
    h('div', { class: 'ail-edu-title' }, ico('sparkles'),
      h('div', null, h('strong', null, 'Chatbot tạo game học tập'),
        h('span', { class: 'ail-edu-sub' }, 'Hỏi đủ câu hỏi, cách chơi, điều khiển, giao diện rồi tạo game có chấm điểm'))),
    h('div', { class: 'ail-edu-actions' },
      h('button', { type: 'button', class: 'ail-btn ghost sm', onclick: function () { offline.hidden = true; frame.src = url; fetch(url, { mode: 'no-cors', cache: 'no-store' }).catch(function () { offline.hidden = false; }); } }, ico('refresh'), 'Tải lại'),
      h('a', { class: 'ail-btn pri sm', href: url, target: '_blank', rel: 'noopener' }, ico('external'), 'Mở tab mới')));

  c.mount(h('section', { class: 'ail-edu', 'aria-label': 'Chatbot tạo game học tập' }, bar, offline, frame));
}
