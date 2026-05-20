import React, { useEffect, useState, useCallback, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import { ArrowLeft, MapPin, Briefcase, CheckCircle, XCircle, Warning, Sparkle, Circle } from "@phosphor-icons/react";
import UsageBanner from "../components/UsageBanner";

const STATUS_FLOW = ["discovered", "applied", "under_review", "interview", "offer"];
const STATUS_LABEL = {
    discovered: "Discovered",
    applied: "Applied",
    under_review: "Under Review",
    interview: "Interview",
    offer: "Offer",
    rejected: "Rejected",
};

export default function JobDetail() {
    const { id } = useParams();
    const [data, setData] = useState(null);
    const [match, setMatch] = useState(null);
    const [analyzing, setAnalyzing] = useState(false);
    const [applying, setApplying] = useState(false);
    const [quotaError, setQuotaError] = useState(null);

    const load = useCallback(async () => {
        const r = await api.get(`/jobs/${id}`);
        setData(r.data);
        if (r.data.application?.match) setMatch(r.data.application.match);
    }, [id]);

    useEffect(() => {
        load();
    }, [load]);

    const runMatch = async () => {
        setAnalyzing(true);
        setQuotaError(null);
        try {
            const r = await api.post(`/jobs/${id}/match`);
            setMatch(r.data);
        } catch (err) {
            if (err.response?.status === 403 && err.response.data?.detail?.code === "quota_exceeded") {
                setQuotaError(err.response.data.detail);
            } else {
                console.error("match failed:", err);
            }
        }
        setAnalyzing(false);
    };

    const apply = async () => {
        setApplying(true);
        try {
            await api.post(`/applications`, { job_id: id, match });
            await load();
        } catch (err) {
            console.error("apply failed:", err);
        }
        setApplying(false);
    };

    const updateStatus = async (newStatus) => {
        if (!data?.application) return;
        await api.patch(`/applications/${data.application.application_id}`, {
            status: newStatus,
            reason: `Marked as ${newStatus} by user`,
        });
        load();
    };

    if (!data) return <div className="p-8 text-zinc-500">Loading…</div>;
    const { job, application } = data;

    return (
        <div className="px-8 py-8 max-w-6xl mx-auto" data-testid="job-detail-page">
            <UsageBanner context="job-detail" />
            <Link to="/jobs" className="inline-flex items-center gap-2 text-sm text-zinc-500 hover:text-zinc-100 mb-6" data-testid="back-to-jobs">
                <ArrowLeft size={14} /> All jobs
            </Link>

            <div className="grid lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-6">
                    {/* Header card */}
                    <div className="card-soft p-6">
                        <div className="overline">{job.company}</div>
                        <h1 className="font-display font-black text-3xl mt-2 tracking-tight">{job.title}</h1>
                        <div className="flex items-center gap-3 text-sm text-zinc-500 mt-3 flex-wrap">
                            <span className="flex items-center gap-1"><MapPin size={14} />{job.location}</span>
                            <span className="flex items-center gap-1"><Briefcase size={14} />{job.seniority}</span>
                            {job.salary_range && <span className="text-zinc-300">{job.salary_range}</span>}
                            {job.remote && <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded font-mono-ui text-[10px] uppercase tracking-widest">Remote</span>}
                        </div>
                        <p className="text-zinc-300 mt-5 leading-relaxed whitespace-pre-line">{job.description}</p>
                        <div className="mt-5 flex flex-wrap gap-2">
                            {(job.skills_required || []).map((s) => (
                                <span key={s} className="text-xs font-mono-ui px-2 py-1 bg-zinc-900 border border-zinc-800 rounded text-zinc-300">{s}</span>
                            ))}
                        </div>
                    </div>

                    {/* Match analysis */}
                    <div className="card-soft p-6" data-testid="match-panel">
                        <div className="flex items-center justify-between mb-4">
                            <div>
                                <div className="overline">Decision Layer</div>
                                <h2 className="font-display font-bold text-2xl mt-1">AI Match Analysis</h2>
                            </div>
                            {!match && (
                                <button
                                    onClick={runMatch}
                                    disabled={analyzing}
                                    data-testid="run-match-btn"
                                    className="bg-blue-600/10 text-blue-400 border border-blue-500/20 hover:bg-blue-600/20 transition-colors rounded-lg px-4 py-2 text-sm flex items-center gap-2"
                                >
                                    <Sparkle size={14} weight="fill" />
                                    {analyzing ? "Analyzing…" : "Run AI analysis"}
                                </button>
                            )}
                        </div>

                        {quotaError && (
                            <div className="mb-4 p-4 rounded-lg bg-orange-500/10 border border-orange-500/30" data-testid="quota-error">
                                <div className="flex items-start gap-3">
                                    <Warning size={18} weight="fill" color="#FF5C00" className="mt-0.5 flex-shrink-0" />
                                    <div className="flex-1">
                                        <div className="font-display font-bold text-base tracking-tight">Out of free matches</div>
                                        <div className="text-sm text-zinc-400 mt-1">{quotaError.message}</div>
                                    </div>
                                    <Link
                                        to="/pricing"
                                        data-testid="quota-upgrade-link"
                                        className="bg-zinc-50 text-black hover:bg-zinc-200 transition-colors rounded-lg px-4 py-2 text-sm font-medium flex-shrink-0"
                                    >
                                        Upgrade →
                                    </Link>
                                </div>
                            </div>
                        )}

                        {!match ? (
                            <div className="text-zinc-500 text-sm">
                                Quick skill match: <span className="font-mono-ui text-zinc-300">{job.quick_score}%</span>.
                                Run full AI analysis for reasoning, gaps, and decision.
                            </div>
                        ) : (
                            <div>
                                <div className="grid grid-cols-3 gap-4 mb-5">
                                    <Stat label="Match Score" value={match.score} color="#10B981" />
                                    <Stat label="Confidence" value={match.confidence} color="#007AFF" />
                                    <DecisionStat decision={match.decision} />
                                </div>
                                <div className="text-zinc-300 leading-relaxed mb-4">{match.reasoning}</div>

                                <div className="grid sm:grid-cols-2 gap-4">
                                    <div>
                                        <div className="overline mb-2 flex items-center gap-1"><CheckCircle size={12} weight="fill" color="#10B981" /> Strengths</div>
                                        <ul className="space-y-1">
                                            {(match.strengths || []).map((s, i) => (
                                            <li key={`str-${s}-${i}`} className="text-sm text-zinc-300 flex gap-2"><span style={{ color: "#10B981" }}>+</span>{s}</li>
                                        ))}
                                        </ul>
                                    </div>
                                    <div>
                                        <div className="overline mb-2 flex items-center gap-1"><Warning size={12} weight="fill" color="#FBBF24" /> Gaps</div>
                                        <ul className="space-y-1">
                                            {(match.gaps || []).map((s, i) => (
                                            <li key={`gap-${s}-${i}`} className="text-sm text-zinc-300 flex gap-2"><span style={{ color: "#FBBF24" }}>!</span>{s}</li>
                                        ))}
                                        </ul>
                                    </div>
                                </div>

                                {match.expected_outcome && (
                                    <div className="mt-5 p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-sm text-zinc-400">
                                        <span className="overline mr-2">Expected outcome</span>{match.expected_outcome}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* Right column: actions + timeline */}
                <div className="space-y-4">
                    <div className="card-soft p-5">
                        <div className="overline mb-3">Actions</div>
                        {!application ? (
                            <button
                                onClick={apply}
                                disabled={applying}
                                data-testid="apply-btn"
                                className="w-full bg-zinc-50 text-black hover:bg-zinc-200 transition-colors rounded-lg px-4 py-3 font-medium"
                            >
                                {applying ? "Submitting…" : "Track this application"}
                            </button>
                        ) : (
                            <div>
                                <div className="text-xs text-zinc-500 mb-2">Status</div>
                                <select
                                    value={application.status}
                                    onChange={(e) => updateStatus(e.target.value)}
                                    data-testid="status-select"
                                    className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm"
                                >
                                    {Object.entries(STATUS_LABEL).map(([k, v]) => (
                                        <option key={k} value={k}>{v}</option>
                                    ))}
                                </select>
                            </div>
                        )}
                    </div>

                    {application && (
                        <div className="card-soft p-5" data-testid="timeline-panel">
                            <div className="overline mb-3">Lifecycle</div>
                            <div className="space-y-3">
                                {(application.timeline || []).map((t, i) => (
                                    <div key={`${t.status}-${t.timestamp}-${i}`} className="flex gap-3">
                                        <div className="mt-0.5">
                                            {t.status === "rejected" ? (
                                                <XCircle size={16} weight="fill" color="#EF4444" />
                                            ) : t.status === "offer" ? (
                                                <CheckCircle size={16} weight="fill" color="#10B981" />
                                            ) : (
                                                <Circle size={16} weight="fill" color="#FBBF24" />
                                            )}
                                        </div>
                                        <div className="flex-1">
                                            <div className="text-sm font-medium">{STATUS_LABEL[t.status] || t.status}</div>
                                            <div className="text-xs text-zinc-500">{new Date(t.timestamp).toLocaleString()}</div>
                                            <div className="text-xs text-zinc-400 mt-1">{t.reason}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Notes Autosave */}
                    {application && <NotesPanel applicationId={application.application_id} initial={application.notes} />}
                </div>
            </div>
        </div>
    );
}

function NotesPanel({ applicationId, initial }) {
    const [notes, setNotes] = useState(initial || "");
    const [saved, setSaved] = useState(true);
    const timerRef = React.useRef(null);

    const handleChange = (val) => {
        setNotes(val);
        setSaved(false);
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(async () => {
            try {
                await api.patch(`/applications/${applicationId}/notes`, { notes: val });
                setSaved(true);
            } catch {}
        }, 1000);
    };

    return (
        <div className="card-soft p-5" data-testid="notes-panel">
            <div className="flex items-center justify-between mb-3">
                <div className="overline">Notes</div>
                <span className="text-xs text-zinc-600">
                    {saved ? "Saved ✓" : "Saving…"}
                </span>
            </div>
            <textarea
                value={notes}
                onChange={e => handleChange(e.target.value)}
                placeholder="Add notes about this application…"
                className="w-full h-28 bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3
                           text-sm text-zinc-200 placeholder:text-zinc-600 resize-none
                           focus:outline-none focus:border-zinc-700 transition-colors"
            />
        </div>
    );
}

function Stat({ label, value, color }) {
    return (
        <div className="p-3 bg-zinc-900/40 border border-zinc-800 rounded-lg">
            <div className="overline mb-1">{label}</div>
            <div className="font-mono-ui text-2xl" style={{ color }}>{value}</div>
        </div>
    );
}

function DecisionStat({ decision }) {
    const map = {
        apply: { c: "#10B981", l: "Apply" },
        consider: { c: "#FBBF24", l: "Consider" },
        skip: { c: "#71717A", l: "Skip" },
    };
    const cfg = map[decision] || map.consider;
    return (
        <div className="p-3 bg-zinc-900/40 border border-zinc-800 rounded-lg">
            <div className="overline mb-1">Decision</div>
            <div className="font-display font-black text-xl uppercase" style={{ color: cfg.c }}>{cfg.l}</div>
        </div>
    );
}
