/* Video giới thiệu (motion) — bản trình chiếu của JULY Aura, chạy bằng Trình phát (Motion Player) của learning:
 *   ailab/web/motion-player/ = trang chủ trình phát + gói f6d33432fb61 (chép từ learning/apps/web/public/motion-player)
 *   ailab/web/motion/*.html  = 3 bài: tổng quan JULY Aura · Aura Flow (tư thế) · Aura Echo (âm thanh) (chép từ july-aura-staging)
 * Trang trình phát nhúng bài học, giao gói trình phát cho bài và vẽ nút điều khiển. */
import { h, modal } from './dom.js';

export var INTROS = {
  overview: { title: 'JULY Aura: tổng quan', file: '/motion/aura-tong-quan.html' },
  pose: { title: 'Aura Flow: giới thiệu mô hình tư thế', file: '/motion/aura-flow.html' },
  audio: { title: 'Aura Echo: giới thiệu mô hình âm thanh', file: '/motion/aura-echo.html' }
};

export function showIntro(key) {
  var it = INTROS[key];
  if (!it) return;
  var src = '/motion-player/index.html?lesson=' + encodeURIComponent(location.origin + it.file);
  var frame = h('iframe', { class: 'ail-motion-frame', title: it.title, allow: 'autoplay; fullscreen', allowfullscreen: true });
  modal(it.title, h('div', { class: 'ail-motion-wrap' }, frame), { cls: 'ail-motion', label: 'Video giới thiệu: ' + it.title });
  /* nạp sau khi hộp thoại đã dàn xong, để trình phát đo đúng khung (đo lúc hộp còn đang mở sẽ lệch tỉ lệ) */
  setTimeout(function () { frame.src = src; }, 350);
}
