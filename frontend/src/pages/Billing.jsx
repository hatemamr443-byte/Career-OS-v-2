import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { ArrowRight, CheckCircle, X, Warning } from "@phosphor-icons/react";
import UsageBanner from "../components/UsageBanner";

export default function Billing() {
    const [me, setMe] = useState({ plan: "free", plan_expires_at: null });
    const [usage, setUsage] = useState(null);
    const [confirmOpen, setConfirmOpen] = useState(false);
    const [cancelling, setCancelling] = useState(false);
    const [flash, setFlash] = useState(null);

    const load = async () => {
        try {
            const [m, u] = await Promise.all([api.get("/billing/me"), api.get("/me/usage")]);
            setMe(m.data);
            setUsage(u.data);
        } catch (err) {
            console.error("billing load failed:", err);
        }
    };

    useEffect(() => {
        load();
    }, []);

    const cancel = async () => {
        setCancelling(true);
        try {
            const r = await api.post("/billing/cancel");
            setFlash(r.data.message);
            setConfirmOpen(false);
            await load();
        } catch (err) {
            console.error("cancel failed:", err);
            setFlash("Cancellation failed. Please try again.");
        }
        setCancelling(false);
    };

    const expiry = me.plan_expires_at ? new Date(me.plan_expires_at).toLocaleDateString() : null;
    const isPaid = me.plan === "pro" || me.plan === "team";

    return (
        <div className="px-8 py-8 max-w-4xl mx-auto" data-testid="billing-page">
            <UsageBanner context="billing" />

            <div className="overline">Account</div>
            <h1 className="font-display font-black text-4xl tracking-tight mt-2 mb-8">Billing</h1>

            {flash && (
                <div className="card-soft p-3 mb-4 text-sm text-emerald-400 border-emerald-500/30" data-testid="billing-flash">
                    {flash}
                </div>
            )}

            <div className="card-soft p-6 mb-6" data-testid="current-plan-card">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                    <div>
                        <div className="overline mb-1">Current plan</div>
                        <div className="font-display font-black text-3xl tracking-tight capitalize">{me.plan}</div>
                        {expiry && isPaid && (
                            <div className="text-zinc-500 text-sm mt-1">Active until {expiry}</div>
                        )}
                        {usage && me.plan === "free" && (
                            <div className="text-zinc-500 text-sm mt-1 font-mono-ui">
                                {usage.matches_used}/{usage.matches_limit} matches used this month
                            </div>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        {isPaid && (
                            <button
                                onClick={() => setConfirmOpen(true)}
                                data-testid="cancel-subscription-btn"
                                className="border border-zinc-800 hover:border-red-500/40 hover:text-red-400 transition-colors rounded-lg px-4 py-2.5 text-sm text-zinc-300"
                            >
                                Cancel subscription
                            </button>
                        )}
                        <Link
                            to="/pricing"
                            data-testid="manage-plan-btn"
                            className="bg-zinc-50 text-black hover:bg-zinc-200 transition-colors rounded-lg px-5 py-2.5 text-sm font-medium flex items-center gap-2"
                        >
                            {me.plan === "free" ? "Upgrade plan" : "Change plan"}
                            <ArrowRight size={14} />
                        </Link>
                    </div>
                </div>
            </div>

            <div className="card-soft p-6">
                <div className="overline mb-3">What Pro unlocks</div>
                <ul className="space-y-2 text-sm text-zinc-300">
                    {[
                        "Unlimited AI match analyses (Claude Sonnet 4.5)",
                        "Full decision engine + reasoning depth",
                        "AI Coach with career memory",
                        "Insights + pattern detection",
                        "Strategy auto-switching when conversion drops",
                    ].map((f) => (
                        <li key={f} className="flex gap-2">
                            <CheckCircle size={14} weight="fill" color="#10B981" className="mt-0.5 flex-shrink-0" />
                            {f}
                        </li>
                    ))}
                </ul>
            </div>

            {/* Confirm Cancel modal */}
            {confirmOpen && (
                <div
                    className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-6"
                    data-testid="cancel-modal"
                >
                    <div className="glass rounded-2xl p-6 max-w-md w-full">
                        <div className="flex items-start gap-3 mb-4">
                            <div className="w-10 h-10 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center flex-shrink-0">
                                <Warning size={18} weight="fill" color="#EF4444" />
                            </div>
                            <div>
                                <h3 className="font-display font-bold text-xl tracking-tight">Cancel your {me.plan} plan?</h3>
                                <p className="text-zinc-400 text-sm mt-1">
                                    You'll drop to Free immediately. Unlimited matching and AI Coach memory will be revoked.
                                    Your data stays intact — you can re-upgrade any time.
                                </p>
                            </div>
                            <button onClick={() => setConfirmOpen(false)} className="text-zinc-500 hover:text-zinc-100" data-testid="cancel-modal-close">
                                <X size={18} />
                            </button>
                        </div>
                        <div className="flex gap-2 mt-5">
                            <button
                                onClick={() => setConfirmOpen(false)}
                                data-testid="cancel-modal-keep"
                                className="flex-1 border border-zinc-800 hover:border-zinc-700 rounded-lg px-4 py-2.5 text-sm"
                            >
                                Keep my plan
                            </button>
                            <button
                                onClick={cancel}
                                disabled={cancelling}
                                data-testid="cancel-modal-confirm"
                                className="flex-1 bg-red-500/15 border border-red-500/30 text-red-400 hover:bg-red-500/25 transition-colors rounded-lg px-4 py-2.5 text-sm font-medium"
                            >
                                {cancelling ? "Cancelling…" : "Yes, cancel"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
