import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { CheckCircle, ArrowRight, Sparkle } from "@phosphor-icons/react";

const PLAN_FEATURES = {
    free: [
        "Up to 5 AI match analyses / month",
        "Daily mission engine (basic)",
        "Application tracker (unlimited)",
        "Recruiter inbox (mock)",
        "Career Map kanban",
    ],
    pro: [
        "Unlimited AI match analyses",
        "Full decision engine + reasoning depth",
        "AI Coach with career memory",
        "Insights + pattern detection",
        "Strategy auto-switching",
        "Priority LLM (Claude Sonnet 4.5)",
    ],
    team: [
        "Everything in Pro",
        "Up to 5 seats",
        "Shared career map",
        "Team analytics + benchmarks",
        "Concierge onboarding",
        "Priority support",
    ],
};

export default function Pricing() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [busy, setBusy] = useState(null);
    const [error, setError] = useState(null);
    const [current, setCurrent] = useState("free");

    useEffect(() => {
        if (!user) return;
        api.get("/billing/me").then((r) => setCurrent(r.data.plan || "free")).catch(() => {});
    }, [user]);

    const signIn = () => {
        // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
        const redirectUrl = window.location.origin + "/pricing";
        window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
    };

    const upgrade = async (plan_id) => {
        if (!user) {
            signIn();
            return;
        }
        setBusy(plan_id);
        setError(null);
        try {
            const r = await api.post("/billing/checkout", {
                plan_id,
                origin_url: window.location.origin,
            });
            window.location.href = r.data.url;
        } catch (err) {
            console.error("checkout failed:", err);
            setError("Checkout failed. Please try again.");
            setBusy(null);
        }
    };

    const cardCls = (plan) =>
        `card-soft p-6 flex flex-col ${plan === "pro" ? "border-zinc-50/30" : ""}`;

    return (
        <div className="min-h-screen grain" data-testid="pricing-page">
            <header className="border-b border-zinc-900 bg-black/40">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <Link to="/" className="flex items-center gap-2" data-testid="logo-link">
                        <div className="w-8 h-8 rounded-md bg-zinc-50 text-black flex items-center justify-center">
                            <Sparkle weight="fill" size={18} />
                        </div>
                        <div className="font-display font-black tracking-tight">Career OS</div>
                    </Link>
                    {user ? (
                        <Link to="/dashboard" className="text-sm text-zinc-300 hover:text-zinc-100" data-testid="back-to-dashboard">
                            Back to dashboard →
                        </Link>
                    ) : (
                        <button
                            onClick={signIn}
                            data-testid="signin-from-pricing"
                            className="bg-zinc-50 text-black hover:bg-zinc-200 transition-colors rounded-lg px-4 py-2 text-sm font-medium"
                        >
                            Sign in
                        </button>
                    )}
                </div>
            </header>

            <main className="max-w-6xl mx-auto px-6 py-20">
                <div className="text-center mb-14">
                    <div className="overline mb-3">Pricing</div>
                    <h1 className="font-display font-black text-5xl tracking-tight mb-4">
                        Pay for outcomes,<br />not for searching.
                    </h1>
                    <p className="text-zinc-400 max-w-lg mx-auto">
                        Free until the AI is paying for itself. Upgrade only when the volume of decisions justifies it.
                    </p>
                </div>

                <div className="grid md:grid-cols-3 gap-4">
                    {/* Free */}
                    <div className={cardCls("free")} data-testid="plan-free">
                        <div className="overline">Free</div>
                        <div className="font-display font-black text-4xl mt-2 mb-4">$0</div>
                        <div className="text-zinc-500 text-sm mb-6">Forever. No credit card.</div>
                        <ul className="space-y-2.5 mb-6 flex-1">
                            {PLAN_FEATURES.free.map((f) => (
                                <li key={f} className="flex gap-2 text-sm text-zinc-300">
                                    <CheckCircle size={14} weight="fill" color="#71717A" className="mt-0.5 flex-shrink-0" />{f}
                                </li>
                            ))}
                        </ul>
                        {current === "free" ? (
                            <div className="bg-zinc-900 border border-zinc-800 text-zinc-400 text-center rounded-lg px-4 py-3 text-sm" data-testid="current-free">
                                Current plan
                            </div>
                        ) : (
                            <button
                                onClick={signIn}
                                className="border border-zinc-800 hover:border-zinc-700 text-zinc-200 rounded-lg px-4 py-3 text-sm"
                                data-testid="cta-free"
                            >
                                Get started
                            </button>
                        )}
                    </div>

                    {/* Pro */}
                    <div className={`${cardCls("pro")} relative`} data-testid="plan-pro">
                        <div className="absolute -top-3 left-6 px-2 py-0.5 bg-zinc-50 text-black text-[10px] font-mono-ui uppercase tracking-widest rounded">
                            Most popular
                        </div>
                        <div className="overline">Pro</div>
                        <div className="font-display font-black text-4xl mt-2 mb-1">
                            $19<span className="text-base text-zinc-500 font-display font-medium">/mo</span>
                        </div>
                        <div className="text-zinc-500 text-sm mb-6">For active job seekers.</div>
                        <ul className="space-y-2.5 mb-6 flex-1">
                            {PLAN_FEATURES.pro.map((f) => (
                                <li key={f} className="flex gap-2 text-sm text-zinc-300">
                                    <CheckCircle size={14} weight="fill" color="#10B981" className="mt-0.5 flex-shrink-0" />{f}
                                </li>
                            ))}
                        </ul>
                        {current === "pro" ? (
                            <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-center rounded-lg px-4 py-3 text-sm" data-testid="current-pro">
                                Current plan
                            </div>
                        ) : (
                            <button
                                onClick={() => upgrade("pro")}
                                disabled={busy === "pro"}
                                data-testid="cta-pro"
                                className="bg-zinc-50 text-black hover:bg-zinc-200 transition-colors rounded-lg px-4 py-3 text-sm font-medium flex items-center justify-center gap-2"
                            >
                                {busy === "pro" ? "Redirecting…" : "Upgrade to Pro"}
                                {busy !== "pro" && <ArrowRight size={14} />}
                            </button>
                        )}
                    </div>

                    {/* Team */}
                    <div className={cardCls("team")} data-testid="plan-team">
                        <div className="overline">Team</div>
                        <div className="font-display font-black text-4xl mt-2 mb-1">
                            $49<span className="text-base text-zinc-500 font-display font-medium">/mo</span>
                        </div>
                        <div className="text-zinc-500 text-sm mb-6">Up to 5 seats.</div>
                        <ul className="space-y-2.5 mb-6 flex-1">
                            {PLAN_FEATURES.team.map((f) => (
                                <li key={f} className="flex gap-2 text-sm text-zinc-300">
                                    <CheckCircle size={14} weight="fill" color="#FBBF24" className="mt-0.5 flex-shrink-0" />{f}
                                </li>
                            ))}
                        </ul>
                        {current === "team" ? (
                            <div className="bg-amber-500/10 border border-amber-500/30 text-amber-400 text-center rounded-lg px-4 py-3 text-sm" data-testid="current-team">
                                Current plan
                            </div>
                        ) : (
                            <button
                                onClick={() => upgrade("team")}
                                disabled={busy === "team"}
                                data-testid="cta-team"
                                className="border border-zinc-700 hover:border-zinc-500 text-zinc-100 rounded-lg px-4 py-3 text-sm font-medium flex items-center justify-center gap-2"
                            >
                                {busy === "team" ? "Redirecting…" : "Upgrade to Team"}
                                {busy !== "team" && <ArrowRight size={14} />}
                            </button>
                        )}
                    </div>
                </div>

                <div className="mt-12 text-center text-xs text-zinc-500">
                    Test mode. Use Stripe test card <span className="font-mono-ui">4242 4242 4242 4242</span> with any future date and any CVC.
                </div>
                {error && (
                    <div className="mt-4 max-w-md mx-auto p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm text-center" data-testid="checkout-error">
                        {error}
                    </div>
                )}
            </main>
        </div>
    );
}
