/* views-assistant.js — Single Chat Workspace cho AI Game Composer.
   Luồng hội thoại duy nhất: lời chào & gợi ý (Empty State) → tin nhắn căn giữa →
   Game Card inline (Chơi thử / Xem chi tiết mở rộng tại chỗ) → Contextual HITL Approval Card →
   Published / Rejected State ngay trong luồng hội thoại. Không còn khung Kế hoạch bên phải.

   Hợp đồng: chatView(ctx) với ctx = { me, llmMode, mount, navigate, openDrawer }.
   Bảo toàn 100% hợp đồng Backend:
   - POST /api/agent, GET /api/agent/drafts/:id/try, POST /api/agent/publish (draft_id + plan_hash + approved + reviewed_knowledge),
     POST /api/agent/review (reject).
   - GET /api/chats, GET /api/chats/:id, POST /api/chats/:id/proposals/:idx/(accept|reject).
   - POST /api/flow, /api/flow/build, /api/flow/fix, /api/flow/accept.
   - Mock Mode cô lập (runMockComposer + MOCK_PRESETS) không ghi DB. */

import { h, api, ico, btn, errBox, toast, modal, promptModal, QHELP, KIND,
  parseQuestionsClient, validateQuestionsClient, skeletonCards } from './dom.js';
import { runMockComposer, MOCK_PRESETS } from './mock-adapter.js';
import { previewFrame } from './list-page.js';

/* ---------- Gợi ý cho Empty State (3–4 prompt thực tế cho giáo viên) ---------- */
var EMPTY_SUGGESTIONS = [
  {
    icon: 'book',
    label: 'Tạo game ôn tập Toán lớp 3',
    prompt: 'Tạo game ôn tập Toán lớp 3 gồm 5 câu hỏi phép nhân chia, chơi bằng chuột hoặc cử chỉ tay.'
  },
  {
    icon: 'wand',
    label: 'Tạo trò chơi bằng cử chỉ bàn tay',
    prompt: 'Tạo trò chơi ôn tập bằng cử chỉ bàn tay gồm 5 câu hỏi trắc nghiệm Toán tiểu học.'
  },
  {
    icon: 'sparkles',
    label: 'Tạo quiz tiếng Anh',
    prompt: 'Tạo quiz tiếng Anh ôn tập từ vựng chủ đề Động vật gồm 5 câu hỏi.'
  },
  {
    icon: 'grid',
    label: 'Khám phá kho trò chơi',
    navigate: '#/players'
  }
];

var FLOW_SUGGESTIONS = [
  {
    icon: 'sparkles',
    label: 'Soạn trò chơi trắc nghiệm mới',
    prompt: 'Soạn cho mình một trò chơi trắc nghiệm ôn tập'
  },
  {
    icon: 'wand',
    label: '4 đáp án (A–D) · điều khiển bằng hình ảnh',
    prompt: 'Soạn game 4 đáp án A-D, điều khiển bằng hình ảnh (camera)'
  },
  {
    icon: 'book',
    label: 'Đúng / Sai · chỉ dùng chuột',
    prompt: 'Soạn game Đúng/Sai 2 đáp án, chỉ dùng chuột'
  },
  {
    icon: 'grid',
    label: 'Khám phá kho trò chơi',
    navigate: '#/players'
  }
];

var THINK_STEPS = [
  'Đang chuẩn bị trò chơi...',
  'Đang thiết kế cách chơi...',
  'Đang kiểm tra trò chơi...'
];
var MOCK_LATENCY = 360;

/* ---------- Phát hiện câu hỏi mẫu / placeholder để bảo toàn Data Integrity ---------- */
function isPlaceholderQuestion(q) {
  if (!q) return true;
  var txt = String(q.text || '').toLowerCase();
  if (/câu hỏi mẫu|cau hoi mau|placeholder|ví dụ mẫu|nhập câu hỏi/.test(txt)) return true;
  var ch = q.choices || [];
  if (ch.length >= 2) {
    var allGeneric = ch.every(function (c) {
      return /^(phương án|phuong an|đáp án|dap an|lựa chọn|lua chon)\s*[a-d1-4]?$/i.test(String(c.text || '').trim());
    });
    if (allGeneric) return true;
  }
  return false;
}

function analyzeExam(ap, examCache) {
  var exam = (ap && ap.exam) || null;
  if (!exam) return { hasExam: false, questions: [], realCount: 0, placeholderCount: 0, errors: [], needsContent: false, ready: true };
  var raw = exam.content;
  if (raw == null && exam.exam_id != null && examCache && examCache[String(exam.exam_id)]) {
    raw = examCache[String(exam.exam_id)].content;
  }
  if (raw == null || !String(raw).trim()) {
    return {
      hasExam: true,
      questions: [],
      realCount: 0,
      placeholderCount: 0,
      errors: [],
      needsContent: exam.mode === 'generate_new',
      ready: exam.mode === 'reuse_existing' && exam.exam_id != null
    };
  }
  var parsed = parseQuestionsClient(raw);
  var qs = parsed.questions || [];
  var errs = parsed.errors || [];
  var realCount = 0;
  var placeholderCount = 0;
  qs.forEach(function (q) {
    if (isPlaceholderQuestion(q)) placeholderCount++;
    else realCount++;
  });
  // Một số trò chơi dạng cặp thẻ (EN = VN) không dùng cú pháp trắc nghiệm '|'
  var isPairList = qs.length === 0 && errs.length > 0 && String(raw).split(/\r?\n/).filter(Boolean).every(function (line) {
    return line.indexOf('=') > 0 && line.indexOf('|') < 0;
  });
  if (isPairList) {
    var pairs = String(raw).split(/\r?\n/).map(function (s) { return s.trim(); }).filter(Boolean);
    return {
      hasExam: true,
      isPairList: true,
      pairs: pairs,
      questions: [],
      realCount: pairs.length,
      placeholderCount: 0,
      errors: [],
      needsContent: false,
      ready: pairs.length > 0
    };
  }
  return {
    hasExam: true,
    questions: qs,
    realCount: realCount,
    placeholderCount: placeholderCount,
    errors: errs,
    needsContent: false,
    ready: realCount > 0 && placeholderCount === 0 && errs.length === 0
  };
}

/* ---------- Nhãn tương tác thân thiện với giáo viên ---------- */
function interactionLabel(ap) {
  var md = ap && ap.model;
  var it = (ap && ap.interaction) || {};
  var kind = (md && md.kind) || it.primary || 'mouse';
  var map = {
    hands: 'Cử chỉ bàn tay',
    pose: 'Tư thế cơ thể (Camera)',
    audio: 'Giọng nói (Micro)',
    image: 'Nhận diện hình ảnh (Camera)',
    camera: 'Camera tương tác',
    mouse: 'Chơi bằng chuột'
  };
  var base = map[kind] || 'Chơi bằng chuột';
  if (kind !== 'mouse' && it.mouse_always_enabled !== false) {
    return base + ' · Có chuột dự phòng';
  }
  return base;
}

function interactionGuide(ap) {
  var md = ap && ap.model;
  var it = (ap && ap.interaction) || {};
  var kind = (md && md.kind) || it.primary || 'mouse';
  if (kind === 'hands') return 'Học sinh dùng cử chỉ bàn tay trước camera để chọn đáp án.';
  if (kind === 'pose') return 'Học sinh nghiêng người hoặc tạo tư thế trước camera để điều khiển.';
  if (kind === 'audio') return 'Học sinh nói đáp án qua micro để trả lời câu hỏi.';
  if (kind === 'image' || kind === 'camera') return 'Học sinh đưa thẻ hoặc hình ảnh trước camera để chọn đáp án.';
  return 'Học sinh nhấn hoặc kéo thả trực tiếp bằng chuột (hoặc màn hình cảm ứng).';
}

