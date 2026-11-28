/* Ba loại mô hình (Hình ảnh · Tư thế · Âm thanh) — tái sử dụng từ learning:
 *   ảnh minh hoạ và khung xương: packages/train-builder/src/kindart (ảnh Wikimedia CC0, phổ tụ âm do sinh ra)
 *   chữ: packages/train-builder/src/i18n.vi.json (kind.hint, kindArt, classes.help, sound.help)
 *   thẻ chọn loại: KindChooser.tsx. Ở đây viết lại thành JS thuần để dùng trong AI Lab (không React). */
import { h, ico } from './dom.js';

/**
 * The 33 body points a pose model finds in kindart/pose.jpg (MediaPipe Pose Landmarker, full model; the student with the raised hand), as
 * fractions of the photo's width and height. Drawn as the skeleton on the kind's picture: the result a Pose model gives, not a drawing.
 */
export const POSE_POINTS = [
  [0.7596, 0.4072],
  [0.7747, 0.3966],
  [0.7784, 0.3989],
  [0.7829, 0.402],
  [0.7696, 0.3935],
  [0.7696, 0.3933],
  [0.7698, 0.3931],
  [0.8028, 0.4299],
  [0.7794, 0.407],
  [0.7638, 0.4341],
  [0.757, 0.4277],
  [0.8282, 0.5435],
  [0.7071, 0.4568],
  [0.8635, 0.6256],
  [0.6476, 0.3804],
  [0.8928, 0.628],
  [0.5862, 0.2591],
  [0.891, 0.625],
  [0.5798, 0.2197],
  [0.8812, 0.6001],
  [0.5843, 0.2137],
  [0.8778, 0.5993],
  [0.5845, 0.2316],
  [0.7716, 0.794],
  [0.6808, 0.7777],
  [0.8258, 0.9292],
  [0.6882, 0.8927],
  [0.8949, 0.9619],
  [0.6923, 1.0132],
  [0.8985, 0.9755],
  [0.6937, 1.0234],
  [0.9293, 0.9729],
  [0.7008, 1.073],
];

/** The bones between those points (pairs of indexes): the arms, the legs, the body and the head. */
export const POSE_BONES = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16], [11, 23], [12, 24], [23, 24], [23, 25], [25, 27], [24, 26], [26, 28],
  [15, 17], [15, 19], [15, 21], [16, 18], [16, 20], [16, 22], [27, 29], [27, 31], [28, 30], [28, 32], [0, 11], [0, 12],
];

var NS = 'http://www.w3.org/2000/svg';
var KINDS = [
  { kind: 'image', label: 'Hình ảnh', hint: 'Dạy bằng ảnh, từ tệp hoặc webcam.', badge: 'Học sinh · 96%', art: '/kindart/image.jpg',
    help: 'Mỗi lớp là một hành động học sinh làm trước camera, tên viết không dấu (Gio tay phai). Train xong, bạn gán mỗi hành động với một đáp án, ví dụ Gio tay phai → A.' },
  { kind: 'pose', label: 'Tư thế', hint: 'Dạy bằng tư thế cơ thể, từ tệp hoặc webcam.', badge: 'Giơ tay · 95%', art: '/kindart/pose.jpg',
    help: 'Mỗi lớp là một hành động học sinh làm trước camera, tên viết không dấu (Gio tay phai). Train xong, bạn gán mỗi hành động với một đáp án, ví dụ Gio tay phai → A.' },
  { kind: 'audio', label: 'Âm thanh', hint: 'Dạy bằng âm thanh ngắn một giây, từ tệp hoặc micro.', badge: 'Vỗ tay · 92%', art: '/kindart/audio-spectrogram.png',
    help: 'Mỗi lớp là một âm thanh học sinh tạo ra (vỗ tay, huýt sáo), tên viết không dấu (Vo tay). Train xong, bạn gán mỗi âm thanh với một đáp án. Lớp Tiếng nền luôn có sẵn. Sau khi train xong, bạn thử bằng micro ở trang chi tiết của mô hình.' }
];
export var TM_TRAIN_URL = { image: 'https://teachablemachine.withgoogle.com/train/image', pose: 'https://teachablemachine.withgoogle.com/train/pose', audio: 'https://teachablemachine.withgoogle.com/train/audio' };

