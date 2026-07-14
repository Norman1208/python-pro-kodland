/* =========================================================
   detect.js — Teachable Machine Image Classification
   =========================================================
   Requires (loaded in detect.html):
     - @tensorflow/tfjs
     - @teachablemachine/image
   ========================================================= */

let model        = null;      // loaded TM model
let lastResult   = null;      // { predicted_class, confidence }
let labelContainer = [];

// ── DOM refs ──────────────────────────────────────────────
const modelUrlInput  = document.getElementById('modelUrlInput');
const loadModelBtn   = document.getElementById('loadModelBtn');
const modelStatus    = document.getElementById('modelStatus');
const uploadArea     = document.getElementById('uploadArea');
const imageInput     = document.getElementById('imageInput');
const uploadPlaceholder = document.getElementById('uploadPlaceholder');
const previewImg     = document.getElementById('previewImg');
const chooseFileBtn  = document.getElementById('chooseFileBtn');
const classifyBtn    = document.getElementById('classifyBtn');
const detectResult   = document.getElementById('detectResult');
const saveDetectBtn  = document.getElementById('saveDetectBtn');
const saveMsg        = document.getElementById('saveMsg');
const detectHistory  = document.getElementById('detectHistory');

// ── Load Model ────────────────────────────────────────────
loadModelBtn.addEventListener('click', async () => {
  const url = modelUrlInput.value.trim();
  if (!url) { setModelStatus('❌ Masukkan URL model terlebih dahulu.', 'error'); return; }
  setModelStatus('⏳ Memuat model, harap tunggu...', 'loading');
  loadModelBtn.disabled = true;
  try {
    const modelURL    = url.endsWith('/') ? url : url + '/';
    const metadataURL = modelURL + 'metadata.json';
    model = await tmImage.load(modelURL + 'model.json', metadataURL);
    setModelStatus(`✅ Model berhasil dimuat! (${model.getTotalClasses()} kelas)`, 'success');
    if (previewImg.src && !previewImg.classList.contains('hidden')) {
      classifyBtn.disabled = false;
    }
  } catch (err) {
    setModelStatus('❌ Gagal memuat model. Periksa URL dan pastikan model publik.', 'error');
    console.error(err);
  }
  loadModelBtn.disabled = false;
});

// ── File upload ───────────────────────────────────────────
chooseFileBtn.addEventListener('click', () => imageInput.click());
uploadArea.addEventListener('click', () => imageInput.click());

imageInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (file) showPreview(file);
});

// Drag & drop
uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('dragover'); });
uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
uploadArea.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadArea.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) showPreview(file);
});

function showPreview(file) {
  const reader = new FileReader();
  reader.onload = (ev) => {
    previewImg.src = ev.target.result;
    previewImg.classList.remove('hidden');
    uploadPlaceholder.classList.add('hidden');
    if (model) classifyBtn.disabled = false;
    detectResult.innerHTML = '<p class="result-placeholder">Klik "Klasifikasi" untuk memproses gambar ini.</p>';
    saveDetectBtn.disabled = true;
    saveMsg.textContent    = '';
    lastResult             = null;
  };
  reader.readAsDataURL(file);
}

// ── Classify ──────────────────────────────────────────────
classifyBtn.addEventListener('click', async () => {
  if (!model) { setModelStatus('⚠️ Muat model terlebih dahulu!', 'error'); return; }
  if (previewImg.classList.contains('hidden')) { alert('Pilih gambar terlebih dahulu!'); return; }

  classifyBtn.disabled = true;
  classifyBtn.textContent = '⏳ Memproses...';
  detectResult.innerHTML = '<p class="result-placeholder">⏳ Menganalisis gambar...</p>';

  try {
    const predictions = await model.predict(previewImg);
    // Sort by probability descending
    predictions.sort((a, b) => b.probability - a.probability);
    const top = predictions[0];

    lastResult = {
      predicted_class: top.className,
      confidence:      top.probability
    };

    renderPredictions(predictions);
    saveDetectBtn.disabled = false;
  } catch (err) {
    detectResult.innerHTML = `<p style="color:var(--danger)">❌ Error saat klasifikasi: ${err.message}</p>`;
    console.error(err);
  }

  classifyBtn.disabled = false;
  classifyBtn.textContent = '🔍 Klasifikasi';
});

function renderPredictions(predictions) {
  const top  = predictions[0];
  const conf = (top.probability * 100).toFixed(1);

  let html = `
    <div class="detect-class">🏷️ ${top.className}</div>
    <div class="detect-conf">Confidence: <strong>${conf}%</strong></div>
    <div class="conf-bar-wrap">
      <div class="conf-bar-fill" style="width:${conf}%"></div>
    </div>
    <div class="all-classes">
      <h4>Semua Kelas:</h4>
  `;
  for (const p of predictions) {
    const pct = (p.probability * 100).toFixed(1);
    html += `
      <div class="class-row">
        <span class="class-row-name">${p.className}</span>
        <div class="class-row-bar"><div class="class-row-fill" style="width:${pct}%"></div></div>
        <span class="class-row-pct">${pct}%</span>
      </div>
    `;
  }
  html += '</div>';
  detectResult.innerHTML = html;
}

// ── Save to DB ────────────────────────────────────────────
saveDetectBtn.addEventListener('click', async () => {
  if (!lastResult) return;
  saveDetectBtn.disabled = true;
  saveMsg.textContent    = '⏳ Menyimpan...';

  const res = await fetch('/api/detect/save', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(lastResult)
  }).then(r => r.json());

  if (res.error) {
    saveMsg.textContent = '❌ ' + res.error;
    saveDetectBtn.disabled = false;
  } else {
    saveMsg.textContent = '✅ ' + res.message;
    loadHistory();
  }
});

// ── Load history ──────────────────────────────────────────
async function loadHistory() {
  try {
    const data = await fetch('/api/detect/history').then(r => r.json());
    if (!data.length) {
      detectHistory.innerHTML = '<p class="result-placeholder">Belum ada riwayat deteksi.</p>';
      return;
    }
    detectHistory.innerHTML = data.map(d => `
      <div class="history-item">
        <span class="history-class">🏷️ ${d.predicted_class}</span>
        <div class="history-meta">
          <div>${(d.confidence * 100).toFixed(1)}% confidence</div>
          <div>${d.timestamp}</div>
        </div>
      </div>
    `).join('');
  } catch(e) { /* silent */ }
}
loadHistory();

// ── Helpers ───────────────────────────────────────────────
function setModelStatus(msg, type) {
  modelStatus.textContent = msg;
  modelStatus.style.color = type === 'success' ? 'var(--success)'
                          : type === 'error'   ? 'var(--danger)'
                          : 'var(--text-muted)';
}
