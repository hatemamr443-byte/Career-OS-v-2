import { useEffect } from "react";
import { Sparkle, ArrowRight, GoogleLogo } from "@phosphor-icons/react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
    const { user, loading } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        if (!loading && user) navigate("/dashboard", { replace: true });
    }, [user, loading, navigate]);

    const signIn = () => {
        // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
        const redirectUrl = window.location.origin + "/dashboard";
        window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
    };

    return (
        <div className="min-h-screen grid lg:grid-cols-2 grain" data-testid="login-page">
            {/* Left: brand */}
            <div className="relative flex flex-col justify-between p-10 border-r border-zinc-900 dot-grid">
                <div className="flex items-center gap-2">
                    <div className="w-9 h-9 rounded-md bg-zinc-50 text-black flex items-center justify-center">
                        <Sparkle weight="fill" size={20} />
                    </div>
                    <div className="font-display font-black text-xl tracking-tight">Career OS</div>
                </div>
                <div>
                    <div className="overline mb-4">an intelligent career system</div>
                    <h1 className="h1-hero text-5xl sm:text-6xl mb-6">
                        Stop searching.
                        <br />
                        Start <span style={{ color: "#FF5C00" }}>deciding</span>.
                    </h1>
                    <p className="text-zinc-400 max-w-md leading-relaxed">
                        An AI career agent that thinks, decides, acts, and learns — so every application
                        you make is the right one.
                    </p>
                    <div className="mt-8 grid grid-cols-2 gap-4 max-w-md">
                        {[
                            { k: "Decision Engine", c: "#10B981" },
                            { k: "Daily Missions", c: "#FBBF24" },
                            { k: "Email Triage", c: "#007AFF" },
                            { k: "Streak System", c: "#FF5C00" },
                        ].map((f) => (
                            <div key={f.k} className="flex items-center gap-2 text-sm">
                                <div className="w-1.5 h-1.5 rounded-full" style={{ background: f.c }} />
                                <span className="text-zinc-300">{f.k}</span>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="text-xs text-zinc-600">
                    Built for serious operators. Not a job board.
                </div>
            </div>

            {/* Right: action */}
            <div className="flex items-center justify-center p-10">
                <div className="w-full max-w-sm">
                    <div className="overline mb-3">Sign in</div>
                    <h2 className="font-display font-black text-3xl mb-2 tracking-tight">Enter your Career OS</h2>
                    <p className="text-zinc-500 text-sm mb-8">
                        One-click Google sign-in. No password. We never post on your behalf.
                    </p>
                    <button
                        onClick={signIn}
                        data-testid="google-signin-btn"
                        className="w-full bg-zinc-50 text-black hover:bg-zinc-200 transition-colors rounded-xl px-5 py-4 font-medium flex items-center justify-center gap-3"
                    >
                        <GoogleLogo size={18} weight="bold" />
                        Continue with Google
                        <ArrowRight size={16} />
                    </button>
                    <div className="mt-6 text-xs text-zinc-600 leading-relaxed">
                        By continuing, you agree to a fair, GDPR-aware data policy. Your CV stays yours.
                    </div>
                </div>
            </div>
        </div>
    );
}
