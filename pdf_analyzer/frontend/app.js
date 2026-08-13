/* ================================================================
   DOCMIND — app.js  |  Talks directly to /ingest and /query
   ================================================================ */

const API = 'http://127.0.0.1:8000';
const INNGEST = 'http://127.0.0.1:8288';

// ── State ─────────────────────────────────────────────────────────
let selectedFile = null;
let ingestHistory = [];
let isQuerying = false;

// ── Animated particle canvas ──────────────────────────────────────
(function initCanvas() {
    const canvas = document.getElementById('bg-canvas');
    const ctx = canvas.getContext('2d');
    let W, H, particles = [];

    const resize = () => { W = canvas.width = innerWidth; H = canvas.height = innerHeight; };
    resize();
    window.addEventListener('resize', resize);

    class Particle {
        constructor() { this.reset(); }
        reset() {
            this.x = Math.random() * W; this.y = Math.random() * H;
            this.vx = (Math.random() - .5) * .3; this.vy = (Math.random() - .5) * .3;
            this.r = Math.random() * 1.5 + .5; this.a = Math.random() * .5 + .1;
            this.hue = [240, 260, 280, 160][Math.floor(Math.random() * 4)];
        }
        update() { this.x += this.vx; this.y += this.vy; if (this.x < 0 || this.x > W || this.y < 0 || this.y > H) this.reset(); }
        draw() { ctx.beginPath(); ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2); ctx.fillStyle = `hsla(${this.hue},80%,70%,${this.a})`; ctx.fill(); }
    }

    for (let i = 0; i < 120; i++) particles.push(new Particle());

    const loop = () => {
        ctx.clearRect(0, 0, W, H);
        particles.forEach(p => { p.update(); p.draw(); });
        // Draw faint connecting lines between nearby particles
        for (let i = 0; i < particles.length; i++)
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x, dy = particles[i].y - particles[j].y;
                const d = Math.sqrt(dx * dx + dy * dy);
                if (d < 90) { ctx.beginPath(); ctx.moveTo(particles[i].x, particles[i].y); ctx.lineTo(particles[j].x, particles[j].y); ctx.strokeStyle = `rgba(99,102,241,${.08 * (1 - d / 90)})`; ctx.lineWidth = .6; ctx.stroke(); }
            }
        requestAnimationFrame(loop);
    };
    loop();
})();

// ── Tabs ──────────────────────────────────────────────────────────
function switchTab(tab) {
    const isUpload = tab === 'upload';
    document.getElementById('panel-upload').style.display = isUpload ? '' : 'none';
    document.getElementById('panel-query').style.display = isUpload ? 'none' : '';
    document.getElementById('nav-upload').classList.toggle('active', isUpload);
    document.getElementById('nav-query').classList.toggle('active', !isUpload);
}

// ── Status pill ───────────────────────────────────────────────────
function setStatus(label, type = 'ready') {
    document.querySelector('.status-dot').className = 'status-dot' + (type === 'loading' ? ' loading' : type === 'error' ? ' error' : '');
    document.getElementById('status-label').textContent = label;
}

// ── File drop zone ────────────────────────────────────────────────
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('drag-over'); const f = e.dataTransfer.files[0]; if (f) handleFile(f); });
dropZone.addEventListener('click', e => { if (!e.target.closest('.drop-file-info') && !e.target.closest('.inline-btn')) fileInput.click(); });
fileInput.addEventListener('change', () => { if (fileInput.files[0]) handleFile(fileInput.files[0]); });

function handleFile(f) {
    if (!f.name.toLowerCase().endsWith('.pdf')) { showToast('Only PDF files are supported.'); return; }
    selectedFile = f;
    document.getElementById('drop-icon').style.display = 'none';
    document.querySelector('.drop-content').style.display = 'none';
    const fi = document.getElementById('drop-file-info');
    fi.style.display = 'flex';
    document.getElementById('file-name-display').textContent = f.name;
    document.getElementById('file-size-display').textContent = formatBytes(f.size);
    dropZone.classList.add('has-file');
}

function clearFile() {
    selectedFile = null; fileInput.value = '';
    document.getElementById('drop-icon').style.display = '';
    document.querySelector('.drop-content').style.display = '';
    document.getElementById('drop-file-info').style.display = 'none';
    dropZone.classList.remove('has-file');
}

const formatBytes = b => b < 1024 ? b + ' B' : b < 1048576 ? (b / 1024).toFixed(1) + ' KB' : (b / 1048576).toFixed(1) + ' MB';

// ── Ingest PDF ────────────────────────────────────────────────────
async function ingestPDF() {
    if (!selectedFile) { showToast('Please select a PDF file first.'); return; }

    const btn = document.getElementById('ingest-btn');
    const card = document.getElementById('progress-card');

    btn.disabled = true;
    card.style.display = '';
    document.getElementById('success-card').style.display = 'none';
    setStatus('Ingesting…', 'loading');

    // Build path from file name (user's Downloads folder is common location)
    const sourceInput = document.getElementById('source-id').value.trim();
    const pdfPath = 'C:\\Users\\prith\\Downloads\\' + selectedFile.name;
    const sourceId = sourceInput || pdfPath;

    // Animate the three steps while the real API call runs
    setStep('step-load', 'active');
    updateBar(15, 'Loading & chunking PDF…');

    let result;
    try {
        setStep('step-load', 'done');
        setStep('step-embed', 'active');
        updateBar(45, 'Generating embeddings…');

        result = await post('/ingest', { pdf_path: pdfPath, source_id: sourceId });

        setStep('step-embed', 'done');
        setStep('step-upsert', 'active');
        updateBar(80, 'Storing in Qdrant…');
        await sleep(400);
        setStep('step-upsert', 'done');
        updateBar(100, 'Done!');
        await sleep(300);
    } catch (err) {
        showToast('Ingest failed: ' + err.message);
        btn.disabled = false;
        setStatus('Error', 'error');
        return;
    }

    card.style.display = 'none';
    const ok = document.getElementById('success-card');
    ok.style.display = 'flex';
    document.getElementById('success-detail').textContent =
        `${result.ingested} chunk${result.ingested !== 1 ? 's' : ''} indexed ∙ source: ${result.source_id}`;

    ingestHistory.push({ name: selectedFile.name, chunks: result.ingested, ts: new Date() });
    renderHistory();
    document.getElementById('history-section').style.display = '';

    btn.disabled = false;
    setStatus('Ready');
}

