import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { ArrowRight, CheckCircle } from "@phosphor-icons/react";

export default function Billing() {
    const [me, setMe] = useState({ plan: "free", plan_expires_at: null });

    useEffect(() => {
        api.get("/billing/me").then((r) => setMe(r.data)).catch((err) => console.error("billing/me failed:", err));
    }, []);

    const expiry = me.plan_expires_at ? new Date(me.plan_expires_at).toLocaleDateString() : null;

    return (
        <div className="px-8 py-8 max-w-4xl mx-auto" data-testid="billing-page">
            <div className="overline">Account</div>
            <h1 className="font-display font-black text-4xl tracking-tight mt-2 mb-8">Billing</h1>

            <div className="card-soft p-6 mb-6" data-testid="current-plan-card">
                <div className="flex items-center justify-between gap-4 flex-wrap">
                    <div>
                        <div className="overline mb-1">Current plan</div>
                        <div className="font-display font-black text-3xl tracking-tight capitalize">{me.plan}</div>
                        {expiry && me.plan !== "free" && (
                            <div className="text-zinc-500 text-sm mt-1">Renews / expires on {expiry}</div>
                        )}
                    </div>
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
        </div>
    );
}
