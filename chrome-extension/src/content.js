// Career OS — Content Script
// Injects "Save to Career OS" button on job listing pages

(function () {
  "use strict";

  // ── Site Detectors ────────────────────────────────────────────
  const SITE_PARSERS = {
    linkedin:  isLinkedIn,
    indeed:    isIndeed,
    glassdoor: isGlassdoor,
    greenhouse: isGreenhouse,
    lever:     isLever,
    workable:  isWorkable,
  };

  function detectSite() {
    const host = window.location.hostname;
    if (host.includes("linkedin.com")) return "linkedin";
    if (host.includes("indeed.com"))   return "indeed";
    if (host.includes("glassdoor.com")) return "glassdoor";
    if (host.includes("greenhouse.io")) return "greenhouse";
    if (host.includes("lever.co"))     return "lever";
    if (host.includes("workable.com")) return "workable";
    return null;
  }

  // ── Parsers ───────────────────────────────────────────────────
  function isLinkedIn() {
    // Title — multiple selector fallbacks
    const title = (
      document.querySelector(".job-details-jobs-unified-top-card__job-title h1")?.textContent?.trim() ||
      document.querySelector(".job-details-jobs-unified-top-card__job-title")?.textContent?.trim() ||
      document.querySelector("h1.t-24")?.textContent?.trim() ||
      document.querySelector("h1[class*='title']")?.textContent?.trim()
    );

    const company = (
      document.querySelector(".job-details-jobs-unified-top-card__company-name a")?.textContent?.trim() ||
      document.querySelector(".job-details-jobs-unified-top-card__company-name")?.textContent?.trim() ||
      document.querySelector(".topcard__org-name-link")?.textContent?.trim()
    );

    const location = (
      document.querySelector(".job-details-jobs-unified-top-card__primary-description-container .tvm__text:nth-child(3)")?.textContent?.trim() ||
      document.querySelector(".job-details-jobs-unified-top-card__bullet")?.textContent?.trim() ||
      document.querySelector(".topcard__flavor--bullet")?.textContent?.trim()
    );

    // Salary — LinkedIn sometimes shows it in the job details
    const salary = (
      document.querySelector(".compensation__salary-range")?.textContent?.trim() ||
      document.querySelector("[class*='salary']")?.textContent?.trim() ||
      null
    );

    // Job type / workplace type (remote/hybrid/on-site)
    const workplace = (
      document.querySelector(".job-details-jobs-unified-top-card__workplace-type")?.textContent?.trim() ||
      null
    );
    const isRemote = workplace?.toLowerCase().includes("remote") || false;

    // Description
    const desc = (
      document.querySelector(".jobs-description__content .jobs-box__html-content")?.innerText?.trim() ||
      document.querySelector(".show-more-less-html__markup")?.innerText?.trim() ||
      document.querySelector(".jobs-description")?.innerText?.trim()
    );

    // Easy Apply detection
    const easyApply = !!document.querySelector(".jobs-apply-button--top-card, [aria-label*='Easy Apply']");

    // Job ID from URL
    const jobIdMatch = window.location.href.match(/\/jobs\/view\/(\d+)/);
    const linkedin_job_id = jobIdMatch?.[1] || null;

    const url = window.location.href.split("?")[0];
    if (!title) return null;

    return {
      title,
      company:         company || "",
      location:        location || "",
      description:     desc || "",
      salary_range:    salary || "",
      remote:          isRemote,
      workplace_type:  workplace || "",
      easy_apply:      easyApply,
      linkedin_job_id,
      source_url:      url,
      source:          "linkedin",
    };
  }

  function isIndeed() {
    const title   = document.querySelector("h1.jobsearch-JobInfoHeader-title, h1[data-testid='jobsearch-JobInfoHeader-title']")?.textContent?.trim();
    const company = document.querySelector("[data-testid='inlineHeader-companyName'], .jobsearch-CompanyInfoContainer a")?.textContent?.trim();
    const location = document.querySelector("[data-testid='job-location'], .jobsearch-JobInfoHeader-subtitle div")?.textContent?.trim();
    const desc    = document.querySelector("#jobDescriptionText, .jobsearch-jobDescriptionText")?.innerText?.trim();
    const url     = window.location.href.split("?")[0];

    if (!title) return null;
    return { title, company: company || "", location: location || "", description: desc || "", source_url: url, source: "indeed" };
  }

  function isGlassdoor() {
    const title   = document.querySelector('[data-test="job-title"], .JobDetails_jobTitle__Rw_gn')?.textContent?.trim();
    const company = document.querySelector('[data-test="employer-name"], .JobDetails_companyName__Rw_gn')?.textContent?.trim();
    const location = document.querySelector('[data-test="location"], .JobDetails_location__Rw_gn')?.textContent?.trim();
    const desc    = document.querySelector(".JobDetails_jobDescription__6VeBn, [data-test='description']")?.innerText?.trim();
    const url     = window.location.href.split("?")[0];

    if (!title) return null;
    return { title, company: company || "", location: location || "", description: desc || "", source_url: url, source: "glassdoor" };
  }

  function isGreenhouse() {
    const title   = document.querySelector("h1.app-title")?.textContent?.trim();
    const company = document.querySelector(".company-name")?.textContent?.trim() || document.title.split(" at ")[1]?.trim();
    const location = document.querySelector(".location")?.textContent?.trim();
    const desc    = document.querySelector("#content")?.innerText?.trim();
    const url     = window.location.href;

    if (!title) return null;
    return { title, company: company || "", location: location || "", description: desc || "", source_url: url, source: "greenhouse" };
  }

  function isLever() {
    const title   = document.querySelector(".posting-headline h2")?.textContent?.trim();
    const company = document.title.split(" at ")[1]?.trim() || "";
    const location = document.querySelector(".posting-categories .location")?.textContent?.trim();
    const desc    = document.querySelector(".posting-description")?.innerText?.trim();
    const url     = window.location.href;

    if (!title) return null;
    return { title, company, location: location || "", description: desc || "", source_url: url, source: "lever" };
  }

  function isWorkable() {
    const title   = document.querySelector("h1.job-title")?.textContent?.trim();
    const company = document.querySelector(".company-name")?.textContent?.trim();
    const location = document.querySelector(".job-location")?.textContent?.trim();
    const desc    = document.querySelector(".job-description")?.innerText?.trim();
    const url     = window.location.href;

    if (!title) return null;
    return { title, company: company || "", location: location || "", description: desc || "", source_url: url, source: "workable" };
  }

  // ── Button Injection ──────────────────────────────────────────
  const BTN_ID = "career-os-save-btn";

  function injectButton(jobData) {
    if (document.getElementById(BTN_ID)) return;

    const btn = document.createElement("div");
    btn.id = BTN_ID;
    btn.innerHTML = `
      <button class="cos-btn" title="Save to Career OS">
        <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
          <path d="M5 4a2 2 0 012-2h6a2 2 0 012 2v14l-5-2.5L5 18V4z"/>
        </svg>
        <span class="cos-btn-text">Save to Career OS</span>
      </button>
    `;

    btn.querySelector(".cos-btn").addEventListener("click", () => handleSave(jobData, btn));

    // Try to inject near apply button
    const anchor =
      document.querySelector(".jobs-apply-button--top-card, .jobs-s-apply button") ||
      document.querySelector("[data-testid='indeedApplyButton'], .icl-Button--primary") ||
      document.querySelector(".apply-button-wPanel button") ||
      document.querySelector("header, .jobHeader, h1")?.parentNode;

    if (anchor) {
      anchor.insertAdjacentElement("afterend", btn);
    } else {
      // Fallback: floating button
      btn.style.cssText = "position:fixed;bottom:24px;right:24px;z-index:9999;";
      document.body.appendChild(btn);
    }
  }

  async function handleSave(jobData, container) {
    const btn = container.querySelector(".cos-btn");
    const text = container.querySelector(".cos-btn-text");

    btn.classList.add("cos-btn--loading");
    text.textContent = "Saving…";

    const result = await chrome.runtime.sendMessage({
      type: "SAVE_JOB",
      payload: jobData,
    });

    if (result.error === "not_authenticated" || result.error === "token_expired") {
      btn.classList.remove("cos-btn--loading");
      btn.classList.add("cos-btn--error");
      text.textContent = "Login required";
      setTimeout(() => {
        chrome.runtime.sendMessage({ type: "OPEN_POPUP" });
        text.textContent = "Save to Career OS";
        btn.classList.remove("cos-btn--error");
      }, 2000);
      return;
    }

    if (result.ok) {
      btn.classList.remove("cos-btn--loading");
      btn.classList.add("cos-btn--saved");
      text.textContent = "Saved! ✓";
    } else {
      btn.classList.remove("cos-btn--loading");
      btn.classList.add("cos-btn--error");
      text.textContent = "Error — retry?";
      setTimeout(() => {
        text.textContent = "Save to Career OS";
        btn.classList.remove("cos-btn--error");
      }, 3000);
    }
  }

  // ── Init ─────────────────────────────────────────────────────
  function tryInit() {
    const site = detectSite();
    if (!site) return;

    const parser = SITE_PARSERS[site];
    if (!parser) return;

    const jobData = parser();
    if (!jobData) return;

    injectButton(jobData);
  }

  // Run on page load
  tryInit();

  // LinkedIn uses SPA navigation — observe DOM changes
  const observer = new MutationObserver(() => {
    if (!document.getElementById(BTN_ID)) tryInit();
  });
  observer.observe(document.body, { childList: true, subtree: true });

})();
