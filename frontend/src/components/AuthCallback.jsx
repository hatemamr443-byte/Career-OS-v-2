import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function AuthCallback() {
    const navigate = useNavigate();
    const { setUser } = useAuth();
    const processed = useRef(false);

    useEffect(() => {
        if (processed.current) return;
        processed.current = true;

        const hash = window.location.hash;
        const m = hash.match(/session_id=([^&]+)/);
        if (!m) {
            navigate("/", { replace: true });
            return;
        }
        const session_id = m[1];

        (async () => {
            try {
                const r = await api.post("/auth/session", { session_id });
                setUser(r.data.user);
                // Seed sample data for first-time users (idempotent)
                try {
                    await api.post("/seed-me");
                } catch (seedErr) {
                    console.error("seed-me failed:", seedErr);
                }
                navigate("/dashboard", { replace: true, state: { user: r.data.user } });
            } catch (err) {
                console.error("session exchange failed:", err);
                navigate("/", { replace: true });
            }
        })();
    }, [navigate, setUser]);

    return (
        <div className="min-h-screen flex items-center justify-center text-zinc-400">
            <div className="text-center">
                <div className="overline mb-3">Authenticating</div>
                <div className="font-display text-2xl">Initializing your Career OS…</div>
            </div>
        </div>
    );
}