function skeleton() {
  var s = document.createElementNS(NS, 'svg');
  s.setAttribute('viewBox', '0 0 1 1'); s.setAttribute('preserveAspectRatio', 'xMidYMid slice'); s.setAttribute('aria-hidden', 'true');
  s.setAttribute('class', 'ail-kind-skel');
  POSE_BONES.forEach(function (b) {
    var l = document.createElementNS(NS, 'line');
    l.setAttribute('x1', POSE_POINTS[b[0]][0]); l.setAttribute('y1', POSE_POINTS[b[0]][1]);
    l.setAttribute('x2', POSE_POINTS[b[1]][0]); l.setAttribute('y2', POSE_POINTS[b[1]][1]);
    l.setAttribute('style', 'stroke:#34d399;fill:none;stroke-width:0.012;stroke-linecap:round');
    s.appendChild(l);
  });
  POSE_POINTS.forEach(function (p) {
    var c = document.createElementNS(NS, 'circle');
    c.setAttribute('cx', p[0]); c.setAttribute('cy', p[1]); c.setAttribute('r', 0.012); c.setAttribute('style', 'fill:#34d399;stroke:none');
    s.appendChild(c);
  });
  return s;
}

/** Thẻ ảnh minh hoạ của một loại (ảnh thật + khung xương cho tư thế + nhãn kết quả). */
export function kindArt(k) {
  return h('span', { class: 'ail-kind-art' }, h('img', { src: k.art, alt: '' }), k.kind === 'pose' ? skeleton() : null, h('span', { class: 'ail-kind-badge' }, k.badge));
}
export var KIND_LIST = KINDS;

/** Trang "Tạo mô hình": ba thẻ chọn loại, mỗi thẻ có "Xem giới thiệu" (video) ở chân thẻ, như KindChooser của learning.
 *  onPick(kind) mở trang train của loại đó; onIntro(kind) mở video giới thiệu. */
export function kindPicker(onPick, onIntro) {
  var titles = { image: 'Giới thiệu JULY Aura', pose: 'Xem giới thiệu Aura Flow', audio: 'Xem giới thiệu Aura Echo' };
  return h('div', { class: 'ail-kind-row ail-kind-pickrow', role: 'list' }, KINDS.map(function (k) {
    return h('div', { class: 'ail-kind-card ail-kind-pickcard', role: 'listitem' },
      h('button', { type: 'button', class: 'ail-kind-pick', 'aria-label': 'Tạo mô hình ' + k.label.toLowerCase(), onclick: function () { onPick(k.kind); } },
        kindArt(k),
        h('strong', { class: 'ail-kind-title' }, k.label, h('span', { 'aria-hidden': 'true' }, ' →')),
        h('span', { class: 'meta' }, k.hint)),
      h('div', { class: 'ail-kind-foot' },
        h('button', { type: 'button', class: 'ail-btn sm', onclick: function () { onIntro(k.kind); } }, ico('play'), titles[k.kind])));
  }));
}

/** Ba thẻ chọn loại mô hình + lời hướng dẫn của loại đang chọn. onPick(kind) được gọi khi bấm thẻ. */
export function kindChooser(current, onPick) {
  var guide = h('p', { class: 'ail-kind-guide meta' });
  var cards = KINDS.map(function (k) {
    var card = h('div', { class: 'ail-kind-card', role: 'listitem' },
      h('button', { type: 'button', class: 'ail-kind-pick', 'aria-label': 'Chọn loại ' + k.label, onclick: function () { pick(k.kind); } },
        kindArt(k),
        h('strong', null, k.label), h('span', { class: 'meta' }, k.hint)),
      h('a', { class: 'ail-btn sm', href: TM_TRAIN_URL[k.kind], target: '_blank', rel: 'noopener' }, 'Mở trang tạo ' + k.label.toLowerCase() + ' ↗'));
    card.dataset.kind = k.kind;
    return card;
  });
  var row = h('div', { class: 'ail-kind-row', role: 'list' }, cards);
  function pick(kind) {
    cards.forEach(function (c) { c.classList.toggle('is-on', c.dataset.kind === kind); });
    var k = KINDS.filter(function (x) { return x.kind === kind; })[0];
    guide.textContent = k ? k.help : '';
    onPick(kind);
  }
  pick(current || 'image');
  return h('div', { class: 'ail-kinds' }, h('strong', null, 'Bước 1 · Chọn loại mô hình và mở trang tạo'), row, guide);
}
