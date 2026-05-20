/**
 * ContextualSuggestions — the UX cohesion engine.
 *
 * Shows smart contextual prompts that guide users from
 * one feature to the next based on their current state.
 *
 * Examples:
 *   After saving a job → "Tailor your CV for this role?"
 *   After rejection   → "Prepare for next interview"
 *   After ATS score   → "Generate cover letter?"
 *   Low interview rate → "Interview practice recommended"
 */
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Link } from "react-router-dom";
import {
    ArrowRight, MagicWand, ChatCircle,
    CurrencyDollar, FileText, TrendUp, Warning
} from "@phosphor-icons/react";

const SUGGESTION_TYPES = {
    tailor_cv: {
        icon: MagicWand,
        color: "#3B82F6",
        title: "Tailor your CV",
        cta: "Tailor Now",
        route: "/cv-tailor",
    },
    interview_prep: {
        icon: ChatCircle,
        color: "#8B5CF6",
        title: "Prepare for interviews",
        cta: "Practice Now",
        route: "/interview-prep",
    },
    salary_check: {
        icon: CurrencyDollar,
        color: "#10B981",
        title: "Check salary range",
        cta: "Check Salary",
        route: "/salary",
    },
    cover_letter: {
        icon: FileText,
        color: "#F59E0B",
        title: "Write a cover letter",
        cta: "Generate",
        route: "/cv-tailor",
    },
    strategic_plan: {
        icon: TrendUp,
        color: "#EC4899",
        title: "Get your 90-day plan",
        cta: "View Plan",
        route: "/insights",
    },
    wellbeing: {
        icon: Warning,
        color: "#EF4444",
        title: "Job search check-in",
        cta: "View",
        route: "/insights",
    },
};

export default function ContextualSuggestions({ context = "dashboard" }) {
    const [suggestions, setSuggestions] = useState([]);

    useEffect(() => {
        loadSuggestions();
    }, [context]);

    const loadSuggestions = async () => {
        try {
            const [insightsRes, onboardingRes, wellbeingRes] = await Promise.allSettled([
                api.get("/insights"),
                api.get("/onboarding"),
                api.get("/decision/wellbeing-check"),
            ]);

            const insights  = insightsRes.status  === "fulfilled" ? insightsRes.value.data  : {};
            const onboarding = onboardingRes.status === "fulfilled" ? onboardingRes.value.data : {};
            const wellbeing  = wellbeingRes.status  === "fulfilled" ? wellbeingRes.value.data  : {};

            const newSuggestions = [];

            // Low interview rate → recommend interview prep
            const interviewRate = insights?.rates?.interview_rate || 0;
            if (interviewRate < 20 && insights?.totals?.applied > 3) {
                newSuggestions.push({
                    type: "interview_prep",
                    message: `Your interview rate is ${interviewRate}%. Practice can double it.`,
                    priority: 1,
                    params: "",
                });
            }

            // Profile incomplete → CV won't score well
            if (onboarding?.steps) {
                const cvStep = onboarding.steps.find(s => s.step_id === "upload_cv");
                if (cvStep && !cvStep.completed) {
                    newSuggestions.push({
                        type: "tailor_cv",
                        message: "Upload your CV to enable AI matching and tailoring.",
                        priority: 2,
                        params: "",
                    });
                }
            }

            // High rejection streak → wellbeing check
            if (wellbeing?.risk_level === "high") {
                newSuggestions.push({
                    type: "wellbeing",
                    message: wellbeing.message || "Consider reviewing your job search strategy.",
                    priority: 0,
                    params: "",
                });
            }

            // Many applications → check salary intelligence
            if ((insights?.totals?.applied || 0) > 5 && context === "dashboard") {
                newSuggestions.push({
                    type: "salary_check",
                    message: "Know your market rate before your next interview.",
                    priority: 3,
                    params: "",
                });
            }

            // Sort by priority and take top 2
            newSuggestions.sort((a, b) => a.priority - b.priority);
            setSuggestions(newSuggestions.slice(0, 2));

        } catch {
            // Silently fail — suggestions are enhancement only
        }
    };

    if (!suggestions.length) return null;

    return (
        <div className="space-y-2" data-testid="contextual-suggestions">
            {suggestions.map((s, i) => {
                const meta = SUGGESTION_TYPES[s.type];
                if (!meta) return null;
                const IconComp = meta.icon;

                return (
                    <Link
                        key={i}
                        to={`${meta.route}${s.params}`}
                        className="flex items-center gap-3 p-3 rounded-xl border border-zinc-800
                                   bg-zinc-900/50 hover:border-zinc-700 hover:bg-zinc-900
                                   transition-all group"
                    >
                        <div
                            className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center"
                            style={{
                                background: `${meta.color}18`,
                                border: `1px solid ${meta.color}30`,
                            }}
                        >
                            <IconComp size={14} weight="fill" color={meta.color} />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-xs font-semibold text-zinc-300">{meta.title}</p>
                            <p className="text-xs text-zinc-500 truncate">{s.message}</p>
                        </div>
                        <ArrowRight
                            size={13}
                            className="text-zinc-600 group-hover:text-zinc-300 transition-colors flex-shrink-0"
                        />
                    </Link>
                );
            })}
        </div>
    );
}
