// ── DevMind Frontend App ─────────────────────────────────────────
const API = "";  // same origin

// ── Check Health & Mode ──────────────────────────────────────────
async function checkHealth() {
  try {
    const res = await fetch(`${API}/health`);
    if (res.ok) {
      const data = await res.json();
      const mode = (data.mode || "demo").toLowerCase();
      const badge = document.getElementById("mode-badge");
      if (badge) {
        badge.textContent = `Mode: ${mode.toUpperCase()}`;
        badge.className = `badge badge-${mode === "real" ? "real" : "demo"}`;
      }
    }
  } catch (err) {
    console.error("Health check error:", err);
  }
}

// ── Update Memory Count (Stored Memories) ───────────────────────
async function updateMemoryCount() {
  const countBadge = document.getElementById("memory-count-badge");
  if (!countBadge) return;
  try {
    const res = await fetch(`${API}/api/memory-count`);
    if (res.ok) {
      const data = await res.json();
      if (data.count !== null && data.count !== undefined) {
        countBadge.textContent = `Memories stored: ${data.count}`;
        countBadge.style.display = "inline-block";
      } else {
        countBadge.style.display = "none";
      }
    } else {
      countBadge.style.display = "none";
    }
  } catch (err) {
    console.error("Memory count check error:", err);
    countBadge.style.display = "none";
  }
}

// Initial page load checks
async function initApp() {
  await Promise.allSettled([checkHealth(), updateMemoryCount()]);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initApp);
} else {
  initApp();
}

async function parseErrorMessage(res) {
  try {
    const data = await res.json();
    if (data.detail) return data.detail;
    if (data.message) return data.message;
    return `Server error: ${res.status}`;
  } catch (_) {
    return `Server error: ${res.status}`;
  }
}

// ── Tab Navigation ───────────────────────────────────────────────
function openTab(name) {
  document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".tab").forEach(el => el.classList.remove("active"));
  document.getElementById(`tab-${name}`)?.classList.add("active");
  document.querySelector(`[data-tab="${name}"]`)?.classList.add("active");
}

// ── Quick Demo Scenarios ─────────────────────────────────────────
const SCENARIOS = {
  db: {
    developer: "Rahul Verma",
    filePath:  "app/db/session.py",
    errorMsg:  "sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) FATAL: remaining connection slots are reserved for non-replication superuser connections",
    stackTrace:`Traceback (most recent call last):
  File "app/db/session.py", line 34, in get_db
    db = SessionLocal()
  File "site-packages/sqlalchemy/orm/session.py", line 568, in __init__
    self.bind = bind
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) FATAL:
remaining connection slots are reserved for non-replication superuser connections`
  },
  auth: {
    developer: "Priya Sharma",
    filePath:  "src/middleware/auth.js",
    errorMsg:  "TypeError: Cannot read properties of null (reading 'userId')",
    stackTrace:`TypeError: Cannot read properties of null (reading 'userId')
    at verifyToken (src/middleware/auth.js:47:22)
    at Layer.handle [as handle_request] (express/lib/router/layer.js:95:5)
    at next (express/lib/router/route.js:137:13)
    at Route.dispatch (express/lib/router/route.js:112:3)`
  },
  race: {
    developer: "Ananya Krishnan",
    filePath:  "services/payment/transaction.py",
    errorMsg:  "AssertionError: Expected user balance to be 500, got 350",
    stackTrace:`Traceback (most recent call last):
  File "tests/test_payment.py", line 88, in test_concurrent_payments
    assert user.balance == 500, f"Expected 500, got {user.balance}"
AssertionError: Expected user balance to be 500, got 350
(Occurs intermittently under concurrent load — 1 in every ~10 runs)`
  },
  async: {
    developer: "Karan Mehta",
    filePath:  "api/routes/reports.py",
    errorMsg:  "asyncio.exceptions.TimeoutError — /api/report endpoint hangs indefinitely under load",
    stackTrace:`File "api/routes/reports.py", line 62, in generate_report
    df = pd.read_csv(filepath)  # 500MB file
  File "pandas/io/parsers/readers.py", line 912, in read_csv
    return _read(filepath_or_buffer, kwds)
(Event loop blocked — all requests queue behind this)`
  },
  new: {
    developer: "Demo Dev",
    filePath:  "services/notifications/email_sender.py",
    errorMsg:  "smtplib.SMTPAuthenticationError: (535, b'5.7.8 Username and Password not accepted')",
    stackTrace:`Traceback (most recent call last):
  File "services/notifications/email_sender.py", line 28, in send_email
    server.login(SMTP_USER, SMTP_PASS)
smtplib.SMTPAuthenticationError: (535, b'5.7.8 Username and Password not accepted. 
Learn more at https://support.google.com/mail/?p=BadCredentials')`
  }
};

function loadScenario(key) {
  const s = SCENARIOS[key];
  if (!s) return;
  document.getElementById("developer").value    = s.developer;
  document.getElementById("file-path").value    = s.filePath;
  document.getElementById("error-message").value = s.errorMsg;
  document.getElementById("stack-trace").value  = s.stackTrace;
}