/* ---------- Tạo phản hồi AI ngắn gọn (1–3 câu), không thêm LLM call, không lộ jargon ---------- */
function stripTechJargon(text) {
  if (!text) return '';
  return String(text)
    .replace(/\[?(REUSE|GENERATE|ASK_CLARIFY|REFUSE|DRAFT|HITL\s*\d?|pending_approval)\]?\s*[:\-–—]?\s*/gi, '')
    .replace(/Spec-driven\s*Model-aware/gi, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

function conciseAssistantText(plan, examInfo) {
  if (!plan) return '';
  var dec = plan.decision;
  var ap = plan.application_plan;

  if (dec === 'REFUSE' || dec === 'ASK_CLARIFY' || dec === 'ERROR' || !ap) {
    return stripTechJargon(plan.message || '') || 'Tôi chưa thể xử lý yêu cầu này. Bạn thử mô tả rõ hơn nhé.';
  }

  var name = ap.name || (ap.player && ap.player.player_name) || 'trò chơi ôn tập';
  var isGenerate = ap.player && ap.player.mode === 'generate_new';
  var countPhrase = '';
  if (examInfo && examInfo.hasExam) {
    if (examInfo.placeholderCount > 0) {
      countPhrase = ' (lưu ý: bộ câu hỏi đang có câu hỏi mẫu, chưa đủ nội dung hoàn chỉnh)';
    } else if (examInfo.realCount > 0) {
      countPhrase = examInfo.isPairList
        ? ' với ' + examInfo.realCount + ' cặp thẻ'
        : ' gồm ' + examInfo.realCount + ' câu hỏi';
    }
  }

  var sentence1 = isGenerate
    ? 'Tôi đã tạo trò chơi "' + name + '"' + countPhrase + '.'
    : 'Tôi đã chuẩn bị trò chơi "' + name + '"' + countPhrase + ' từ kho trò chơi.';

  var md = ap.model;
  var kind = (md && md.kind) || (ap.interaction && ap.interaction.primary) || 'mouse';
  var sentence2 = '';
  if (kind === 'hands') sentence2 = ' Học sinh dùng cử chỉ bàn tay để chọn đáp án, và luôn có thể chơi bằng chuột.';
  else if (kind === 'pose') sentence2 = ' Học sinh điều khiển bằng tư thế trước camera, có hỗ trợ chuột dự phòng.';
  else if (kind === 'audio') sentence2 = ' Học sinh trả lời bằng giọng nói qua micro, có hỗ trợ chuột dự phòng.';
  else if (kind === 'image' || kind === 'camera') sentence2 = ' Học sinh tương tác qua camera và luôn có thể chơi bằng chuột.';
  else sentence2 = ' Học sinh có thể chơi trực tiếp bằng chuột.';

  return sentence1 + sentence2;
}

function answerLabel(q) {
  if (q.type === 'truefalse') return q.answer === 'T' ? 'Đúng' : 'Sai';
  var c = (q.choices || []).filter(function (x) { return x.key === q.answer; })[0];
  return q.answer + (c && c.text ? ' — ' + c.text : '');
}

function extractSubjectHint(ap) {
  var src = ((ap && ap.name) || '') + ' ' + ((ap && ap.exam && ap.exam.exam_name) || '');
  var m = src.match(/(Toán|Tiếng Anh|Vật lý|Hóa học|Sinh học|Lịch sử|Địa lý|Ngữ văn|Tin học|Khoa học|Âm nhạc)(?:\s+lớp\s*\d+)?/i);
  return m ? m[0] : '';
}

/* ---------- Kiểm tra điều kiện hiển thị Contextual HITL Approval Card ---------- */
function shouldShowApproval(plan, isMock) {
  if (!plan || !plan.application_plan) return false;
  if (plan.decision !== 'REUSE' && plan.decision !== 'GENERATE') return false;
  if (plan.status !== 'pending_approval') return false;
  if (plan._decided) return false;
  if (!isMock && (!plan.draft_id || !plan.plan_hash)) return false;
  return true;
}

export function chatView(ctx) {
  ctx = ctx || {};
  var mountFn = typeof ctx.mount === 'function' ? ctx.mount : function (el) {
    var m = document.getElementById('main'); if (m) m.replaceChildren(el);
  };
  var navigateFn = typeof ctx.navigate === 'function' ? ctx.navigate : function (p) { location.hash = p; };
  var llmMode = ctx.llmMode == null ? '' : String(ctx.llmMode);
  var userKey = 'ail.chat.session.' + ((ctx.me && ctx.me.id) || 'anon');

  /* ---------- trạng thái tách biệt theo chế độ ---------- */
  var mode = 'flow'; // 'flow' | 'real' | 'mock'
  var real = { chatId: null, conversationId: null, msgs: [], busy: false, chats: [], sideErr: null, openErr: null, brief: null, flowPlan: null, thinkSteps: null };
  var mock = { msgs: [], busy: false, catalog: null };
  var catalogCache = { playersById: {}, examsById: {}, loaded: false };

  function modeStorageKey(m) { return userKey + '.' + (m || mode); }
  function defaultPlaceholder(m) {
    return (m || mode) === 'flow'
      ? 'Mô tả trò chơi muốn soạn (số đáp án: 2/3/4 · điều khiển: chuột, hình ảnh, tư thế, âm thanh)...'
      : 'Nhập môn học, chủ đề, số câu hỏi hoặc cách chơi bạn muốn...';
  }

  /* Khôi phục phiên hội thoại hiện tại khi reload (tách riêng theo chế độ) */
  function restoreSession(m) {
    real.chatId = null;
    real.conversationId = null;
    real.msgs = [];
    real.openErr = null;
    real.brief = null;
    real.flowPlan = null;
    if (m === 'mock') return;
    try {
      var saved = sessionStorage.getItem(modeStorageKey(m));
      if (saved) {
        var parsed = JSON.parse(saved);
        if (parsed && Array.isArray(parsed.msgs) && parsed.msgs.length) {
          real.msgs = parsed.msgs;
          real.chatId = parsed.chatId || null;
          real.conversationId = parsed.conversationId || null;
          real.brief = parsed.brief || null;
          real.flowPlan = parsed.flowPlan || null;
        }
      }
    } catch (e) {}
  }
  restoreSession(mode);

  function persistSession() {
    try {
      if (mode === 'mock') return;
      var k = modeStorageKey(mode);
      if (!real.msgs.length) { sessionStorage.removeItem(k); return; }
      // Không lưu HTML lớn trong sessionStorage
      var slim = real.msgs.slice(-30).map(function (m) {
        var copy = Object.assign({}, m);
        if (copy.plan && copy.plan.application_plan && copy.plan.application_plan.player && copy.plan.application_plan.player.html) {
          copy.plan = Object.assign({}, copy.plan, {
            application_plan: Object.assign({}, copy.plan.application_plan, {
              player: Object.assign({}, copy.plan.application_plan.player, { html: null })
            })
          });
        }
        return copy;
      });
      sessionStorage.setItem(k, JSON.stringify({
        chatId: real.chatId,
        conversationId: mode === 'real' ? real.conversationId : null,
        msgs: slim,
        brief: mode === 'flow' ? real.brief : null,
        flowPlan: mode === 'flow' ? real.flowPlan : null
      }));
    } catch (e) {}
  }

  /* Đọc nhẹ catalog để hiển thị thumbnail thật cho Game Card & nội dung bộ đề có sẵn */
  function loadCatalogMeta() {
    if (catalogCache.loaded) return Promise.resolve(catalogCache);
    catalogCache.loaded = true;
    return Promise.all([
      api('GET', '/api/players?scope=usable').catch(function () { return { players: [] }; }),
      api('GET', '/api/exams').catch(function () { return { exams: [] }; })
    ]).then(function (res) {
      var pls = (res[0] && res[0].players) || [];
      var exs = (res[1] && res[1].exams) || [];
      pls.forEach(function (p) { catalogCache.playersById[String(p.id)] = p; });
      exs.forEach(function (e) { catalogCache.examsById[String(e.id)] = e; });
      if (real.msgs.length || mock.msgs.length) drawLog(false);
      return catalogCache;
    }).catch(function () { return catalogCache; });
  }
  loadCatalogMeta();

  /* ---------- phần tử gốc (Single Column — KHÔNG có Plan Panel bên phải) ---------- */
  var historyOpen = false;
  var head = h('header', { class: 'ail-chat-head' });
  var bannerSlot = h('div', { class: 'ail-chat-banner-slot' });
  var log = h('div', { class: 'ail-chat-log', role: 'log', 'aria-live': 'polite', 'aria-label': 'Nội dung trò chuyện' });
  var side = h('aside', { class: 'ail-chat-history is-hidden', 'aria-label': 'Lịch sử trò chuyện' });

  var input = h('textarea', {
    rows: 1,
    maxlength: 2000,
    'aria-label': 'Mô tả trò chơi ôn tập bạn muốn tạo',
    placeholder: defaultPlaceholder(mode)
  });
  function autoResize() {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 160) + 'px';
  }
  input.addEventListener('input', autoResize);

  var send = h('button', {
    class: 'ail-send-btn',
    type: 'button',
    'aria-label': 'Gửi',
    title: 'Gửi (Enter)'
  }, ico('send'));

  var composeBox = h('div', { class: 'ail-chat-compose' }, input, send);
  var emptyPromptsSlot = h('div', { class: 'ail-empty-prompts-slot' });
  var composeWrap = h('div', { class: 'ail-chat-compose-wrap' }, composeBox, emptyPromptsSlot);
  var main = h('div', { class: 'ail-chat-main' }, head, bannerSlot, log, composeWrap);

  /* ---------- tiện ích ---------- */
  function focusInput() { try { input.focus({ preventScroll: true }); } catch (e) { input.focus(); } }
  function wait(ms) { return new Promise(function (ok) { setTimeout(ok, ms); }); }
  function flexModalBody(children) {
    return h('div', { class: 'ail-try-wrap' }, children);
  }

  /* ================= 1 · Header tối giản ================= */
  var histAnchor = h('div', { class: 'ail-hist-anchor' });
  function closeHistory() {
    if (!historyOpen) return;
    historyOpen = false;
    side.classList.add('is-hidden');
    drawHead();
  }
  function toggleHistory(e) {
    if (e) e.stopPropagation();
    historyOpen = !historyOpen;
    side.classList.toggle('is-hidden', !historyOpen);
    drawHead();
  }
  document.addEventListener('click', function onAway(e) {
    if (!main.isConnected) return document.removeEventListener('click', onAway);
    if (historyOpen && !histAnchor.contains(e.target)) closeHistory();
  });
  document.addEventListener('keydown', function onEsc(e) {
    if (!main.isConnected) return document.removeEventListener('keydown', onEsc);
    if (historyOpen && e.key === 'Escape') closeHistory();
  });

  function drawHead() {
    var mob = typeof ctx.openDrawer === 'function'
      ? h('button', { type: 'button', class: 'ail-mobile-btn', 'aria-label': 'Mở menu điều hướng', onclick: ctx.openDrawer }, ico('menu'))
      : null;

    histAnchor.replaceChildren(
      btn('Lịch sử', 'chat', {
        cls: 'sm' + (historyOpen ? ' pri' : ' ghost'),
        title: 'Mở lịch sử trò chuyện',
        onclick: toggleHistory
      }),
      side
    );

    var llmOk = llmMode && llmMode.toLowerCase().indexOf('giả') < 0;
    var modeSelect = h('select', {
      class: 'ail-mode-select',
      'aria-label': 'Chế độ AI',
      title: 'Chọn chế độ làm việc của AI',
      onchange: function () {
        var next = modeSelect.value;
        if (next === mode) return;
        mode = next;
        restoreSession(mode);
        input.placeholder = defaultPlaceholder(mode);
        closeHistory();
        drawAll();
        focusInput();
      }
    },
      h('option', { value: 'flow', selected: mode === 'flow' ? true : null }, 'Soạn trò chơi'),
      h('option', { value: 'real', selected: mode === 'real' ? true : null }, llmOk ? 'AI Composer (nâng cao)' : 'AI Composer (giả lập)'),
      h('option', { value: 'mock', selected: mode === 'mock' ? true : null }, 'Xem thử (Mock)')
    );

    var modeControl = h('div', { class: 'ail-mode-pill' },
      h('span', { class: 'ail-mode-dot ' + (mode === 'mock' ? 'is-mock' : llmOk ? 'is-ok' : 'is-mock'), 'aria-hidden': 'true' }),
      modeSelect
    );

    head.replaceChildren(
      h('div', { class: 'ail-chat-head-l' },
        mob,
        h('span', { class: 'ail-chat-title' }, 'AI Game Composer')
      ),
      h('div', { class: 'ail-chat-head-r' },
        histAnchor,
        btn('Cuộc mới', 'plus', {
          cls: 'sm ghost',
          title: 'Bắt đầu cuộc hội thoại mới',
          onclick: function () { closeHistory(); newChat(); }
        }),
        modeControl
      )
    );
  }

  function drawBanner() {
    bannerSlot.replaceChildren();
    if (mode !== 'mock') return;
    bannerSlot.appendChild(
      h('div', { class: 'ail-banner-mock ail-chat-mock-bar', role: 'status' },
        h('span', { style: 'display:inline-flex;align-items:center;gap:6px' },
          ico('info'),
          h('b', null, 'Chế độ xem thử (Mock)'),
          '— không gọi AI trả phí và không ghi dữ liệu thật'
        ),
        h('div', { class: 'row', style: 'gap:6px' }, MOCK_PRESETS.map(function (pr) {
          return btn(pr.title, pr.icon, {
            cls: 'sm',
            title: pr.desc,
            onclick: function () { input.value = pr.prompt; submit(); }
          });
        }))
      )
    );
  }

  /* ================= 2 · Lịch sử trò chuyện ================= */
  function newChat() {
    if (mode === 'mock') {
      mock.msgs = [];
    } else {
      real.chatId = null;
      real.conversationId = null;
      real.msgs = [];
      real.openErr = null;
      real.brief = null;
      real.flowPlan = null;
      try { sessionStorage.removeItem(modeStorageKey(mode)); } catch (e) {}
    }
    input.placeholder = defaultPlaceholder(mode);
    drawLog(true);
    focusInput();
  }

  function drawSideMock() {
    side.replaceChildren(
      h('div', { class: 'ail-chat-hist-head' },
        h('b', null, 'Chế độ xem thử'),
        h('button', { type: 'button', class: 'ail-btn ghost icon sm', 'aria-label': 'Đóng lịch sử', onclick: toggleHistory }, ico('x'))
      ),
      h('p', { class: 'meta', style: 'padding:4px 6px' }, 'Phiên Mock hoạt động độc lập, không ghi vào lịch sử thật.'),
      btn('Phiên mới', 'plus', { cls: 'sm', onclick: function () { closeHistory(); newChat(); } })
    );
  }

  function drawSideList() {
    var kids = [
      h('div', { class: 'ail-chat-hist-head' },
        h('b', null, 'Lịch sử trò chuyện'),
        h('button', { type: 'button', class: 'ail-btn ghost icon sm', 'aria-label': 'Đóng lịch sử', onclick: toggleHistory }, ico('x'))
      ),
      btn('Cuộc trò chuyện mới', 'plus', { cls: 'sm', onclick: function () { closeHistory(); newChat(); } })
    ];
    if (!real.chats.length) {
      kids.push(h('p', { class: 'meta', style: 'padding:8px 6px' }, 'Chưa có cuộc trò chuyện nào.'));
    }
    real.chats.forEach(function (c) {
      var cur = String(c.id) === String(real.chatId);
      kids.push(h('button', {
        type: 'button',
        class: 'ail-chat-hist-item' + (cur ? ' on' : ''),
        'aria-current': cur ? 'true' : null,
        title: c.title || ('Chat #' + c.id),
        onclick: function () { openChat(c.id); }
      }, ico('chat'), h('span', null, c.title || ('Chat #' + c.id))));
    });
    side.replaceChildren.apply(side, kids);
  }

  function drawSide() {
    if (mode === 'mock') { drawSideMock(); return; }
    side.replaceChildren(
      h('div', { class: 'ail-chat-hist-head' }, h('b', null, 'Lịch sử trò chuyện')),
      skeletonCards(2)
    );
    api('GET', '/api/chats').then(function (d) {
      real.chats = (d && d.chats) || [];
      real.sideErr = null;
      drawSideList();
    }).catch(function (e) {
      real.sideErr = e;
      side.replaceChildren(
        h('div', { class: 'ail-chat-hist-head' }, h('b', null, 'Lịch sử trò chuyện')),
        errBox(e),
        btn('Thử lại', 'refresh', { cls: 'sm', onclick: drawSide })
      );
    });
  }

  function syncPlayerStatuses(msgs) {
    var hasAccepted = (msgs || []).some(function (m) { return m.proposal && m.proposal.status === 'accepted' && m.proposal.playerId; });
    if (!hasAccepted) return;
    var scope = ctx.me && ctx.me.role === 'admin' ? 'all' : 'mine';
    api('GET', '/api/players?scope=' + scope).then(function (d) {
      var byId = {};
      ((d && d.players) || []).forEach(function (pl) { byId[String(pl.id)] = pl.status; });
      var changed = false;
      (msgs || []).forEach(function (m) {
        if (m.proposal && m.proposal.playerId && byId[String(m.proposal.playerId)]) {
          m.proposal._playerStatus = byId[String(m.proposal.playerId)];
          changed = true;
        }
      });
      if (changed) drawLog(false);
    }).catch(function () {});
  }

  function openChat(id) {
    closeHistory();
    api('GET', '/api/chats/' + id).then(function (x) {
      real.chatId = x.id;
      real.msgs = (x && x.messages) || [];
      real.openErr = null;
      persistSession();
      drawLog(true);
      drawSideList();
      syncPlayerStatuses(real.msgs);
    }).catch(function (e) {
      real.openErr = { id: id, e: e };
      toast('Không mở được cuộc trò chuyện: ' + e.message, 'err');
      drawLog(false);
    });
  }

  function resyncChat() {
    var targetId = real.chatId;
    if (!targetId) return;
    api('GET', '/api/chats/' + targetId).then(function (x) {
      if (real.chatId !== targetId) return;
      real.chatId = x.id;
      real.msgs = (x && x.messages) || [];
      toast('Đã cập nhật trạng thái mới nhất.', 'info');
      drawLog(false);
      syncPlayerStatuses(real.msgs);
    }).catch(function (e) { toast('Không đồng bộ được trạng thái: ' + e.message, 'err'); });
  }

  /* ================= 3 · Empty State & Loading State ================= */
  function emptyState() {
    return h('div', { class: 'ail-chat-welcome' },
      h('span', { class: 'ail-welcome-mark', 'aria-hidden': 'true' }, ico('sparkles')),
      h('h1', { class: 'ail-welcome-title' }, 'Bạn muốn tạo trò chơi ôn tập gì hôm nay?')
    );
  }

  function renderEmptySuggestions(isEmpty) {
    emptyPromptsSlot.replaceChildren();
    if (!isEmpty) return;
    var items = mode === 'flow' ? FLOW_SUGGESTIONS : EMPTY_SUGGESTIONS;
    emptyPromptsSlot.appendChild(
      h('div', { class: 'ail-suggest-row', role: 'group', 'aria-label': 'Gợi ý nhanh' },
        items.map(function (s) {
          return h('button', {
            type: 'button',
            class: 'ail-suggest-pill',
            onclick: function () {
              if (s.navigate) { navigateFn(s.navigate); return; }
              input.value = s.prompt;
              autoResize();
              submit();
            }
          }, ico(s.icon), h('span', null, s.label));
        })
      )
    );
  }

  var thinkTimer = null;
  function stopThink() { if (thinkTimer) { clearInterval(thinkTimer); thinkTimer = null; } }

  function thinkingEl() {
    var step = 0;
    var steps = (mode !== 'mock' && real.thinkSteps) || THINK_STEPS;
    var lbl = h('span', null, steps[0]);
    stopThink();
    thinkTimer = setInterval(function () {
      if (!lbl.isConnected) return stopThink();
      step = (step + 1) % steps.length;
      lbl.textContent = steps[step];
    }, 2200);
    return h('div', { class: 'ail-msg ail-msg-bot is-loading', 'aria-live': 'polite' },
      h('span', { class: 'ail-bot-avatar', 'aria-hidden': 'true' }, ico('sparkles')),
      h('div', { class: 'ail-msg-body' },
        h('div', { class: 'ail-thinking' },
          h('span', { class: 'dots', 'aria-hidden': 'true' }, h('span'), h('span'), h('span')),
          lbl
        )
      )
    );
  }

  /* ================= 4 · Preview Modal (chỉ mở khi người dùng nhấn Chơi thử) ================= */
  function openPreview(ap, plan) {
    var p = (ap && ap.player) || {};
    var title = 'Chơi thử: ' + (ap.name || p.player_name || 'Trò chơi');
    if (plan && plan.preview_url) {
      var wp = previewFrame(plan.preview_url);
      modal(title, flexModalBody([
        h('span', { class: 'meta' }, 'Chạy thử an toàn trong khung cách ly. Chuột luôn hoạt động.'),
        wp
      ]), { cls: 'ail-try' });
    } else if (p.mode === 'generate_new' && p.html) {
      modal(title, flexModalBody([
        h('span', { class: 'meta' }, 'Chạy thử bản nháp trong khung cách ly.'),
        h('iframe', { sandbox: 'allow-scripts', allow: 'camera; microphone', title: title, srcdoc: p.html })
      ]), { cls: 'ail-try' });
    } else if (p.player_id != null) {
      var w = previewFrame(p.player_id);
      modal(title, flexModalBody([
        h('span', { class: 'meta' }, 'Chạy thử trình chơi trong khung cách ly.'),
        w
      ]), { cls: 'ail-try' });
    } else {
      toast('Chưa có dữ liệu trò chơi để chơi thử.', 'err');
    }
  }

  /* ================= 5 · Inline Expandable Plan (bên trong Game Card) ================= */
  function mockQuestionEditor(plan) {
    var exam = plan.application_plan.exam;
    var box = h('div', { style: 'margin-top:8px' });
    var open = false;
    function draw() {
      if (!open) {
        box.replaceChildren(btn('Chỉnh sửa bộ câu hỏi (Mock)', 'edit', { cls: 'sm', onclick: function () { open = true; draw(); } }));
        return;
      }
      var ta = h('textarea', { class: 'code', spellcheck: 'false', style: 'min-height:120px;width:100%', 'aria-label': 'Nội dung bộ câu hỏi' });
      ta.value = exam.content || '';
      var res = h('div', { class: 'ail-val-list', 'aria-live': 'polite', style: 'margin-top:6px' });
      function validate() {
        var r = validateQuestionsClient(ta.value);
        res.replaceChildren(r.valid
          ? h('div', { class: 'ok' }, 'Hợp lệ: ' + r.questions.length + ' câu hỏi.')
          : r.errors.map(function (er) { return h('div', { class: 'bad' }, 'Dòng ' + er.line + ': ' + er.error); }));
        return r;
      }
      ta.addEventListener('input', validate);
      var apply = btn('Áp dụng', 'check', { cls: 'sm pri', onclick: function () {
        var r = validateQuestionsClient(ta.value);
        if (!r.valid) { validate(); toast('Bộ câu hỏi còn dòng chưa hợp lệ.', 'err'); return; }
        exam.content = ta.value;
        exam.knowledge_review_required = true;
        toast('Đã cập nhật bộ câu hỏi trong phiên Mock.', 'ok');
        drawLog(false);
      } });
      box.replaceChildren(
        h('small', { class: 'meta', style: 'display:block;margin-bottom:6px' }, QHELP),
        ta,
        res,
        h('div', { class: 'row', style: 'margin-top:8px' }, apply, btn('Đóng', 'x', { cls: 'sm', onclick: function () { open = false; draw(); } }))
      );
      validate();
    }
    draw();
    return box;
  }

  function renderQuestionsSection(ap, plan, examInfo, isMock) {
    var items = [];
    if (examInfo.placeholderCount > 0) {
      items.push(h('div', { class: 'ail-inline-warn', role: 'alert' },
        ico('alert'),
        h('span', null, 'Phát hiện ' + examInfo.placeholderCount + ' câu hỏi mẫu chưa hoàn chỉnh. Cần kiểm tra lại dữ liệu trước khi duyệt.')
      ));
    }
    if (examInfo.isPairList && examInfo.pairs.length) {
      items.push(h('ol', { class: 'ail-q-clean-list' },
        examInfo.pairs.map(function (pair) {
          return h('li', null, h('span', null, pair));
        })
      ));
    } else if (examInfo.questions.length) {
      items.push(h('ol', { class: 'ail-q-clean-list' },
        examInfo.questions.map(function (q) {
          var isPh = isPlaceholderQuestion(q);
          var choicesText = q.type === 'truefalse'
            ? 'Đúng / Sai'
            : (q.choices || []).map(function (c) { return c.key + '. ' + c.text; }).join('  ·  ');
          return h('li', { class: isPh ? 'is-placeholder' : '' },
            h('div', { class: 'ail-q-stem' },
              q.text,
              isPh ? h('span', { class: 'ail-chip warn', style: 'margin-left:6px' }, 'Câu mẫu') : null
            ),
            h('div', { class: 'ail-q-choices' }, choicesText),
            h('div', { class: 'ail-q-ans' }, 'Đáp án: ', h('b', null, answerLabel(q)))
          );
        })
      ));
    } else if (examInfo.errors.length) {
      items.push(h('div', { class: 'ail-val-list' },
        examInfo.errors.map(function (er) { return h('div', { class: 'bad' }, 'Dòng ' + er.line + ': ' + er.error); })
      ));
    } else if (ap.exam && ap.exam.exam_name) {
      items.push(h('p', { class: 'meta' }, 'Sử dụng bộ câu hỏi có sẵn: ' + ap.exam.exam_name + '.'));
    } else {
      items.push(h('p', { class: 'meta' }, 'Trò chơi này không kèm bộ câu hỏi riêng.'));
    }

    if (isMock && ap.exam && ap.exam.mode === 'generate_new') {
      items.push(mockQuestionEditor(plan));
    }
    return items;
  }

  function renderExpandablePlan(plan, ap, examInfo, isMock, focusSection) {
    var p = ap.player || {};
    var md = ap.model || null;
    var subject = extractSubjectHint(ap);
    var isGenerate = p.mode === 'generate_new';

    var secGoal = h('details', { class: 'ail-plan-fold', open: true },
      h('summary', null, 'Mục tiêu học tập'),
      h('div', { class: 'ail-plan-fold-b' },
        h('div', { class: 'ail-kv' },
          h('span', { class: 'k' }, 'Tên trò chơi'), h('span', { class: 'v' }, ap.name || '—'),
          subject ? [h('span', { class: 'k' }, 'Môn / Chủ đề'), h('span', { class: 'v' }, subject)] : null,
          ap.description ? [h('span', { class: 'k' }, 'Mục tiêu'), h('span', { class: 'v' }, ap.description)] : null
        )
      )
    );

    var secGame = h('details', { class: 'ail-plan-fold' },
      h('summary', null, 'Trò chơi'),
      h('div', { class: 'ail-plan-fold-b' },
        h('div', { class: 'ail-kv' },
          h('span', { class: 'k' }, 'Trình chơi'), h('span', { class: 'v' }, p.player_name || ap.name || 'Trò chơi tương tác'),
          h('span', { class: 'k' }, 'Nguồn gốc'), h('span', { class: 'v' }, isGenerate ? 'Tạo mới riêng cho phiên này (chưa công khai)' : 'Tái sử dụng từ kho trò chơi có sẵn'),
          h('span', { class: 'k' }, 'Cách chơi'), h('span', { class: 'v' }, ap.description || 'Học sinh trả lời từng câu hỏi để ghi điểm và hoàn thành lượt chơi.')
        )
      )
    );

    var secInteract = h('details', { class: 'ail-plan-fold' },
      h('summary', null, 'Cách tương tác'),
      h('div', { class: 'ail-plan-fold-b' },
        h('div', { class: 'ail-kv' },
          md ? [h('span', { class: 'k' }, 'Mô hình AI'), h('span', { class: 'v' }, md.model_name || KIND[md.kind] || md.kind)] : null,
          h('span', { class: 'k' }, 'Thao tác'), h('span', { class: 'v' }, interactionGuide(ap)),
          h('span', { class: 'k' }, 'Dự phòng'), h('span', { class: 'v' },
            (ap.interaction && ap.interaction.mouse_always_enabled !== false)
              ? 'Luôn hỗ trợ chơi đầy đủ bằng chuột khi không dùng camera/micro.'
              : 'Kiểm tra hỗ trợ chuột trước khi dùng trên lớp.'
          )
        )
      )
    );

    var qCountLabel = examInfo.placeholderCount > 0
      ? 'Bộ câu hỏi (cần kiểm tra)'
      : examInfo.realCount > 0
        ? 'Bộ câu hỏi (' + examInfo.realCount + (examInfo.isPairList ? ' cặp' : ' câu') + ')'
        : 'Bộ câu hỏi';

    var secQuestions = h('details', { class: 'ail-plan-fold', open: focusSection === 'questions' || examInfo.placeholderCount > 0 ? true : null },
      h('summary', null, qCountLabel),
      h('div', { class: 'ail-plan-fold-b' }, renderQuestionsSection(ap, plan, examInfo, isMock))
    );

    return h('div', { class: 'ail-inline-plan' }, secGoal, secGame, secInteract, secQuestions);
  }

  /* ================= 6 · Inline Game Card ================= */
  function renderGameCard(m, plan, isMock) {
    var ap = plan.application_plan;
    var p = ap.player || {};
    var examInfo = analyzeExam(ap, catalogCache.examsById);
    var cachedPlayer = p.player_id != null ? catalogCache.playersById[String(p.player_id)] : null;
    var thumbUrl = p.image || (cachedPlayer && cachedPlayer.image) || '';
    var subject = extractSubjectHint(ap);
    var flags = plan.safety_flags || [];

    var thumbEl = h('div', { class: 'ail-gc-thumb' + (thumbUrl ? ' has-img' : '') },
      thumbUrl
        ? h('img', { src: thumbUrl, alt: ap.name || 'Ảnh trò chơi', loading: 'lazy' })
        : ico(ap.model ? 'camera' : 'play')
    );

    var pills = [];
    if (subject) pills.push(h('span', { class: 'ail-gc-pill' }, subject));
    if (examInfo.hasExam) {
      if (examInfo.placeholderCount > 0) {
        pills.push(h('span', { class: 'ail-gc-pill is-warn' }, 'Có câu hỏi mẫu'));
      } else if (examInfo.realCount > 0) {
        pills.push(h('span', { class: 'ail-gc-pill' }, examInfo.realCount + (examInfo.isPairList ? ' cặp thẻ' : ' câu hỏi')));
      }
    }
    pills.push(h('span', { class: 'ail-gc-pill' }, interactionLabel(ap)));

    var expanded = !!m._detailsOpen;
    var detailBtn = btn(expanded ? 'Thu gọn chi tiết' : 'Xem chi tiết', 'eye', {
      cls: 'sm',
      onclick: function () {
        m._detailsOpen = !m._detailsOpen;
        m._focusSection = null;
        drawLog(false);
      }
    });

    var playBtn = btn('Chơi thử', 'play', {
      cls: 'sm pri',
      onclick: function () { openPreview(ap, plan); }
    });

    var card = h('div', { class: 'ail-game-card' },
      h('div', { class: 'ail-gc-top' },
        thumbEl,
        h('div', { class: 'ail-gc-info' },
          h('div', { class: 'ail-gc-title' }, ap.name || p.player_name || 'Trò chơi ôn tập'),
          ap.description ? h('p', { class: 'ail-gc-desc' }, ap.description) : null,
          h('div', { class: 'ail-gc-pills' }, pills)
        )
      ),
      flags.length ? h('div', { class: 'ail-inline-warn', role: 'alert', style: 'margin:0 16px 12px' },
        ico('alert'),
        h('span', null, 'Cảnh báo an toàn: ' + flags.map(function (f) { return f.label || f.reason || f.code; }).join('; '))
      ) : null,
      h('div', { class: 'ail-gc-actions' }, playBtn, detailBtn)
    );

    if (expanded) {
      card.appendChild(renderExpandablePlan(plan, ap, examInfo, isMock, m._focusSection));
    }

    return card;
  }

  /* ================= 7 · Contextual HITL Approval Card & Published/Rejected State ================= */
  function renderContextualHitl(m, plan, isMock) {
    var ap = plan.application_plan;
    if (!ap) return null;

    /* Published State (Section 10) */
    if (plan._decided === 'published') {
      var isGen = ap.player && ap.player.mode === 'generate_new';
      return h('div', { class: 'ail-status-card is-published', role: 'status' },
        h('div', { class: 'ail-status-head' },
          h('span', { class: 'ail-status-ico' }, ico('checkCircle')),
          h('div', { class: 'ail-status-txt' },
            h('b', null, 'Trò chơi đã được lưu.'),
            isGen ? h('span', { class: 'meta' }, 'Đã lưu riêng tư trong tài khoản của bạn (không tự đưa vào kho công khai).') : null
          )
        ),
        h('div', { class: 'ail-status-actions' },
          plan._playUrl ? btn('Chơi ngay', 'play', { cls: 'sm pri', href: plan._playUrl, target: '_blank' }) : null,
          btn('Xem ứng dụng', 'grid', { cls: 'sm', onclick: function () { navigateFn('#/apps'); } })
        )
      );
    }

    /* Mock Published State */
    if (plan._decided === 'accepted_mock') {
      return h('div', { class: 'ail-status-card is-published', role: 'status' },
        h('div', { class: 'ail-status-head' },
          h('span', { class: 'ail-status-ico' }, ico('checkCircle')),
          h('div', { class: 'ail-status-txt' },
            h('b', null, 'Trò chơi đã được lưu (bản xem thử Mock).'),
            h('span', { class: 'meta' }, 'Chuyển sang AI Composer để lưu thật vào tài khoản và mở chơi ngay.')
          )
        ),
        h('div', { class: 'ail-status-actions' },
          btn('Chơi thử', 'play', { cls: 'sm pri', onclick: function () { openPreview(ap, plan); } }),
          btn('Xem ứng dụng', 'grid', { cls: 'sm', onclick: function () { navigateFn('#/apps'); } })
        )
      );
    }

    /* Rejected State (Section 10) */
    if (plan._decided === 'rejected' || plan._decided === 'rejected_mock') {
      return h('div', { class: 'ail-status-card is-rejected', role: 'status' },
        h('div', { class: 'ail-status-head' },
          h('span', { class: 'ail-status-ico' }, ico('xCircle')),
          h('div', { class: 'ail-status-txt' },
            h('b', null, 'Đã từ chối bản nháp này.'),
            h('span', { class: 'meta' }, (plan._rejectReason ? 'Lý do: ' + plan._rejectReason + '. ' : '') + 'Bạn có thể gửi yêu cầu mới bên dưới.')
          )
        )
      );
    }

    /* Không hiển thị Approval Card nếu không đúng điều kiện backend */
    if (!shouldShowApproval(plan, isMock)) return null;

    var examInfo = analyzeExam(ap, catalogCache.examsById);
    var notReadyReason = null;
    if (examInfo.placeholderCount > 0) {
      notReadyReason = 'Bộ câu hỏi vẫn còn câu hỏi mẫu, chưa đủ nội dung hoàn chỉnh để duyệt.';
    } else if (examInfo.errors.length > 0) {
      notReadyReason = 'Bộ câu hỏi còn lỗi định dạng, chưa sẵn sàng phê duyệt.';
    } else if (examInfo.needsContent) {
      notReadyReason = 'Bộ câu hỏi đang trống, chưa sẵn sàng phê duyệt.';
    }

    var submitting = !!plan._submitting;
    var errSlot = h('div', { class: 'ail-approval-err' });
    if (plan._submitErr) errSlot.appendChild(h('div', { class: 'err', role: 'alert' }, plan._submitErr));

    var cb = h('input', {
      type: 'checkbox',
      checked: !!plan._reviewedKnowledge,
      disabled: (submitting || !!notReadyReason) ? true : null,
      onchange: function () {
        plan._reviewedKnowledge = !!cb.checked;
        bApprove.disabled = submitting || !!notReadyReason || !plan._reviewedKnowledge;
      }
    });

    var viewQLink = h('button', {
      type: 'button',
      class: 'ail-link-inline',
      onclick: function () {
        m._detailsOpen = true;
        m._focusSection = 'questions';
        drawLog(false);
      }
    }, 'Xem bộ câu hỏi');

    var bApprove = btn(submitting ? 'Đang lưu...' : 'Duyệt & lưu', 'check', {
      cls: 'sm pri',
      onclick: function () {
        if (plan._submitting || plan._decided || notReadyReason) return;
        if (!plan._reviewedKnowledge) {
          toast('Vui lòng đánh dấu xác nhận đã kiểm tra câu hỏi và đáp án.', 'err');
          return;
        }
        if (isMock) {
          plan._decided = 'accepted_mock';
          toast('Trò chơi đã được lưu (phiên xem thử Mock).', 'ok');
          drawLog(false);
          return;
        }
        plan._submitting = true;
        plan._submitErr = null;
        drawLog(false);
        api('POST', '/api/agent/publish', {
          draft_id: plan.draft_id,
          plan_hash: plan.plan_hash,
          approved: true,
          reviewed_knowledge: true
        }).then(function (r) {
          plan._submitting = false;
          plan._decided = 'published';
          plan._appId = r.app_id;
          plan._playUrl = r.play_url;
          persistSession();
          toast('Trò chơi đã được lưu.', 'ok');
          drawLog(false);
        }).catch(function (e) {
          plan._submitting = false;
          plan._submitErr = (e && e.message) || 'Không thể lưu trò chơi. Vui lòng thử lại.';
          toast(plan._submitErr, 'err');
          drawLog(false);
        });
      }
    });
    bApprove.disabled = submitting || !!notReadyReason || !plan._reviewedKnowledge;

    var bReject = btn('Từ chối', 'x', {
      cls: 'sm bad',
      onclick: function () {
        if (plan._submitting || plan._decided) return;
        promptModal('Từ chối bản nháp', 'Ghi lý do từ chối (tùy chọn):', {
          confirmLabel: 'Xác nhận từ chối',
          fieldLabel: 'Lý do',
          placeholder: 'Ví dụ: câu hỏi chưa đúng chủ đề hoặc muốn đổi cách chơi...',
          minLen: 0,
          maxLen: 300
        }).then(function (reason) {
          if (reason == null) return;
          if (isMock) {
            plan._decided = 'rejected_mock';
            plan._rejectReason = reason;
            toast('Đã từ chối bản nháp.', 'info');
            drawLog(false);
            return;
          }
          plan._submitting = true;
          plan._submitErr = null;
          drawLog(false);
          api('POST', '/api/agent/review', {
            draft_id: plan.draft_id,
            action: 'reject',
            reason: reason
          }).then(function () {
            plan._submitting = false;
            plan._decided = 'rejected';
            plan._rejectReason = reason;
            persistSession();
            toast('Đã từ chối bản nháp.', 'ok');
            drawLog(false);
          }).catch(function (e) {
            plan._submitting = false;
            plan._submitErr = (e && e.message) || 'Không thể từ chối bản nháp.';
            toast(plan._submitErr, 'err');
            drawLog(false);
          });
        });
      }
    });
    bReject.disabled = submitting;

    return h('div', { class: 'ail-approval-card', 'data-draft-id': plan.draft_id || 'mock' },
      h('div', { class: 'ail-approval-head' },
        ico('shield'),
        h('b', null, 'Xác nhận trò chơi'),
        examInfo.hasExam ? viewQLink : null
      ),
      notReadyReason
        ? h('div', { class: 'ail-inline-warn', role: 'alert' }, ico('alert'), h('span', null, notReadyReason))
        : h('label', { class: 'ail-approval-check' }, cb, h('span', null, 'Tôi đã kiểm tra câu hỏi và đáp án')),
      errSlot,
      h('div', { class: 'ail-approval-actions' }, bApprove, bReject)
    );
  }

  /* ================= 8 · Quick Replies (ASK_CLARIFY) ================= */
  function quickReplies(plan, isLatest) {
    var q = plan && plan.decision === 'ASK_CLARIFY' ? (plan.quick_replies || []) : [];
    if (!q.length) return null;
    return h('div', { class: 'ail-quick-replies' }, q.map(function (qr) {
      return h('button', {
        type: 'button',
        class: 'ail-suggest-pill',
        disabled: isLatest ? null : true,
        onclick: function () { input.value = qr; autoResize(); submit(); }
      }, ico('chevR'), h('span', null, qr));
    }));
  }

  /* ================= 9 · Chế độ Soạn khung nhanh (/api/flow) inline ================= */
  function flowRun(label, steps, fn) {
    real.busy = true;
    send.disabled = true;
    real.thinkSteps = steps;
    drawLog(true);
    return fn().catch(function (e) {
      toast(e.message || label + ' không được.', 'err');
      real.msgs.push({ role: 'bot', text: '', error: e.message || label + ' không được.' });
    }).then(function () {
      real.busy = false;
      send.disabled = false;
      real.thinkSteps = null;
      drawLog(true);
    });
  }

  function pushBuilt(d, brief) {
    var f = Object.assign({ stage: 'built', brief: brief }, d);
    if (real.flowPlan) real.flowPlan.built = f;
    real.brief = null;
    real.msgs.push({ role: 'bot', text: d.message || '', flow: f });
    persistSession();
  }

  function flowApprove(fp) {
    if (!fp || fp.approved || real.busy) return;
    fp.approved = true;
    persistSession();
    flowRun('Tạo trò chơi', THINK_STEPS, function () {
      return api('POST', '/api/flow/build', { brief: fp.brief })
        .then(function (d) { pushBuilt(d, fp.brief); })
        .catch(function (e) { fp.approved = false; persistSession(); throw e; });
    });
  }

  function flowTry(f) {
    var wp = previewFrame(f.preview_url);
    modal('Chơi thử: ' + (f.name || f.player_name || 'Trò chơi'), flexModalBody([
      h('span', { class: 'meta' }, 'Chạy thử trong khung cách ly. Chuột luôn dùng được.'),
      wp
    ]), { cls: 'ail-try' });
  }

  function flowPlanInlineCard(f) {
    var fp = f._fp || real.flowPlan;
    var plan = f.plan || (fp && fp.plan) || {};
    var pl = plan.player || {};
    var lines = Array.isArray(plan.lines) ? plan.lines : [];
    var approved = !!(fp && fp.approved);
    return h('div', { class: 'ail-game-card' },
      h('div', { class: 'ail-gc-top' },
        h('div', { class: 'ail-gc-thumb' }, ico('sparkles')),
        h('div', { class: 'ail-gc-info' },
          h('div', { class: 'ail-gc-title' }, 'Kế hoạch: ' + (plan.name || 'Trò chơi mới')),
          h('div', { class: 'ail-gc-pills' },
            h('span', { class: 'ail-gc-pill' }, plan.answers === 2 ? 'Đúng / Sai (2 đáp án)' : (plan.answers || 4) + ' đáp án'),
            h('span', { class: 'ail-gc-pill' }, plan.model ? (KIND[plan.model.kind] || plan.model.kind) + ' · Có chuột' : 'Chỉ dùng chuột'),
            h('span', { class: 'ail-gc-pill' }, pl.mode === 'reuse_existing' ? 'Dùng lại kho trò chơi' : 'AI viết trò chơi mới')
          )
        )
      ),
      lines.length ? h('div', { class: 'ail-plan-fold-b', style: 'padding-top:10px;border-top:1px solid var(--jl-border-divider)' },
        h('ul', { class: 'ail-flow-steps' }, lines.map(function (ln) { return h('li', null, ln); }))
      ) : null,
      h('div', { class: 'ail-gc-actions' },
        !approved ? btn('Duyệt & tạo trò chơi', 'check', { cls: 'sm pri', onclick: function () { flowApprove(fp); } })
          : h('span', { class: 'ail-chip ok' }, 'Đã duyệt tạo trò chơi'),
        (!approved && pl.mode === 'reuse_existing') ? btn('Tạo game mới (không dùng lại)', 'sparkles', { cls: 'sm', onclick: function () { input.value = 'Đừng dùng lại game có sẵn, hãy tạo game mới khác'; submit(); } }) : null,
        (!approved && pl.mode === 'reuse_existing') ? btn('Xem game trong kho', 'grid', { cls: 'sm', onclick: function () { input.value = 'Xem các game trong kho'; submit(); } }) : null,
        !approved ? btn('Chỉnh lại', 'edit', { cls: 'sm', onclick: function () { input.placeholder = 'Bạn muốn đổi gì? (số đáp án: 2/3/4, điều khiển: chuột/hình ảnh/tư thế/âm thanh...)'; focusInput(); } }) : null
      )
    );
  }

  function flowBuiltCard(f, active) {
    var card = h('div', { class: 'ail-game-card' });
    card.appendChild(
      h('div', { class: 'ail-gc-top' },
        h('div', { class: 'ail-gc-thumb' }, ico('play')),
        h('div', { class: 'ail-gc-info' },
          h('div', { class: 'ail-gc-title' }, f.name || f.player_name || 'Trò chơi mới'),
          h('div', { class: 'ail-gc-pills' },
            h('span', { class: 'ail-gc-pill' }, f.kind === 'reuse' ? 'Kho trò chơi' : 'Phiên bản ' + (f.version || 1)),
            (f.flags && f.flags.length)
              ? h('span', { class: 'ail-gc-pill is-warn' }, f.flags.length + ' cảnh báo an toàn')
              : h('span', { class: 'ail-gc-pill' }, 'Đã kiểm tra an toàn')
          )
        )
      )
    );

    var actions = h('div', { class: 'ail-gc-actions' },
      btn('Chơi thử', 'play', { cls: 'sm pri', onclick: function () { flowTry(f); } })
    );
    card.appendChild(actions);

    if (!active) return card;
    if (f.accepted) {
      actions.appendChild(btn('Ghép thành ứng dụng', 'grid', { cls: 'sm', href: '#/apps/new?player=' + f.player_id }));
      return card;
    }
    if (f.kind === 'reuse') {
      actions.appendChild(btn('Ghép thành ứng dụng', 'grid', { cls: 'sm', href: '#/apps/new?player=' + f.player_id }));
      return card;
    }

    var noFixesLeft = typeof f.fixes_left === 'number' && f.fixes_left <= 0;
    var fb = h('textarea', {
      rows: 2,
      maxlength: 1500,
      'aria-label': 'Bạn muốn sửa gì',
      placeholder: noFixesLeft ? 'Đã hết lượt sửa tự động — bạn hãy lưu trình chơi rồi chỉnh tiếp trong Kho mẫu game.' : 'Chơi thử xong, bạn muốn AI chỉnh sửa gì?',
      class: 'ail-in',
      disabled: noFixesLeft ? true : null,
      style: 'width:100%'
    });
    var bFix = btn(typeof f.fixes_left === 'number' ? 'Chỉnh sửa (' + f.fixes_left + ')' : 'Chỉnh sửa', 'edit', {
      cls: 'sm',
      disabled: noFixesLeft,
      onclick: function () {
        var t = fb.value.trim();
        if (t.length < 3) { toast('Hãy mô tả ngắn điểm muốn sửa.', 'err'); fb.focus(); return; }
        flowRun('Chỉnh sửa trò chơi', ['Đang chỉnh sửa trò chơi...', 'Đang kiểm tra trò chơi...'], function () {
          return api('POST', '/api/flow/fix', { draftId: f.draft_id, feedback: t })
            .then(function (d) { real.msgs.push({ role: 'user', text: 'Sửa: ' + t }); pushBuilt(d, f.brief); });
        });
      }
    });
    var bOk = btn('Lưu trình chơi', 'check', {
      cls: 'sm pri',
      onclick: function () {
        bOk.disabled = true;
        api('POST', '/api/flow/accept', { draftId: f.draft_id }).then(function (d) {
          f.accepted = true;
          f.player_id = d.player_id;
          persistSession();
          toast('Đã lưu trình chơi.', 'ok');
          drawLog(false);
        }).catch(function (e) { bOk.disabled = false; toast(e.message, 'err'); });
      }
    });
    card.appendChild(h('div', { class: 'ail-flow-edit-box' }, fb, h('div', { class: 'row' }, bOk, bFix)));
    return card;
  }

  function flowCard(m) {
    var f = m.flow;
    var idx = real.msgs.indexOf(m);
    if (f.stage === 'catalog') {
      var pls = Array.isArray(f.players) ? f.players : [];
      var liveCat = idx === real.msgs.length - 1 && !real.busy;
      var wrap = h('div', { style: 'display:flex;flex-direction:column;gap:8px;margin-top:6px' });
      pls.forEach(function (p) {
        wrap.appendChild(
          h('div', { class: 'ail-game-card' },
            h('div', { class: 'ail-gc-top' },
              h('div', { class: 'ail-gc-thumb' }, ico('grid')),
              h('div', { class: 'ail-gc-info' },
                h('div', { class: 'ail-gc-title' }, p.name || ('Trò chơi #' + p.id)),
                p.description ? h('p', { class: 'ail-gc-desc' }, p.description) : null,
                h('div', { class: 'ail-gc-pills' },
                  p.game_kind ? h('span', { class: 'ail-gc-pill' }, p.game_kind) : null,
                  p.control ? h('span', { class: 'ail-gc-pill' }, p.control) : null
                )
              )
            ),
            h('div', { class: 'ail-gc-actions' },
              btn('Chơi thử', 'play', { cls: 'sm pri', onclick: function () { flowTry({ name: p.name, preview_url: p.preview_url }); } }),
              btn('Ghép thành ứng dụng', 'grid', { cls: 'sm', href: '#/apps/new?player=' + p.id })
            )
          )
        );
      });
      if ((f.quick_replies || []).length) {
        wrap.appendChild(h('div', { class: 'ail-quick-replies' }, f.quick_replies.map(function (q) {
          return h('button', {
            type: 'button',
            class: 'ail-suggest-pill',
            disabled: liveCat ? null : true,
            onclick: function () { input.value = q; submit(); }
          }, ico('chevR'), h('span', null, q));
        })));
      }
      return wrap;
    }
    if (f.stage === 'ask' || f.stage === 'disambiguate') {
      var live = idx === real.msgs.length - 1 && !real.busy;
      return (f.quick_replies || []).length
        ? h('div', { class: 'ail-quick-replies' }, f.quick_replies.map(function (q) {
            return h('button', {
              type: 'button',
              class: 'ail-suggest-pill',
              disabled: live ? null : true,
              onclick: function () { input.value = q; submit(); }
            }, ico('chevR'), h('span', null, q));
          }))
        : null;
    }
    if (f.stage === 'plan') return flowPlanInlineCard(f);
    if (f.stage === 'built') {
      var last = -1;
      for (var i = real.msgs.length - 1; i >= 0; i--) {
        if (real.msgs[i].flow && real.msgs[i].flow.stage === 'built') { last = i; break; }
      }
      return flowBuiltCard(f, idx === last);
    }
    return null;
  }

  /* ================= 10 · Legacy Proposal Card (lịch sử /api/chats cũ) ================= */
  function decideLegacy(p, action, holder, btns) {
    btns.forEach(function (b) { b.disabled = true; });
    api('POST', '/api/chats/' + real.chatId + '/proposals/' + p.index + '/' + action).then(function (r) {
      p.status = r.status;
      if (r.playerId) p.playerId = r.playerId;
      toast(action === 'accept' ? 'Đã lưu trình chơi.' : 'Đã từ chối đề xuất.', 'ok');
      drawLog(false);
    }).catch(function (e) {
      if (e.status === 409) { resyncChat(); return; }
      btns.forEach(function (b) { b.disabled = false; });
      var old = holder.querySelector('.err'); if (old) old.remove();
      holder.appendChild(errBox(e));
    });
  }

  function legacyProposalCard(m) {
    var p = m.proposal;
    var holder = h('div', { class: 'ail-game-card' });
    holder.appendChild(
      h('div', { class: 'ail-gc-top' },
        h('div', { class: 'ail-gc-thumb' }, ico('play')),
        h('div', { class: 'ail-gc-info' },
          h('div', { class: 'ail-gc-title' }, p.name || 'Trò chơi đề xuất'),
          p.description ? h('p', { class: 'ail-gc-desc' }, p.description) : null
        )
      )
    );
    var row = h('div', { class: 'ail-gc-actions' });
    if (real.chatId != null) {
      row.appendChild(btn('Chơi thử', 'play', {
        cls: 'sm pri',
        onclick: function () {
          var w = previewFrame('/api/chats/' + real.chatId + '/proposals/' + p.index + '/try');
          modal('Chơi thử: ' + p.name, flexModalBody([w]), { cls: 'ail-try' });
        }
      }));
    }
    if (p.status === 'pending') {
      var bAcc = btn('Lưu trình chơi', 'check', { cls: 'sm', onclick: function () { decideLegacy(p, 'accept', holder, [bAcc, bRej]); } });
      var bRej = btn('Từ chối', 'x', { cls: 'sm bad', onclick: function () { decideLegacy(p, 'reject', holder, [bAcc, bRej]); } });
      row.appendChild(bAcc);
      row.appendChild(bRej);
    } else if (p.status === 'accepted') {
      row.appendChild(h('span', { class: 'ail-chip ok' }, 'Đã lưu'));
      row.appendChild(btn('Xem trong Kho mẫu game', 'grid', { cls: 'sm', href: '#/players' }));
    } else {
      row.appendChild(h('span', { class: 'ail-chip bad' }, 'Đã từ chối'));
    }
    holder.appendChild(row);
    return holder;
  }

  /* ================= 11 · Render từng tin nhắn ================= */
  function msgEl(m, idx, total) {
    if (m.role === 'user') {
      return h('div', { class: 'ail-msg ail-msg-user' },
        h('div', { class: 'ail-user-bubble' }, m.text || '')
      );
    }

    var body = h('div', { class: 'ail-msg-body' });

    if (m.error) {
      body.appendChild(h('div', { class: 'err', role: 'alert' }, m.error));
      if (m.retryText) {
        body.appendChild(h('div', { class: 'row', style: 'margin-top:8px' },
          btn('Thử lại', 'refresh', {
            cls: 'sm',
            onclick: function () { if (!input.value.trim()) input.value = m.retryText; autoResize(); submit(); }
          })
        ));
      }
      return h('div', { class: 'ail-msg ail-msg-bot' },
        h('span', { class: 'ail-bot-avatar', 'aria-hidden': 'true' }, ico('sparkles')),
        body
      );
    }

    var isMock = mode === 'mock' || !!(m.plan && m.plan.simulated);
    var displayText = m.text || '';
    if (m.plan) {
      var examInfo = m.plan.application_plan ? analyzeExam(m.plan.application_plan, catalogCache.examsById) : null;
      displayText = conciseAssistantText(m.plan, examInfo);
    }
    if (displayText) {
      body.appendChild(h('div', { class: 'ail-bot-text' }, displayText));
    }

    if (m.flow) {
      var fc = flowCard(m);
      if (fc) body.appendChild(fc);
    } else if (m.plan) {
      if (m.plan.application_plan) {
        body.appendChild(renderGameCard(m, m.plan, isMock));
        var hitl = renderContextualHitl(m, m.plan, isMock);
        if (hitl) body.appendChild(hitl);
      } else {
        var qr = quickReplies(m.plan, idx === total - 1 && !(mode === 'mock' ? mock.busy : real.busy));
        if (qr) body.appendChild(qr);
      }
    } else if (m.proposal) {
      body.appendChild(legacyProposalCard(m));
    }

    return h('div', { class: 'ail-msg ail-msg-bot' },
      h('span', { class: 'ail-bot-avatar', 'aria-hidden': 'true' }, ico('sparkles')),
      body
    );
  }

  function drawLog(forceScroll) {
    var wasNearBottom = (log.scrollHeight - log.scrollTop - log.clientHeight) < 140;
    var list = mode === 'mock' ? mock.msgs : real.msgs;
    var busy = mode === 'mock' ? mock.busy : real.busy;
    var isEmpty = !list.length && !busy && !(mode !== 'mock' && real.openErr);

    main.classList.toggle('is-empty', isEmpty);
    send.disabled = busy;
    stopThink();
    log.replaceChildren();

    if (mode !== 'mock' && real.openErr) {
      log.appendChild(h('div', { class: 'ail-chat-stream' },
        h('div', { class: 'err', role: 'alert' }, 'Không tải được lịch sử: ' + (real.openErr.e && real.openErr.e.message || 'Vui lòng thử lại.')),
        h('div', { style: 'margin-top:8px' }, btn('Thử lại', 'refresh', { cls: 'sm', onclick: function () { openChat(real.openErr.id); } }))
      ));
    }

    if (isEmpty) {
      log.appendChild(emptyState());
    } else {
      var stream = h('div', { class: 'ail-chat-stream' });
      list.forEach(function (m, i) { stream.appendChild(msgEl(m, i, list.length)); });
      if (busy) stream.appendChild(thinkingEl());
      log.appendChild(stream);
    }

    renderEmptySuggestions(isEmpty);

    if (forceScroll !== false && (forceScroll === true || wasNearBottom || busy)) {
      log.scrollTop = log.scrollHeight;
    }
  }

  function drawAll() { drawHead(); drawBanner(); drawSide(); drawLog(); }

  /* ================= 12 · Gửi tin nhắn ================= */
  function submit() {
    if (mode === 'real') submitAgent();
    else if (mode === 'flow') submitFlow();
    else submitMock();
  }

  function submitAgent() {
    var t = input.value.trim();
    if (real.busy || t.length < 3) return;
    real.busy = true;
    send.disabled = true;
    real.thinkSteps = null;
    real.msgs.push({ role: 'user', text: t });
    input.value = '';
    input.style.height = '';
    persistSession();
    drawLog(true);

    var reqBody = { text: t };
    if (real.conversationId != null) reqBody.conversation_id = real.conversationId;
    api('POST', '/api/agent', reqBody).then(function (d) {
      var plan = d || {};
      if (plan.conversation_id != null) real.conversationId = plan.conversation_id;
      real.msgs.push({ role: 'bot', text: plan.message || '', plan: plan, simulated: !!plan.simulated });
      persistSession();
    }).catch(function (e) {
      real.msgs.push({ role: 'bot', text: '', error: (e && e.message) || 'Không thể kết nối máy chủ AI.', retryText: t });
      if (!input.value.trim()) input.value = t;
    }).then(function () {
      real.busy = false;
      send.disabled = false;
      drawLog(true);
      focusInput();
    });
  }

  function submitFlow() {
    var t = input.value.trim();
    if (real.busy || t.length < 2) return;
    real.busy = true;
    send.disabled = true;
    real.thinkSteps = ['Đang đọc yêu cầu...', 'Đang chuẩn bị trò chơi...'];
    real.msgs.push({ role: 'user', text: t });
    input.value = '';
    input.style.height = '';
    input.placeholder = defaultPlaceholder(mode);
    persistSession();
    drawLog(true);

    api('POST', '/api/flow', { text: t, brief: real.brief }).then(function (d) {
      real.brief = d.brief || real.brief;
      if (d.stage === 'plan') {
        real.flowPlan = { plan: d.plan, brief: d.brief, approved: false, built: null };
        d._fp = real.flowPlan;
      }
      real.msgs.push({ role: 'bot', text: d.message || '', flow: d });
      persistSession();
    }).catch(function (e) {
      real.msgs.push({ role: 'bot', text: '', error: (e && e.message) || 'Không thể kết nối máy chủ AI.', retryText: t });
      if (!input.value.trim()) input.value = t;
    }).then(function () {
      real.busy = false;
      send.disabled = false;
      real.thinkSteps = null;
      drawLog(true);
      focusInput();
    });
  }

  function ensureMockCatalog() {
    if (mock.catalog) return Promise.resolve(mock.catalog);
    return Promise.all([
      api('GET', '/api/players?scope=usable').catch(function () { return { players: [] }; }),
      api('GET', '/api/models?scope=usable').catch(function () { return { models: [] }; })
    ]).then(function (r) {
      mock.catalog = { players: (r[0] && r[0].players) || [], models: (r[1] && r[1].models) || [] };
      return mock.catalog;
    });
  }

  function submitMock() {
    var t = input.value.trim();
    if (mock.busy || t.length < 3) return;
    mock.busy = true;
    send.disabled = true;
    mock.msgs.push({ role: 'user', text: t });
    input.value = '';
    input.style.height = '';
    drawLog(true);

    ensureMockCatalog().then(function (cat) {
      return wait(MOCK_LATENCY).then(function () { return runMockComposer(t, cat); });
    }).then(function (plan) {
      mock.msgs.push({ role: 'bot', text: plan.message || '', plan: plan });
    }).catch(function (e) {
      mock.msgs.push({ role: 'bot', text: '', error: e.message, retryText: t });
      if (!input.value.trim()) input.value = t;
    }).then(function () {
      mock.busy = false;
      send.disabled = false;
      drawLog(true);
      focusInput();
    });
  }

  send.addEventListener('click', submit);
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && (!e.shiftKey || e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      submit();
    }
  });

  /* ---------- Gắn Single Chat Workspace vào shell (KHÔNG có Plan Panel bên phải) ---------- */
  mountFn(h('div', { class: 'ail-chat-wrap' }, main));
  drawAll();
}
