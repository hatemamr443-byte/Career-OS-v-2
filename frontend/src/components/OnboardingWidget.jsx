import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { CheckCircle, Circle, Sparkle } from "@phosphor-icons/react";

export default function OnboardingWidget() {
    const [data, setData] = useState(null);
    const [dismissed, setDismissed] = useState(false);

    useEffect(() => {
        api.get("/onboarding").then(r => setData(r.data)).catch(() => {});
        const d = localStorage.getItem("onboarding_dismissed");
        if (d) setDismissed(true);
    }, []);

    if (!data || dismissed || data.done) return null;
    if (data.percent >= 100) return null;

    const handleDismiss = () => {
        localStorage.setItem("onboarding_dismissed", "1");
        setDismissed(true);
    };

    return (
        <div className="card-soft p-5 border border-zinc-700 space-y-4" data-testid="onboarding-widget">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Sparkle size={16} weight="fill" color="#FBBF24" />
                    <span className="font-display font-bold text-sm">Get Started</span>
                    <span className="font-mono-ui text-xs text-zinc-500">
                        {data.completed_count}/{data.total_steps}
                    </span>
                </div>
                <button onClick={handleDismiss} className="text-zinc-600 hover:text-zinc-400 text-xs">
                    dismiss
                </button>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-zinc-800 rounded-full h-1">
                <div
                    className="h-1 rounded-full bg-yellow-400 transition-all duration-700"
                    style={{ width: `${data.percent}%` }}
                />
            </div>

            {/* Steps */}
            <div className="space-y-2">
                {data.steps.slice(0, 4).map((step) => (
                    <div key={step.step_id} className="flex items-center gap-3">
                        {step.completed
                            ? <CheckCircle size={16} weight="fill" color="#10B981" className="flex-shrink-0" />
                            : <Circle size={16} weight="regular" color="#52525b" className="flex-shrink-0" />
                        }
                        <div className="flex-1 min-w-0">
                            <p className={`text-xs font-medium truncate ${step.completed ? "text-zinc-500 line-through" : "text-zinc-300"}`}>
                                {step.title}
                            </p>
                        </div>
                        <span className="text-xs text-zinc-600 flex-shrink-0">+{step.xp_reward} XP</span>
                    </div>
                ))}
            </div>

            {data.total_xp_available > 0 && (
                <p className="text-xs text-zinc-500">
                    Complete all steps to earn {data.total_xp_available} XP
                </p>
            )}
        </div>
    );
}
