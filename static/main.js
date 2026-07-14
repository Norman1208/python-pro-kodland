/* =========================================================
   main.js — Auth, Quiz Session, Leaderboard, Weather, Scores
   ========================================================= */

// ── Helper: fetch JSON ────────────────────────────────────
async function api(url, opts) {
  opts = opts || {};
  opts.headers = opts.headers || {};
  if (!opts.headers['Content-Type']) opts.headers['Content-Type'] = 'application/json';
  const resp = await fetch(url, opts);
  return resp.json();
}

// ── Score Widget (runs on every page) ────────────────────
async function loadScoreWidget() {
  try {
    const data = await api('/api/scores');
    const globalEl = document.getElementById('globalBest');
    const userEl   = document.getElementById('userBest');
    if (globalEl) globalEl.textContent = data.global_best.toFixed(1) + '%';
    if (userEl)   userEl.textContent   = data.user_best.toFixed(1) + '%';
  } catch(e) { /* silent */ }
}
loadScoreWidget();

// ── Register ──────────────────────────────────────────────
const registerForm = document.getElementById('registerForm');
if (registerForm) {
  registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd  = Object.fromEntries(new FormData(e.target));
    const msg = document.getElementById('registerMsg');
    msg.className = 'form-msg';
    const res = await api('/api/register', {
      method: 'POST',
      body: JSON.stringify({ username: fd.username, display_name: fd.display_name, password: fd.password, confirm: fd.confirm })
    });
    if (res.error) {
      msg.textContent = res.error;
      msg.classList.add('error');
    } else {
      msg.textContent = res.message;
      msg.classList.add('success');
      setTimeout(() => location.href = '/login', 1400);
    }
  });
}

// ── Login ─────────────────────────────────────────────────
const loginForm = document.getElementById('loginForm');
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd  = Object.fromEntries(new FormData(e.target));
    const msg = document.getElementById('loginMsg');
    msg.className = 'form-msg';
    const res = await api('/api/login', {
      method: 'POST',
      body: JSON.stringify({ username: fd.username, password: fd.password })
    });
    if (res.error) {
      msg.textContent = res.error;
      msg.classList.add('error');
    } else {
      msg.textContent = 'Berhasil masuk!';
      msg.classList.add('success');
      setTimeout(() => location.href = '/quiz', 800);
    }
  });
}

// ── Logout ────────────────────────────────────────────────
const logoutBtn = document.getElementById('logoutBtn');
if (logoutBtn) {
  logoutBtn.addEventListener('click', async () => {
    await api('/api/logout', { method: 'POST' });
    location.href = '/';
  });
}

// ── Weather ───────────────────────────────────────────────
const getWeatherBtn = document.getElementById('getWeatherBtn');
if (getWeatherBtn) {
  getWeatherBtn.addEventListener('click', async () => {
    const city = document.getElementById('cityInput').value.trim() || 'Jakarta';
    const container = document.getElementById('weatherResult');
    container.innerHTML = '<p style="color:var(--text-muted)">⏳ Memuat data cuaca...</p>';
    const res = await api(`/api/weather?city=${encodeURIComponent(city)}`);
    if (res.error) {
      container.innerHTML = `<p style="color:var(--danger)">${res.error}${res.detail ? ': ' + res.detail : ''}</p>`;
      return;
    }
    let html = `<h3>${res.city}</h3><table><thead><tr><th>Tanggal</th><th>Hari</th><th>Siang (°C)</th><th>Malam (°C)</th><th>Cuaca</th></tr></thead><tbody>`;
    for (const d of res.forecast) {
      html += `<tr><td>${d.date}</td><td>${d.day}</td><td>${d.temp_day}</td><td>${d.temp_night}</td><td>${d.weather}</td></tr>`;
    }
    html += '</tbody></table>';
    container.innerHTML = html;
  });
}

// ── Leaderboard ───────────────────────────────────────────
async function loadLeaderboard() {
  const table = document.getElementById('leaderboardTable');
  if (!table) return;
  const data  = await api('/api/leaderboard');
  const tbody = table.querySelector('tbody');
  tbody.innerHTML = '';
  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="loading-row">Belum ada data.</td></tr>';
    return;
  }
  const medals = ['🥇', '🥈', '🥉'];
  data.forEach((u, i) => {
    const tr = document.createElement('tr');
    const rank = medals[i] ? `<span class="rank-medal">${medals[i]}</span>` : `${i + 1}`;
    tr.innerHTML = `<td>${rank}</td><td>${u.display_name}</td><td>${u.username}</td><td><strong>${u.best_score.toFixed(1)}%</strong></td>`;
    tbody.appendChild(tr);
  });
}
loadLeaderboard();

// =========================================================
// QUIZ SESSION (5 soal per percobaan)
// =========================================================

// State
let questions    = [];
let currentIdx   = 0;
let userAnswers  = {};   // { questionId: choiceId }

// Elements
const screenStart  = document.getElementById('screenStart');
const screenQuiz   = document.getElementById('screenQuiz');
const screenResult = document.getElementById('screenResult');

