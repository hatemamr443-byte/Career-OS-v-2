// Career OS Extension — Popup Script
const API_BASE = "https://career-os-api.onrender.com/api";

const body        = document.getElementById("main-body");
const statusBadge = document.getElementById("status-badge");
const logoutBtn   = document.getElementById("logout-btn");

// ── Helpers ──────────────────────────────────────────────────────
async function sendMsg(type, extra = {}) {
  return chrome.runtime.sendMessage({ type, ...extra });
}

async function apiGet(path, token) {
  const r = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function apiPost(path, body, token) {
  const r = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });
  return { ok: r.ok, data: await r.json(), status: r.status };
}

// ── Get current tab job data ──────────────────────────────────────
async function getCurrentTabJob() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return null;
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const btn = document.getElementById("career-os-save-btn");
        if (!btn) return null;
        // Read the job data cached on the button element
        return btn._jobData || null;
      },
    });
    return results?.[0]?.result || null;
  } catch {
    return null;
  }
}

// ── Render Views ─────────────────────────────────────────────────
function renderAuthView() {
  statusBadge.textContent = "Not logged in";
  statusBadge.className = "status-badge disconnected";
  logoutBtn.style.display = "none";

  body.innerHTML = `
    <div class="auth-view">
      <div class="auth-title">Welcome to Career OS</div>
      <div class="auth-sub">Log in to save jobs, track applications, and get AI match scores.</div>

      <label class="input-label">Your Career OS API token</label>
      <input id="token-input" class="input-field" type="password" placeholder="Paste your token here…" />
      <button id="login-btn" class="btn-primary">Connect</button>
      <div id="auth-msg" style="margin-top:8px"></div>

      <p style="margin-top:16px; font-size:11px; color:#52525b;">
        Get your token from
        <a href="https://career-os-web.onrender.com/profile" target="_blank" style="color:#71717a">Career OS Profile</a>
      </p>
    </div>
  `;

  document.getElementById("login-btn").addEventListener("click", async () => {
    const token = document.getElementById("token-input").value.trim();
    if (!token) return;
    const msg = document.getElementById("auth-msg");
    msg.textContent = "Verifying…";
    msg.className = "";

    try {
      const data = await apiGet("/me/stats", token);
      await sendMsg("SET_TOKEN", { token });
      msg.textContent = "Connected!";
      msg.className = "success-msg";
      setTimeout(init, 800);
    } catch {
      msg.textContent = "Invalid token. Check your Career OS profile.";
      msg.className = "error-msg";
    }
  });
}

// ── HTML escape helper ───────────────────────────────────────────
function escHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

