/* ═══════════════════════════════════════════
   Medical Report Analyzer — Frontend Logic
   ═══════════════════════════════════════════ */

const API = "";  // same origin

// ─── Helpers ───
const $ = (id) => document.getElementById(id);

function showSpinner(id)  { $(id).classList.remove("hidden"); }
function hideSpinner(id)  { $(id).classList.add("hidden"); }

async function api(endpoint, body) {
  const res = await fetch(`${API}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Error ${res.status}`);
  }
  return res.json();
}

// ─── Upload ───
$("btn-upload").addEventListener("click", async () => {
  const pdfPath = $("pdf-path").value.trim();
  if (!pdfPath) return alert("Please enter a PDF path.");

  const resultBox = $("upload-result");
  resultBox.classList.add("hidden");
  showSpinner("upload-spinner");
  $("btn-upload").querySelector(".btn-text").textContent = "Indexing…";

  try {
    const data = await api("/load_file_path", {
      pdf_path: pdfPath,
      source_id: $("source-id").value.trim() || "",
    });
    resultBox.classList.remove("hidden", "error");
    resultBox.classList.add("success");
    resultBox.textContent = `✅ Indexed ${data.loaded_chunks} chunk(s)\nSource ID: ${data.source_id}`;

    // Auto-fill the analyze source field
    $("analyze-source").value = data.source_id;
  } catch (e) {
    resultBox.classList.remove("hidden", "success");
    resultBox.classList.add("error");
    resultBox.textContent = `❌ ${e.message}`;
  } finally {
    hideSpinner("upload-spinner");
    $("btn-upload").querySelector(".btn-text").textContent = "Index Report";
  }
});

// ─── Query Chat ───
function addChatMsg(text, type) {
  $("chat-empty")?.remove();
  const div = document.createElement("div");
  div.className = `chat-msg ${type}`;
  if (type === "bot") {
    // Split answer and disclaimer
    const parts = text.split("⚠️");
    div.innerHTML = parts[0].trim();
    if (parts[1]) {
      const disc = document.createElement("span");
      disc.className = "disclaimer";
      disc.textContent = "⚠️" + parts[1];
      div.appendChild(disc);
    }
  } else {
    div.textContent = text;
  }
  $("chat-messages").appendChild(div);
  $("chat-container").scrollTop = $("chat-container").scrollHeight;
}

async function sendQuery(question) {
  if (!question) return;
  addChatMsg(question, "user");
  $("query-input").value = "";
  showSpinner("query-spinner");
  $("btn-query").querySelector(".btn-text").textContent = "…";

  try {
    const data = await api("/query", { question, top_k: 5 });
    addChatMsg(data.answer, "bot");
  } catch (e) {
    addChatMsg(`Error: ${e.message}`, "bot");
  } finally {
    hideSpinner("query-spinner");
    $("btn-query").querySelector(".btn-text").textContent = "Ask";
  }
}

$("btn-query").addEventListener("click", () => sendQuery($("query-input").value.trim()));
$("query-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendQuery($("query-input").value.trim());
});

// Suggestion chips
document.querySelectorAll(".suggestion").forEach((btn) => {
  btn.addEventListener("click", () => sendQuery(btn.dataset.q));
});

// ─── Analyze ───
function renderAnalysis(raw) {
  let data;
  try {
    data = typeof raw === "string" ? JSON.parse(raw) : raw;
  } catch {
    return `<pre>${raw}</pre>`;
  }

  let html = "";

  // Summary
  if (data.summary) {
    html += `<div class="analysis-summary">📋 <strong>Summary:</strong> ${data.summary}</div>`;
  }
  if (typeof data.abnormal_count === "number") {
    html += `<p style="margin-top:0.5rem;color:var(--text-dim);font-size:0.85rem;">
      Abnormal results: <strong style="color:${data.abnormal_count > 0 ? 'var(--red)' : 'var(--green)'}">${data.abnormal_count}</strong>
    </p>`;
  }

  // Test table
  if (data.tests && data.tests.length > 0) {
    html += `<table class="analysis-table">
      <thead><tr><th>Test</th><th>Value</th><th>Range</th><th>Status</th></tr></thead><tbody>`;
    data.tests.forEach((t) => {
      const cls = (t.status || "unknown").toLowerCase();
      html += `<tr>
        <td><strong>${t.test_name || "—"}</strong><br><span style="font-size:0.78rem;color:var(--text-dim)">${t.plain_english || ""}</span></td>
        <td>${t.value || "—"}</td>
        <td>${t.reference_range || "—"}</td>
        <td><span class="status-badge ${cls}">${t.status || "?"}</span></td>
      </tr>`;
    });
    html += `</tbody></table>`;
  } else {
    html += `<p style="margin-top:0.5rem;color:var(--text-dim);">No test results found.</p>`;
  }

  return html;
}

$("btn-analyze").addEventListener("click", async () => {
  const sourceId = $("analyze-source").value.trim();
  if (!sourceId) return alert("Please enter a Source ID.");

  const resultBox = $("analyze-result");
  resultBox.classList.add("hidden");
  showSpinner("analyze-spinner");
  $("btn-analyze").querySelector(".btn-text").textContent = "Analyzing…";

  try {
    const data = await api("/analyze", { source_id: sourceId, top_k: 10 });
    resultBox.classList.remove("hidden", "error");
    resultBox.classList.add("success");
    resultBox.innerHTML = renderAnalysis(data.analysis);
  } catch (e) {
    resultBox.classList.remove("hidden", "success");
    resultBox.classList.add("error");
    resultBox.textContent = `❌ ${e.message}`;
  } finally {
    hideSpinner("analyze-spinner");
    $("btn-analyze").querySelector(".btn-text").textContent = "Analyze Report";
  }
});