function setStep(id, state) {
    const el = document.getElementById(id);
    el.className = 'step-item ' + state;
}
function updateBar(pct, title) {
    document.getElementById('progress-bar').style.width = pct + '%';
    document.getElementById('progress-pct').textContent = pct + '%';
    document.getElementById('progress-title').textContent = title;
}

function renderHistory() {
    document.getElementById('history-list').innerHTML = ingestHistory.slice().reverse().map(item => `
    <div class="history-item">
      <span class="history-item-dot"></span>
      <span class="history-name">${esc(item.name)}</span>
      <span class="history-meta">${item.chunks} chunks ∙ ${item.ts.toLocaleTimeString()}</span>
    </div>`).join('');
}

// ── Query ─────────────────────────────────────────────────────────
function setQuery(q) {
    const ta = document.getElementById('query-input');
    ta.value = q; autoResize(ta); ta.focus();
    document.getElementById('suggestions').style.display = 'none';
}

function handleQueryKey(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitQuery(); } }

function autoResize(el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 200) + 'px'; }

async function submitQuery() {
    if (isQuerying) return;
    const question = document.getElementById('query-input').value.trim();
    if (!question) return;
    const topK = parseInt(document.getElementById('top-k').value, 10) || 5;

    document.getElementById('suggestions').style.display = 'none';
    appendMessage('user', question);
    document.getElementById('query-input').value = '';
    document.getElementById('query-input').style.height = 'auto';

    isQuerying = true;
    document.getElementById('query-send-btn').disabled = true;
    document.getElementById('thinking-card').style.display = 'flex';
    setStatus('Querying…', 'loading');

    try {
        const result = await post('/query', { question, top_k: topK });
        document.getElementById('thinking-card').style.display = 'none';
        appendAIMessage(result.answer, result.sources, result.num_contexts);
    } catch (err) {
        document.getElementById('thinking-card').style.display = 'none';
        appendAIMessage('⚠ Error: ' + err.message + '\n\nMake sure the FastAPI server is running on port 8000.', [], 0);
    }

    isQuerying = false;
    document.getElementById('query-send-btn').disabled = false;
    setStatus('Ready');
}

// ── Message rendering ─────────────────────────────────────────────
function appendMessage(role, text) {
    const area = document.getElementById('chat-area');
    const div = document.createElement('div');
    div.className = `msg msg-${role}`;
    div.innerHTML = `<div class="msg-bubble">${esc(text)}</div>`;
    area.appendChild(div);
    area.scrollTop = area.scrollHeight;
}

function appendAIMessage(answer, sources, numCtx) {
    const area = document.getElementById('chat-area');
    const div = document.createElement('div');
    div.className = 'msg msg-ai';
    const srcHtml = sources.length
        ? `<div class="msg-sources"><div class="sources-label">Sources</div>${sources.map(s => `<span class="source-tag">📄 ${esc(truncate(s, 40))}</span>`).join('')}</div>`
        : '';
    const metaHtml = numCtx ? `<div class="meta-row">${numCtx} context chunk${numCtx !== 1 ? 's' : ''} retrieved</div>` : '';
    div.innerHTML = `
    <div class="msg-bubble">
      <div class="msg-ai-header"><div class="ai-avatar">AI</div><span class="ai-label">DocMind AI</span></div>
      <div class="msg-answer">${esc(answer).replace(/\n/g, '<br/>')}</div>
      ${srcHtml}${metaHtml}
    </div>`;
    area.appendChild(div);
    area.scrollTop = area.scrollHeight;
}

// ── API helper ────────────────────────────────────────────────────
async function post(path, body) {
    const res = await fetch(API + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    return res.json();
}

// ── Toast ─────────────────────────────────────────────────────────
function showToast(msg) {
    const t = document.createElement('div');
    t.className = 'toast'; t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 4000);
}

// ── Utils ─────────────────────────────────────────────────────────
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const truncate = (s, n) => s.length > n ? s.slice(0, n) + '…' : s;
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ── Init ──────────────────────────────────────────────────────────
(async function init() {
    setStatus('Checking backend…', 'loading');
    try {
        await fetch(API + '/api/inngest');
        setStatus('Ready');
    } catch {
        setStatus('Backend offline', 'error');
    }
    // Show Inngest link in footer
    document.getElementById('backend-url-display').innerHTML =
        `Backend: ${API} &nbsp;|&nbsp; <a href="${INNGEST}" target="_blank" style="color:var(--accent-3);text-decoration:none">📊 Inngest Dashboard ↗</a>`;
})();