if (screenStart) {

  // ── Start ──────────────────────────────────────────────
  document.getElementById('startQuizBtn').addEventListener('click', async () => {
    const data = await api('/api/quiz/questions');
    if (data.error || !data.questions || !data.questions.length) {
      alert('Soal tidak tersedia. Hubungi admin.');
      return;
    }
    questions   = data.questions;
    currentIdx  = 0;
    userAnswers = {};
    switchScreen('quiz');
    renderQuestion();
  });

  // ── Navigation ─────────────────────────────────────────
  document.getElementById('prevBtn').addEventListener('click', () => {
    if (currentIdx > 0) { currentIdx--; renderQuestion(); }
  });
  document.getElementById('nextBtn').addEventListener('click', () => {
    if (currentIdx < questions.length - 1) { currentIdx++; renderQuestion(); }
  });

  // ── Submit ─────────────────────────────────────────────
  document.getElementById('submitQuizBtn').addEventListener('click', async () => {
    const answers = Object.entries(userAnswers).map(([qid, cid]) => ({
      question_id: parseInt(qid),
      choice_id:   parseInt(cid)
    }));
    const res = await api('/api/quiz/submit', {
      method: 'POST',
      body:   JSON.stringify({ answers })
    });
    showResult(res);
    loadScoreWidget();   // refresh widget
  });

  // ── Retry ──────────────────────────────────────────────
  document.getElementById('retryBtn').addEventListener('click', () => {
    switchScreen('start');
  });
}

// ── Render one question ───────────────────────────────────
function renderQuestion() {
  if (!questions.length) return;
  const q = questions[currentIdx];

  // Progress
  const pct = ((currentIdx + 1) / questions.length * 100).toFixed(0);
  document.getElementById('progressFill').style.width = pct + '%';
  document.getElementById('questionCounter').textContent = `Soal ${currentIdx + 1} / ${questions.length}`;

  // Category badge
  const catMap = { nlp: 'NLP', computer_vision: 'Computer Vision', discord: 'Discord.py', flask: 'Flask', general: 'Umum' };
  document.getElementById('categoryBadge').textContent = catMap[q.category] || q.category;

  // Question text
  document.getElementById('questionText').textContent = q.text;

  // Choices
  const list = document.getElementById('choicesList');
  list.innerHTML = '';
  for (const c of q.choices) {
    const btn = document.createElement('button');
    btn.className = 'choice-btn';
    btn.textContent = c.text;
    if (userAnswers[q.id] === c.id) btn.classList.add('selected');
    btn.addEventListener('click', () => {
      userAnswers[q.id] = c.id;
      renderQuestion();        // re-render to update selection + counters
    });
    list.appendChild(btn);
  }

  // Nav buttons
  document.getElementById('prevBtn').disabled = currentIdx === 0;
  document.getElementById('nextBtn').disabled = currentIdx === questions.length - 1;

  // Answered count + submit
  const answeredCount = Object.keys(userAnswers).length;
  document.getElementById('answeredCount').textContent = `${answeredCount} / ${questions.length} dijawab`;
  const submitBtn  = document.getElementById('submitQuizBtn');
  const submitHint = document.getElementById('submitHint');
  if (answeredCount === questions.length) {
    submitBtn.disabled  = false;
    submitHint.textContent = 'Semua soal sudah dijawab — klik Submit!';
    submitHint.style.color = 'var(--success)';
  } else {
    submitBtn.disabled  = true;
    submitHint.textContent = 'Jawab semua soal sebelum submit';
    submitHint.style.color = '';
  }
}

// ── Show result screen ────────────────────────────────────
function showResult(res) {
  switchScreen('result');
  const pct = res.score_pct || 0;

  // Emoji & title
  let emoji = '😔', title = 'Terus Semangat!';
  if (pct >= 80) { emoji = '🎉'; title = 'Luar Biasa!'; }
  else if (pct >= 60) { emoji = '👍'; title = 'Bagus!'; }
  else if (pct >= 40) { emoji = '🙂'; title = 'Lumayan!'; }
  document.getElementById('resultEmoji').textContent = emoji;
  document.getElementById('resultTitle').textContent = title;

  document.getElementById('resultPct').textContent = pct + '%';
  document.getElementById('resultDetail').textContent =
    `Kamu menjawab ${res.correct} dari ${res.total} soal dengan benar`;

  // New best banner
  const banner = document.getElementById('newBestBanner');
  const prevInfo = document.getElementById('prevBestInfo');
  if (res.is_new_best) {
    banner.classList.remove('hidden');
    prevInfo.textContent = res.previous_best > 0 ? `(Sebelumnya: ${res.previous_best}%)` : '';
  } else {
    banner.classList.add('hidden');
    prevInfo.textContent = `Rekor terbaikmu: ${res.previous_best}%`;
  }

  // Review list
  const reviewList = document.getElementById('reviewList');
  reviewList.innerHTML = '';
  for (const r of (res.results || [])) {
    const item = document.createElement('div');
    item.className = 'review-item ' + (r.correct ? 'correct' : 'wrong');
    item.innerHTML = `
      <div class="ri-question">${r.correct ? '✅' : '❌'} ${r.question_text}</div>
      <div class="ri-answer">Jawabanmu: ${r.your_answer}</div>
      ${!r.correct ? `<div class="ri-correct-ans">Jawaban benar: ${r.correct_answer}</div>` : ''}
    `;
    reviewList.appendChild(item);
  }
}

// ── Switch screen helper ──────────────────────────────────
function switchScreen(name) {
  ['screenStart', 'screenQuiz', 'screenResult'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.remove('active');
  });
  const target = document.getElementById('screen' + name.charAt(0).toUpperCase() + name.slice(1));
  if (target) target.classList.add('active');
}
