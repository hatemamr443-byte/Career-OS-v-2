import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { X, Shield } from "lucide-react";

/**
 * GDPR-compliant cookie consent banner.
 * Persists choice in localStorage and POSTs to /api/me/consent when the user is authenticated.
 * Mounts globally in App.js. Visible until "Accept" or "Reject non-essential" is clicked.
 */
const STORAGE_KEY = "careeros.cookieConsent.v1";

export default function CookieConsent() {
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (!saved) setVisible(true);
        } catch {
            setVisible(true);
        }
    }, []);

    const persist = async (choice) => {
        const payload = {
            essential: true,
            analytics: choice === "accept_all",
            marketing_emails: choice === "accept_all",
            ai_improvement: choice === "accept_all",
            ts: new Date().toISOString(),
        };
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
        } catch { /* no-op */ }

        // Best-effort sync to server (no auth required for essential-only)
        try {
            const backend = process.env.REACT_APP_BACKEND_URL || "";
            await fetch(`${backend}/api/me/consent`, {
                method: "PATCH",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    analytics: payload.analytics,
                    marketing_emails: payload.marketing_emails,
                    ai_improvement: payload.ai_improvement,
                }),
            });
        } catch { /* unauthenticated users just save locally */ }

        setVisible(false);
    };

    if (!visible) return null;

    return (
        <div
            data-testid="cookie-consent-banner"
            className="fixed bottom-0 left-0 right-0 z-50 px-4 pb-4 sm:pb-6 sm:px-6 pointer-events-none"
        >
            <div className="mx-auto max-w-4xl rounded-2xl border border-neutral-200/80 bg-white/95 backdrop-blur shadow-2xl pointer-events-auto">
                <div className="p-5 sm:p-6 flex flex-col sm:flex-row sm:items-start gap-4">
                    <div className="flex-shrink-0 hidden sm:flex h-10 w-10 items-center justify-center rounded-xl bg-neutral-900 text-white">
                        <Shield size={18} />
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-base font-semibold text-neutral-900">
                            Your privacy, your choice
                        </p>
                        <p className="mt-1 text-sm text-neutral-600 leading-relaxed">
                            Career OS uses cookies essential to authentication and a small set
                            of optional analytics to improve your career insights. You can
                            change this anytime in your profile.{" "}
                            <Link
                                to="/privacy"
                                data-testid="cookie-consent-privacy-link"
                                className="underline underline-offset-2 hover:text-neutral-900"
                            >
                                Privacy Policy
                            </Link>{" "}
                            ·{" "}
                            <Link
                                to="/terms"
                                data-testid="cookie-consent-terms-link"
                                className="underline underline-offset-2 hover:text-neutral-900"
                            >
                                Terms
                            </Link>
                        </p>
                    </div>
                    <div className="flex flex-col sm:flex-row gap-2 sm:items-center">
                        <button
                            data-testid="cookie-consent-reject-btn"
                            type="button"
                            onClick={() => persist("essential_only")}
                            className="rounded-full px-4 py-2 text-sm font-medium border border-neutral-300 bg-white text-neutral-900 hover:bg-neutral-50 transition-colors"
                        >
                            Essential only
                        </button>
                        <button
                            data-testid="cookie-consent-accept-btn"
                            type="button"
                            onClick={() => persist("accept_all")}
                            className="rounded-full px-4 py-2 text-sm font-semibold bg-neutral-900 text-white hover:bg-neutral-800 transition-colors"
                        >
                            Accept all
                        </button>
                        <button
                            data-testid="cookie-consent-close-btn"
                            aria-label="Dismiss"
                            type="button"
                            onClick={() => persist("essential_only")}
                            className="hidden sm:inline-flex items-center justify-center h-8 w-8 rounded-full hover:bg-neutral-100 text-neutral-500"
                        >
                            <X size={14} />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
