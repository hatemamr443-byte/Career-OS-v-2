import { useState } from "react";
import { api } from "../lib/api";
import { TrendUp, Brain, Warning, ArrowRight } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import ContextualSuggestions from "../components/ContextualSuggestions";

export default function DecisionEngine() {
    const [tab, setTab] = useState("plan");
    const [plan, setPlan]       = useState(null);
    const [wellbeing, setWell]  = useState(null);
    const [gaps, setGaps]       = useState(null);
    const [loading, setLoading] = useState({});

    const load = async (key, endpoint) => {
        setLoading(l => ({...l, [key]: true}));
        try {
            const r = await api.get(endpoint);
            if (key === "plan")      setPlan(r.data);
            if (key === "wellbeing") setWell(r.data);
            if (key === "gaps")      setGaps(r.data);
        } catch {}
        setLoading(l => ({...l, [key]: false}));
    };

    const riskColor = r => ({ high: "#EF4444", medium: "#FBBF24", low: "#10B981" }[r] || "#71717A");

    return (
        <div className="px-6 py-8 max-w-4xl mx-auto">
            <div className="mb-6">
                <div className="overline">AI Intelligence</div>
                <h1 className="font-display font-black text-4xl tracking-tight mt-2">Decision Engine</h1>
                <p className="text-zinc-500 text-sm mt-2">Strategic career intelligence powered by your full history.</p>
            </div>

            {/* Contextual suggestions */}
            <div className="mb-6"><ContextualSuggestions context="decision" /></div>

            {/* Tabs */}
            <div className="flex gap-1 mb-8 border-b border-zinc-800">
                {[
                    { id: "plan",      label: "90-Day Plan",    icon: TrendUp  },
                    { id: "wellbeing", label: "Wellbeing Check", icon: Warning  },
                    { id: "gaps",      label: "Skill Gaps",      icon: Brain    },
                ].map(t => (
                    <button key={t.id} onClick={() => setTab(t.id)}
                        className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                            tab === t.id ? "border-zinc-100 text-zinc-100"
                                        : "border-transparent text-zinc-500 hover:text-zinc-300"
                        }`}>
                        {t.label}
                    </button>
                ))}
            </div>

            {/* 90-Day Plan */}
            {tab === "plan" && (
                <div className="space-y-5">
                    {!plan && (
                        <button onClick={() => load("plan", "/decision/strategic-plan")}
                            disabled={loading.plan}
                            className="flex items-center gap-2 bg-zinc-50 text-black px-5 py-2.5
                                       rounded-lg text-sm font-semibold hover:bg-zinc-200 transition-colors
                                       disabled:opacity-40">
                            <TrendUp size={16} weight="fill" />
                            {loading.plan ? "Analyzing your career…" : "Generate My 90-Day Plan"}
                        </button>
                    )}
                    {plan && (
                        <>
                            <div className="card-soft p-5">
                                <p className="text-xs text-zinc-500 mb-2">Situation Assessment</p>
                                <p className="text-sm text-zinc-200 leading-relaxed">{plan.situation_assessment}</p>
                                {plan.biggest_blocker && (
                                    <div className="mt-3 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg">
                                        <p className="text-xs text-red-400">⚠ Biggest blocker: {plan.biggest_blocker}</p>
                                    </div>
                                )}
                            </div>

                            {[
                                { label: "Weeks 1–4",  items: plan.week_1_4,  color: "#3B82F6" },
                                { label: "Weeks 5–8",  items: plan.week_5_8,  color: "#8B5CF6" },
                                { label: "Weeks 9–12", items: plan.week_9_12, color: "#10B981" },
                            ].map(w => (
                                <div key={w.label} className="card-soft p-4">
                                    <h4 className="text-xs font-semibold mb-2" style={{ color: w.color }}>{w.label}</h4>
                                    <ul className="space-y-1">
                                        {(w.items || []).map((item, i) => (
                                            <li key={i} className="text-xs text-zinc-400 flex gap-2">
                                                <span style={{ color: w.color }}>→</span>{item}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            ))}

                            {plan.strategic_recommendation && (
                                <div className="card-soft p-4 border-l-2 border-yellow-500">
                                    <p className="text-xs font-semibold text-yellow-400 mb-1">Final Advice</p>
                                    <p className="text-sm text-zinc-300">{plan.strategic_recommendation}</p>
                                </div>
                            )}

                            <button onClick={() => setPlan(null)}
                                className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">
                                Regenerate plan
                            </button>
                        </>
                    )}
                </div>
            )}

            {/* Wellbeing */}
            {tab === "wellbeing" && (
                <div className="space-y-4">
                    {!wellbeing && (
                        <button onClick={() => load("wellbeing", "/decision/wellbeing-check")}
                            disabled={loading.wellbeing}
                            className="flex items-center gap-2 bg-zinc-50 text-black px-5 py-2.5
                                       rounded-lg text-sm font-semibold hover:bg-zinc-200 transition-colors
                                       disabled:opacity-40">
                            <Warning size={16} weight="fill" />
                            {loading.wellbeing ? "Checking…" : "Check My Wellbeing"}
                        </button>
                    )}
                    {wellbeing && (
                        <>
                            <div className="card-soft p-6 flex items-center gap-5">
                                <div className="text-center">
                                    <div className="text-5xl font-black"
                                         style={{ color: riskColor(wellbeing.risk_level) }}>
                                        {wellbeing.risk_level?.toUpperCase()}
                                    </div>
                                    <p className="text-xs text-zinc-500 mt-1">Risk Level</p>
                                </div>
                                <p className="flex-1 text-sm text-zinc-300 leading-relaxed">{wellbeing.message}</p>
                            </div>

                            <div className="grid grid-cols-3 gap-3">
                                {[
                                    { label: "Rejection Streak", val: wellbeing.rejection_streak },
                                    { label: "Total Apps",       val: wellbeing.total_applications },
                                    { label: "Offers",           val: wellbeing.offers_received },
                                ].map(s => (
                                    <div key={s.label} className="card-soft p-3 text-center">
                                        <p className="font-mono-ui text-2xl font-bold">{s.val}</p>
                                        <p className="text-xs text-zinc-500 mt-1">{s.label}</p>
                                    </div>
                                ))}
                            </div>

                            <div className="card-soft p-4">
                                <h4 className="text-xs font-semibold text-zinc-400 mb-2">Recommendations</h4>
                                <ul className="space-y-2">
                                    {(wellbeing.recommendations || []).map((r, i) => (
                                        <li key={i} className="text-sm text-zinc-300 flex gap-2">
                                            <span className="text-green-400">✓</span>{r}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </>
                    )}
                </div>
            )}

            {/* Skill Gaps */}
            {tab === "gaps" && (
                <div className="space-y-4">
                    {!gaps && (
                        <button onClick={() => load("gaps", "/decision/skill-gaps")}
                            disabled={loading.gaps}
                            className="flex items-center gap-2 bg-zinc-50 text-black px-5 py-2.5
                                       rounded-lg text-sm font-semibold hover:bg-zinc-200 transition-colors
                                       disabled:opacity-40">
                            <Brain size={16} weight="fill" />
                            {loading.gaps ? "Analyzing skills…" : "Analyze My Skill Gaps"}
                        </button>
                    )}
                    {gaps && (
                        <>
                            <div className="grid md:grid-cols-2 gap-4">
                                {[
                                    { title: "Critical Gaps",   items: gaps.critical_gaps,  color: "#EF4444" },
                                    { title: "Quick Wins",      items: gaps.quick_wins,     color: "#10B981" },
                                    { title: "Long-Term Skills",items: gaps.long_term_skills,color: "#8B5CF6"},
                                    { title: "Priority Order",  items: gaps.priority_order, color: "#FBBF24" },
                                ].map(s => (
                                    <div key={s.title} className="card-soft p-4">
                                        <h4 className="text-xs font-semibold mb-2" style={{ color: s.color }}>
                                            {s.title}
                                        </h4>
                                        <ul className="space-y-1">
                                            {(s.items || []).slice(0, 5).map((item, i) => (
                                                <li key={i} className="text-xs text-zinc-400">• {item}</li>
                                            ))}
                                        </ul>
                                    </div>
                                ))}
                            </div>

                            {gaps.impact_estimate && (
                                <div className="card-soft p-4 border-l-2 border-green-500">
                                    <p className="text-xs font-semibold text-green-400 mb-1">Expected Impact</p>
                                    <p className="text-sm text-zinc-300">{gaps.impact_estimate}</p>
                                </div>
                            )}

                            <div className="flex gap-3 pt-2">
                                <Link to="/interview-prep"
                                    className="text-xs flex items-center gap-1 text-zinc-400 hover:text-zinc-200 transition-colors">
                                    Practice interview skills <ArrowRight size={11} />
                                </Link>
                                <Link to="/cv-tailor"
                                    className="text-xs flex items-center gap-1 text-zinc-400 hover:text-zinc-200 transition-colors">
                                    Tailor CV for gaps <ArrowRight size={11} />
                                </Link>
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
}
