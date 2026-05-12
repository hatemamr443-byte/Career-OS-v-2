import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Warning, ArrowRight, X } from "@phosphor-icons/react";

export default function UsageBanner({ context = "default" }) {
    const [usage, setUsage] = useState(null);
    const [dismissed, setDismissed] = useState(false);

    useEffect(() => {
        api
            .get("/me/usage")
            .then((r) => setUsage(r.data))
            .catch((err) => console.error("usage fetch failed:", err));
    }, []);

    if (!usage || dismissed) return null;
    if (usage.plan !== "free") return null;
    if (!usage.near_limit && !usage.over_limit) return null;

    const isOver = usage.over_limit;
    const message = isOver
        ? `You've used all ${usage.matches_limit} free matches this month.`
        : `${usage.matches_used}/${usage.matches_limit} matches used this month — running low.`;
    const subtext = isOver
        ? "Upgrade to Pro for unlimited matching, deeper reasoning, and the full decision engine."
        : "One more match and you're out. Upgrade now and never hit a wall.";
    const colors = isOver
        ? { bg: "bg-orange-500/10", border: "border-orange-500/30", icon: "#FF5C00" }
        : { bg: "bg-amber-500/10", border: "border-amber-500/30", icon: "#FBBF24" };

    return (
        <div
            data-testid={`usage-banner-${context}`}
            className={`relative ${colors.bg} ${colors.border} border rounded-xl p-4 mb-6 flex items-start gap-3`}
        >
            <Warning size={20} weight="fill" color={colors.icon} className="flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
                <div className="font-display font-bold text-base tracking-tight" data-testid="banner-message">
                    {message}
                </div>
                <div className="text-sm text-zinc-400 mt-0.5">{subtext}</div>
            </div>
            <Link
                to="/pricing"
                data-testid="banner-upgrade-cta"
                className="bg-zinc-50 text-black hover:bg-zinc-200 transition-colors rounded-lg px-4 py-2 text-sm font-medium flex items-center gap-2 flex-shrink-0"
            >
                Upgrade <ArrowRight size={14} />
            </Link>
            <button
                onClick={() => setDismissed(true)}
                data-testid="banner-dismiss"
                className="text-zinc-500 hover:text-zinc-100 p-1 flex-shrink-0"
                title="Dismiss"
            >
                <X size={16} />
            </button>
        </div>
    );
}