// ── Analyze Bug (With Memory vs Without Memory) ──────────────────
async function analyzeError() {
  const developer   = document.getElementById("developer").value.trim()     || "anonymous";
  const filePath    = document.getElementById("file-path").value.trim()     || "unknown";
  const errorMsg    = document.getElementById("error-message").value.trim();
  const stackTrace  = document.getElementById("stack-trace").value.trim();

  if (!errorMsg) { showToast("⚠️ Please enter an error message.", "error"); return; }

  const resultArea = document.getElementById("result-area");
  resultArea.className = "";
  // Render dual-card comparison layout with immediate loading states
  resultArea.innerHTML = `
    <div class="comparison-grid">
      <!-- Without Memory Card -->
      <div class="compare-card" id="card-without-memory">
        <div class="compare-header">
          <div class="compare-title">
            <span class="compare-icon">🔇</span>
            <h3>Without memory</h3>
          </div>
          <span class="badge badge-off">Standard AI</span>
        </div>
        <div class="compare-body" id="body-without-memory">
          <div class="loading">
            <div class="spinner"></div>
            <span>Analyzing without memory…</span>
          </div>
        </div>
      </div>

      <!-- With Memory Card -->
      <div class="compare-card compare-card-highlight" id="card-with-memory">
        <div class="compare-header">
          <div class="compare-title">
            <span class="compare-icon">🧠</span>
            <h3>With memory</h3>
          </div>
          <span class="badge badge-on">Hindsight Memory</span>
        </div>
        <div class="compare-body" id="body-with-memory">
          <div class="loading">
            <div class="spinner"></div>
            <span>Searching memory + analyzing…</span>
          </div>
        </div>
      </div>
    </div>
  `;

  const payloadBase = {
    developer,
    file_path: filePath,
    error_message: errorMsg,
    stack_trace: stackTrace,
  };

  // 1. Fetch Without Memory (use_memory: false)
  const reqWithout = fetch(`${API}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payloadBase, use_memory: false }),
  });

  // 2. Fetch With Memory (use_memory: true)
  const reqWith = fetch(`${API}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payloadBase, use_memory: true }),
  });

  // Handle Card 1: Without Memory
  reqWithout.then(async (res) => {
    const bodyEl = document.getElementById("body-without-memory");
    if (!bodyEl) return;
    if (!res.ok) {
      const errDetail = await parseErrorMessage(res);
      bodyEl.innerHTML = `<div class="memory-status memory-miss">❌ Error: ${escapeHtml(errDetail)}</div>`;
      return;
    }
    const data = await res.json();
    bodyEl.innerHTML = `
      <div class="memory-status memory-miss">
        <div class="memory-dot"></div>
        🔇 Standard AI (No team memory used)
      </div>
      <div class="analysis-content">${escapeHtml(data.analysis)}</div>
      <div class="meta-row">
        <span class="meta-chip">⚡ 0 memories accessed</span>
        <span class="meta-chip">🕒 ${new Date().toLocaleTimeString()}</span>
      </div>
    `;
  }).catch((err) => {
    const bodyEl = document.getElementById("body-without-memory");
    if (bodyEl) {
      bodyEl.innerHTML = `<div class="memory-status memory-miss">❌ Error: ${escapeHtml(err.message)}</div>`;
    }
  });

  // Handle Card 2: With Memory
  reqWith.then(async (res) => {
    const bodyEl = document.getElementById("body-with-memory");
    if (!bodyEl) return;
    if (!res.ok) {
      const errDetail = await parseErrorMessage(res);
      bodyEl.innerHTML = `<div class="memory-status memory-miss">❌ Error: ${escapeHtml(errDetail)}</div>`;
      return;
    }
    const data = await res.json();

    // Number of recalled snippets (up to 5)
    const snippetCount = (data.memories && data.memories.length !== undefined)
      ? data.memories.length
      : (data.memories_found || 0);

    const hasMemoryHit = Boolean(data.memory_used && snippetCount > 0);

    // Update global memory badge
    const badge = document.getElementById("memory-badge");
    if (badge) {
      if (hasMemoryHit) {
        badge.textContent = `Memory: ON (${snippetCount} closest)`;
        badge.className = "badge badge-on";
      } else {
        badge.textContent = "Memory: No match found";
        badge.className = "badge badge-off";
      }
    }

    // Memories used collapsible section
    let memoriesCollapsibleHtml = "";
    if (data.memories && data.memories.length > 0) {
      const snippetsHtml = data.memories.map((m, i) => `
        <div class="memory-snippet">
          <div class="snippet-header">#${i + 1} Closest Memory Snippet</div>
          <div class="snippet-content">${escapeHtml(m)}</div>
        </div>
      `).join("");
      memoriesCollapsibleHtml = `
        <details class="memories-collapsible" open>
          <summary>📚 Memories used (${snippetCount})</summary>
          <div class="memories-list">
            ${snippetsHtml}
          </div>
        </details>
      `;
    } else {
      memoriesCollapsibleHtml = `
        <details class="memories-collapsible">
          <summary>📚 Memories used (0)</summary>
          <p class="hint" style="margin-top: 8px;">No previous team memories matched this error.</p>
        </details>
      `;
    }

    bodyEl.innerHTML = `
      <div class="memory-status ${hasMemoryHit ? 'memory-hit' : 'memory-miss'}">
        <div class="memory-dot"></div>
        ${hasMemoryHit
          ? `🧠 Hindsight Memory: <strong>${snippetCount} closest memories</strong>${data.has_reflection ? ' · synthesized' : ''}`
          : '🔇 No previous record found in team memory — first time seeing this bug'}
      </div>
      <div class="analysis-content">${escapeHtml(data.analysis)}</div>
      ${memoriesCollapsibleHtml}
      <div class="meta-row">
        <span class="meta-chip">👤 ${escapeHtml(developer)}</span>
        <span class="meta-chip">📁 ${escapeHtml(filePath)}</span>
        <span class="meta-chip">🕒 ${new Date().toLocaleTimeString()}</span>
      </div>
    `;
  }).catch((err) => {
    const bodyEl = document.getElementById("body-with-memory");
    if (bodyEl) {
      bodyEl.innerHTML = `<div class="memory-status memory-miss">❌ Error: ${escapeHtml(err.message)}</div>`;
    }
  });
}

