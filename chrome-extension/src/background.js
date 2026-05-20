// Career OS — Background Service Worker (Manifest V3)

const API_BASE = "https://career-os-api.onrender.com/api";

// ── Auth helpers ────────────────────────────────────────────────
async function getToken() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["career_os_token"], (r) => resolve(r.career_os_token || null));
  });
}

async function setToken(token) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ career_os_token: token }, resolve);
  });
}

// ── Save job to Career OS ────────────────────────────────────────
async function saveJobToCareerOS(jobData) {
  const token = await getToken();
  if (!token) {
    return { ok: false, error: "not_authenticated" };
  }

  try {
    const res = await fetch(`${API_BASE}/extension/save-job`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify(jobData),
    });

    if (res.status === 401) {
      await setToken(null);
      return { ok: false, error: "token_expired" };
    }

    const data = await res.json();
    return { ok: res.ok, data, status: res.status };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

// ── Message handler ──────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "SAVE_JOB") {
    saveJobToCareerOS(msg.payload)
      .then(sendResponse)
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true; // async response
  }

  if (msg.type === "GET_TOKEN") {
    getToken().then((token) => sendResponse({ token }));
    return true;
  }

  if (msg.type === "SET_TOKEN") {
    setToken(msg.token).then(() => sendResponse({ ok: true }));
    return true;
  }

  if (msg.type === "CLEAR_TOKEN") {
    setToken(null).then(() => sendResponse({ ok: true }));
    return true;
  }

  if (msg.type === "CHECK_AUTH") {
    getToken().then((token) => {
      if (!token) {
        sendResponse({ authenticated: false });
        return;
      }
      // Verify token is still valid
      fetch(`${API_BASE}/me/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => sendResponse({ authenticated: r.ok }))
        .catch(() => sendResponse({ authenticated: false }));
    });
    return true;
  }
});

// ── Extension installed/updated ─────────────────────────────────
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    chrome.tabs.create({ url: "popup.html?onboarding=1" });
  }
});
