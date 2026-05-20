import { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Link } from "react-router-dom";
import { Check, ArrowRight, Sparkle, Flame, TrendUp, Lightning } from "@phosphor-icons/react";
import ActivityFeed from "../components/ActivityFeed";
import ProfileCompleteness from "../components/ProfileCompleteness";
import OnboardingWidget from "../components/OnboardingWidget";
import BrainReveal from "../components/BrainReveal";

const ACTION_LABELS = {
    apply: "Apply",
    review: "Review",
    update_cv: "CV",
    reflect: "Reflect",
    research: "Research",
};

export default function Dashboard() {
    const { user } = useAuth();
    const [missions, setMissions] = useState([]);
    const [stats, setStats] = useState({ xp: 0, level: 1, streak: 0, progress: { percent: 0, current: 0, needed: 100 } });
    const [recs, setRecs] = useState([]);
    const [insights, setInsights] = useState(null);
    const [loading, setLoading] = useState(true);

    const loadAll = useCallback(async () => {
        setLoading(true);
        try {
            const [m, s, r, i] = await Promise.all([
                api.get("/missions/today"),
                api.get("/me/stats"),
                api.get("/decisions/recommendations?limit=4"),
                api.get("/insights"),
            ]);
            setMissions(m.data.missions || []);
            setStats(s.data);
            setRecs(r.data.recommendations || []);
            setInsights(i.data);
        } catch (err) {
            console.error("dashboard load failed:", err);
        }
        setLoading(false);
    }, []);

    useEffect(() => {
        loadAll();
    }, [loadAll]);

    const completeMission = async (id) => {
        try {
            const r = await api.post(`/missions/${id}/complete`);
            setMissions((ms) => ms.map((x) => (x.mission_id === id ? { ...x, completed: true } : x)));
            setStats((s) => ({ ...s, xp: r.data.xp, level: r.data.level, streak: r.data.streak }));
        } catch (err) {
            console.error("mission complete failed:", err);
        }
    };

    const completedCount = missions.filter((m) => m.completed).length;

    return (
        <div className="px-8 py-8 max-w-7xl mx-auto" data-testid="dashboard-page">
            {/* Header */}
            <div className="flex items-end justify-between mb-8 flex-wrap gap-4">
                <div>
                    <div className="overline mb-2">Mission Control</div>
                    <h1 className="font-display font-black text-4xl sm:text-5xl tracking-tight">
                        {(() => {
                            const h = new Date().getHours();
                            const greet = h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
                            return `${greet}, ${user?.name?.split(" ")[0] || "Operator"}.`;
                        })()}
                    </h1>
                    <p className="text-zinc-500 mt-2">Today's plan is ready. {completedCount}/{missions.length} missions complete.</p>
                </div>
                <Link
                    to="/jobs"
                    data-testid="dashboard-view-jobs"
                    className="bg-zinc-50 text-black hover:bg-zinc-200 transition-colors rounded-lg px-5 py-2.5 text-sm font-medium flex items-center gap-2"
                >
                    Browse Jobs <ArrowRight size={14} />
                </Link>
            </div>

            {/* Brain Reveal — thin orchestration surface (renders nothing when empty) */}
            <BrainReveal />

            {/* KPI strip */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                <KPI label="Streak" value={stats.streak} suffix="d" color="#FF5C00" Icon={Flame} testid="kpi-streak" />
                <KPI label="XP" value={stats.xp} color="#FBBF24" Icon={Lightning} testid="kpi-xp" />
                <KPI label="Level" value={stats.level} color="#FAFAFA" Icon={Sparkle} testid="kpi-level" />
                <KPI label="Interview Rate" value={(insights?.rates?.interview_rate ?? 0)} suffix="%" color="#10B981" Icon={TrendUp} testid="kpi-interview" />
            </div>

            <div className="grid lg:grid-cols-3 gap-6">
                {/* Missions */}
                <div className="lg:col-span-2 card-soft p-6" data-testid="missions-panel">
                    <div className="flex items-center justify-between mb-5">
                        <div>
                            <div className="overline">Today's Missions</div>
                            <h2 className="font-display font-bold text-2xl mt-1">Decide, don't drift.</h2>
                        </div>
                        <div className="font-mono-ui text-sm text-zinc-500">{completedCount}/{missions.length}</div>
                    </div>

                    {/* Progress bar */}
                    <div className="h-1.5 bg-zinc-900 rounded-full mb-6 overflow-hidden">
                        <div
                            className="h-full transition-all duration-500"
                            style={{
                                width: missions.length ? `${(completedCount / missions.length) * 100}%` : "0%",
                                background: "#FBBF24",
                            }}
                        />
                    </div>

                    {loading ? (
                        <div className="text-zinc-500 text-sm">Loading missions…</div>
                    ) : missions.length === 0 ? (
                        <div className="text-zinc-500 text-sm">No missions yet. Refresh.</div>
                    ) : (
                        <div className="space-y-3">
                            {missions.map((m) => (
                                <div
                                    key={m.mission_id}
                                    data-testid={`mission-${m.mission_id}`}
                                    className={`flex items-start gap-4 p-4 rounded-xl border transition-all ${
                                        m.completed
                                            ? "border-emerald-500/20 bg-emerald-500/5"
                                            : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-700"
                                    }`}
                                >
                                    <button
                                        onClick={() => !m.completed && completeMission(m.mission_id)}
                                        data-testid={`mission-complete-${m.mission_id}`}
                                        disabled={m.completed}
                                        className={`mt-0.5 w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                                            m.completed
                                                ? "bg-emerald-500 border-emerald-500"
                                                : "border-zinc-700 hover:border-zinc-400"
                                        }`}
                                    >
                                        {m.completed && <Check size={14} weight="bold" color="#000" />}
                                    </button>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                                            <span className="font-display font-bold text-base">{m.title}</span>
                                            <span className="text-[10px] font-mono-ui uppercase tracking-widest px-1.5 py-0.5 bg-zinc-800 rounded text-zinc-400">
                                                {ACTION_LABELS[m.action_type] || m.action_type}
                                            </span>
                                        </div>
                                        <div className="text-zinc-400 text-sm leading-relaxed">{m.description}</div>
                                        {m.reasoning && (
                                            <div className="mt-2 text-xs text-zinc-500 italic">Why: {m.reasoning}</div>
                                        )}
                                    </div>
                                    <div className="font-mono-ui text-sm" style={{ color: "#FBBF24" }}>+{m.xp_reward}</div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Recommendations */}
                <div className="space-y-4">
                    {/* Onboarding */}
                    <OnboardingWidget />

                    {/* Profile Completeness */}
                    <ProfileCompleteness />

                    {/* Top picks */}
                    <div className="card-soft p-6" data-testid="recommendations-panel">
                        <div className="overline">Decision Engine</div>
                        <h2 className="font-display font-bold text-2xl mt-1 mb-5">Top picks</h2>
                        <div className="space-y-3">
                            {recs.length === 0 && <div className="text-zinc-500 text-sm">No recommendations yet.</div>}
                            {recs.map((j) => (
                                <Link
                                    key={j.job_id}
                                    to={`/jobs/${j.job_id}`}
                                    data-testid={`rec-${j.job_id}`}
                                    className="block p-3 rounded-lg border border-zinc-800 hover:border-zinc-700 hover:bg-zinc-900/40 transition-all"
                                >
                                    <div className="flex items-start justify-between gap-3 mb-1">
                                        <div className="font-medium text-sm leading-tight">{j.title}</div>
                                        <div className="font-mono-ui text-sm" style={{ color: "#10B981" }}>
                                            {j.quick_score}
                                        </div>
                                    </div>
                                    <div className="text-xs text-zinc-500 mb-2">{j.company} • {j.location}</div>
                                    <div className="text-[11px] text-zinc-400 leading-relaxed">
                                        {j.decision?.reason}
                                    </div>
                                    <div className="mt-2 inline-flex items-center gap-1 text-[10px] font-mono-ui uppercase tracking-widest" style={{ color: j.decision?.decision === "apply" ? "#10B981" : j.decision?.decision === "consider" ? "#FBBF24" : "#71717A" }}>
                                        {j.decision?.decision} · conf {j.decision?.confidence}
                                    </div>
                                </Link>
                            ))}
                        </div>
                    </div>

                    {/* Activity Feed */}
                    <div className="card-soft p-5" data-testid="activity-panel">
                        <div className="overline mb-1">Recent Activity</div>
                        <h2 className="font-display font-bold text-lg mb-4">Your history</h2>
                        <ActivityFeed limit={8} />
                    </div>
                </div>
            </div>
        </div>
    );
}

function KPI({ label, value, suffix = "", color, Icon, testid }) {
    return (
        <div className="card-soft p-4" data-testid={testid}>
            <div className="flex items-center justify-between mb-2">
                <div className="overline">{label}</div>
                <Icon size={14} weight="duotone" color={color} />
            </div>
            <div className="font-mono-ui text-3xl font-medium" style={{ color }}>
                {value}
                <span className="text-sm text-zinc-500 ml-1">{suffix}</span>
            </div>
        </div>
    );
}