async function renderDashboard(token) {
  statusBadge.textContent = "Connected";
  statusBadge.className   = "status-badge connected";
  logoutBtn.style.display = "block";

  body.innerHTML = `<div style="color:#52525b;font-size:12px;text-align:center;padding:20px">Loading…</div>`;

  const DASHBOARD = "https://career-os-web.onrender.com";

  try {
    const [stats, currentJob] = await Promise.all([
      apiGet("/me/stats", token),
      getCurrentTabJob(),
    ]);

    const level  = stats.level  || 1;
    const xp     = stats.xp    || 0;
    const streak = stats.streak || 0;
    const apps   = stats.total_applications || 0;

    body.innerHTML = `
      <!-- Stats row -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">Level</div>
          <div class="stat-value" style="color:#a78bfa">${level}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">XP</div>
          <div class="stat-value" style="color:#fbbf24">${xp.toLocaleString()}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Streak</div>
          <div class="stat-value" style="color:#fb923c">${streak}d 🔥</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Apps</div>
          <div class="stat-value" style="color:#34d399">${apps}</div>
        </div>
      </div>

      ${currentJob ? `
        <!-- Job detected -->
        <div class="section-title">Job Detected</div>
        <div class="job-preview" id="job-preview-card">
          <div class="job-preview-title">${escHtml(currentJob.title || "Unknown role")}</div>
          <div class="job-preview-meta">
            ${escHtml(currentJob.company || "")} • ${escHtml(currentJob.location || "")}
          </div>
          <div style="display:flex;align-items:center;justify-content:space-between;margin-top:4px">
            <div class="job-preview-meta" style="font-size:10px;color:#52525b">
              ${escHtml(currentJob.source || "web")}
            </div>
            <div id="quick-score-badge" style="font-size:11px;color:#52525b;font-family:monospace">
              Scoring…
            </div>
          </div>
        </div>

        <!-- Save button -->
        <button id="save-job-btn" class="save-btn">
          <svg width="13" height="13" viewBox="0 0 20 20" fill="currentColor">
            <path d="M5 4a2 2 0 012-2h6a2 2 0 012 2v14l-5-2.5L5 18V4z"/>
          </svg>
          Save to Career OS
        </button>
        <div id="save-msg" style="margin-top:4px;font-size:11px"></div>

        <!-- Quick actions -->
        <div class="section-title" style="margin-top:12px">AI Tools</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-top:4px">
          <button class="quick-action-btn" id="tailor-cv-btn">✏️ Tailor CV</button>
          <button class="quick-action-btn" id="cover-letter-btn">📄 Cover Letter</button>
          <button class="quick-action-btn" id="interview-btn">🎤 Interview Prep</button>
          <button class="quick-action-btn" id="salary-btn">💰 Salary Check</button>
        </div>
      ` : `
        <!-- No job -->
        <div class="section-title">Save a Job</div>
        <div class="job-preview" style="text-align:center;padding:16px 12px;opacity:0.6">
          <div style="font-size:22px;margin-bottom:6px">🔍</div>
          <div style="font-size:11px;color:#71717a;line-height:1.5">
            Navigate to a job on LinkedIn, Indeed, Glassdoor, or any ATS
          </div>
        </div>

        <!-- Quick nav to tools -->
        <div class="section-title" style="margin-top:12px">AI Tools</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-top:4px">
          <button class="quick-action-btn" id="tailor-cv-btn">✏️ Tailor CV</button>
          <button class="quick-action-btn" id="cover-letter-btn">📄 Cover Letter</button>
          <button class="quick-action-btn" id="interview-btn">🎤 Interview Prep</button>
          <button class="quick-action-btn" id="salary-btn">💰 Salary Check</button>
        </div>
      `}

      <!-- Dashboard link -->
      <div style="margin-top:12px;text-align:center">
        <a href="${DASHBOARD}/dashboard" target="_blank"
           style="font-size:11px;color:#52525b;text-decoration:none;
                  hover:color:#a1a1aa;transition:color 0.15s">
          Open Career OS ↗
        </a>
      </div>
    `;

    // ── Job params for deep links ───────────────────────────
    const jobParams = currentJob
      ? `?job_title=${encodeURIComponent(currentJob.title || "")}&company=${encodeURIComponent(currentJob.company || "")}`
      : "";

    // ── Quick Score (non-blocking) ──────────────────────────
    if (currentJob) {
      apiPost("/cv/ats-score", {
        job_description: currentJob.description || currentJob.title || "",
      }, token).then(r => {
        const el = document.getElementById("quick-score-badge");
        if (!el) return;
        const score = r?.score ?? r?.data?.score;
        if (score !== undefined) {
          const color = score >= 70 ? "#10B981" : score >= 45 ? "#FBBF24" : "#EF4444";
          el.innerHTML = `<span style="color:${color};font-weight:700">ATS ${score}</span>`;
        } else {
          el.textContent = "";
        }
      }).catch(() => {
        const el = document.getElementById("quick-score-badge");
        if (el) el.textContent = "";
      });

      // ── Save job ──────────────────────────────────────────
      document.getElementById("save-job-btn").addEventListener("click", async () => {
        const btn = document.getElementById("save-job-btn");
        const msg = document.getElementById("save-msg");
        btn.textContent = "Saving…";
        btn.disabled = true;

        const result = await sendMsg("SAVE_JOB", { payload: currentJob });

        if (result.ok) {
          btn.className = "save-btn saved";
          btn.innerHTML = `<span>Saved ✓</span>`;
          msg.innerHTML = `<span style="color:#86efac">+10 XP · <a href="${DASHBOARD}/jobs"
            target="_blank" style="color:#86efac;text-decoration:underline">
            View in Career OS ↗</a></span>`;
        } else if (result.error === "not_authenticated" || result.error === "token_expired") {
          await sendMsg("CLEAR_TOKEN");
          renderAuthView();
        } else {
          btn.disabled = false;
          btn.textContent = "Save to Career OS";
          msg.innerHTML = `<span style="color:#f87171">Save failed — try again</span>`;
        }
      });
    }

    // ── Quick Action buttons ────────────────────────────────
    document.getElementById("tailor-cv-btn")?.addEventListener("click", () =>
      chrome.tabs.create({ url: `${DASHBOARD}/cv-tailor${jobParams}` }));

    document.getElementById("cover-letter-btn")?.addEventListener("click", () =>
      chrome.tabs.create({ url: `${DASHBOARD}/cv-tailor?tab=cover-letter&${jobParams.slice(1)}` }));

    document.getElementById("interview-btn")?.addEventListener("click", () =>
      chrome.tabs.create({ url: `${DASHBOARD}/interview-prep${jobParams}` }));

    document.getElementById("salary-btn")?.addEventListener("click", () =>
      chrome.tabs.create({ url: `${DASHBOARD}/salary${jobParams}` }));

  } catch (err) {
    console.error("Dashboard render failed:", err);
    body.innerHTML = `
      <div style="text-align:center;padding:20px;color:#f87171;font-size:12px">
        Failed to load dashboard.
        <button id="retry-btn" style="display:block;margin:8px auto 0;
          background:#18181b;border:1px solid #3f3f46;border-radius:6px;
          color:#a1a1aa;font-size:11px;padding:5px 12px;cursor:pointer">
          Retry
        </button>
      </div>`;
    document.getElementById("retry-btn")?.addEventListener("click", () => renderDashboard(token));
  }
}

// ── Init ─────────────────────────────────────────────────────────
async function init() {
  const { token } = await sendMsg("GET_TOKEN");

  if (!token) {
    renderAuthView();
    return;
  }

  // Quick auth check
  try {
    await apiGet("/me/stats", token);
    await renderDashboard(token);
  } catch {
    await sendMsg("CLEAR_TOKEN");
    renderAuthView();
  }
}

// Logout
logoutBtn.addEventListener("click", async () => {
  await sendMsg("CLEAR_TOKEN");
  renderAuthView();
});

// Start
init();

// ── Quick Action Styles already in popup.html ────────────────────