// ── Log Fix ──────────────────────────────────────────────────────
async function logFix() {
  const payload = {
    developer:     document.getElementById("lf-developer").value.trim()    || "anonymous",
    error_type:    document.getElementById("lf-error-type").value.trim()   || "UnknownError",
    error_message: document.getElementById("lf-error-message").value.trim(),
    file_path:     document.getElementById("lf-file-path").value.trim()    || "unknown",
    root_cause:    document.getElementById("lf-root-cause").value.trim(),
    fix_applied:   document.getElementById("lf-fix-applied").value.trim(),
    tags: document.getElementById("lf-tags").value.split(",").map(t => t.trim()).filter(Boolean),
  };

  if (!payload.error_message || !payload.root_cause || !payload.fix_applied) {
    showToast("⚠️ Please fill in Error Message, Root Cause and Fix Applied.", "error");
    return;
  }

  const resultEl = document.getElementById("log-fix-result");
  resultEl.className = "log-result";
  resultEl.textContent = "Retaining fix into Hindsight memory…";
  resultEl.classList.remove("hidden");

  try {
    const res = await fetch(`${API}/api/log-fix`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const errDetail = await parseErrorMessage(res);
      throw new Error(errDetail);
    }
    const data = await res.json();
    resultEl.className = "log-result success";
    // Requirement 6: "Saved. Run Analyze again to see this fix recalled."
    resultEl.textContent = "✅ Saved. Run Analyze again to see this fix recalled.";
    showToast("✅ Saved. Run Analyze again to see this fix recalled.", "success");
    // Requirement 5: Refresh memory count after Log a Fix
    await updateMemoryCount();
  } catch (err) {
    resultEl.className = "log-result error";
    resultEl.textContent = "❌ " + err.message;
    showToast("❌ " + err.message, "error");
  }
}

// ── Search Memory ────────────────────────────────────────────────
async function searchMemory() {
  const query = document.getElementById("search-query").value.trim();
  if (!query) { showToast("⚠️ Enter a search query.", "error"); return; }

  const area = document.getElementById("search-results");
  area.innerHTML = `<div class="loading"><div class="spinner"></div><span>Searching memory…</span></div>`;

  try {
    const res = await fetch(`${API}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) {
      const errDetail = await parseErrorMessage(res);
      throw new Error(errDetail);
    }
    const data = await res.json();

    if (!data.results?.length) {
      area.innerHTML = `<p class="no-results">No matching memories found for "<strong>${escapeHtml(query)}</strong>".</p>`;
      return;
    }

    area.innerHTML = `<p class="hint">Found <strong>${data.count}</strong> memory chunks matching "<em>${escapeHtml(query)}</em>"</p>` +
      data.results.map((r, i) => `
        <div class="memory-chunk"><strong>#${i+1}</strong>\n${escapeHtml(r.text)}</div>
      `).join("");
  } catch (err) {
    area.innerHTML = `<p class="no-results">❌ ${escapeHtml(err.message)}</p>`;
    showToast("❌ " + err.message, "error");
  }
}

// ── Seed Demo Data ───────────────────────────────────────────────
async function seedMemory() {
  showToast("🌱 Seeding past debugging sessions into Hindsight memory…");
  try {
    const res = await fetch(`${API}/api/seed`, { method: "POST" });
    if (!res.ok) {
      const errDetail = await parseErrorMessage(res);
      throw new Error(errDetail);
    }
    const data = await res.json();
    showToast(`✅ ${data.message}`, "success");
    // Requirement 5: Refresh memory count after Seed
    await updateMemoryCount();
  } catch (err) {
    showToast("❌ Seed failed: " + err.message, "error");
  }
}

// ── Utilities ────────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

let toastTimer;
function showToast(msg, type = "") {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.className = `toast ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.add("hidden"), 4000);
}
