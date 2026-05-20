import { createContext, useContext, useEffect } from "react";
import { useAuth } from "./AuthContext";

const PostHogContext = createContext(null);

// Load PostHog lazily — only if REACT_APP_POSTHOG_KEY is set
function loadPostHog(key, host) {
    if (!key || window.__posthogLoaded) return;
    window.__posthogLoaded = true;

    const script = document.createElement("script");
    script.innerHTML = `
        !function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]);t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+" (stub)"},o="capture identify alias people.set people.set_once set_config register register_once unregister opt_out_capturing has_opted_out_capturing opt_in_capturing reset isFeatureEnabled onFeatureFlags getFeatureFlag getFeatureFlagPayload reloadFeatureFlags group updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures getActiveMatchingSurveys getSurveys onSessionId".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
        posthog.init("${key}", {api_host: "${host || "https://us.i.posthog.com"}", person_profiles: "identified_only", capture_pageview: false, capture_pageleave: true, session_recording: { maskAllInputs: true }});
    `;
    document.head.appendChild(script);
}

export function AnalyticsProvider({ children }) {
    const { user } = useAuth();
    const key  = process.env.REACT_APP_POSTHOG_KEY  || "";
    const host = process.env.REACT_APP_POSTHOG_HOST || "https://us.i.posthog.com";

    useEffect(() => {
        if (key) loadPostHog(key, host);
    }, [key, host]);

    // Identify user when logged in
    useEffect(() => {
        if (!user || !window.posthog) return;
        window.posthog.identify(user.user_id || user.email, {
            email: user.email,
            name:  user.name,
            plan:  user.plan || "free",
        });
    }, [user]);

    return <PostHogContext.Provider value={null}>{children}</PostHogContext.Provider>;
}

// ── Track helper ─────────────────────────────────────────────────

export function track(event, props = {}) {
    try {
        if (window.posthog) {
            window.posthog.capture(event, props);
        }
    } catch { /* noop */ }
}

// ── Page view hook ───────────────────────────────────────────────

export function usePageView(pageName) {
    useEffect(() => {
        track("$pageview", { page: pageName });
    }, [pageName]);
}

// ── Key events ───────────────────────────────────────────────────

export const Analytics = {
    jobSaved:        (jobId, score)     => track("job_saved",            { job_id: jobId, score }),
    jobApplied:      (jobId, company)   => track("job_applied",          { job_id: jobId, company }),
    cvTailored:      (jobTitle)         => track("cv_tailored",          { job_title: jobTitle }),
    atsScored:       (score)            => track("ats_scored",            { score }),
    coverLetterGen:  (lang)             => track("cover_letter_generated",{ language: lang }),
    interviewStarted:(company)          => track("interview_prep_started",{ company }),
    salaryChecked:   (role, location)   => track("salary_checked",        { role, location }),
    trialStarted:    ()                 => track("trial_started"),
    upgradeClicked:  (from)             => track("upgrade_clicked",       { from }),
    referralShared:  ()                 => track("referral_shared"),
    gmailConnected:  ()                 => track("gmail_connected"),
    extensionInstall:()                 => track("extension_install_clicked"),
    featureBlocked:  (feature, plan)    => track("feature_quota_hit",    { feature, plan }),
};
