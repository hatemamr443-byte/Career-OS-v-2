import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Link } from "react-router-dom";
import { MagnifyingGlass, MapPin, Briefcase, ArrowRight } from "@phosphor-icons/react";

export default function Jobs() {
    const [jobs, setJobs] = useState([]);
    const [q, setQ] = useState("");
    const [remoteOnly, setRemoteOnly] = useState(false);
    const [loading, setLoading] = useState(true);

    const load = async () => {
        setLoading(true);
        try {
            const r = await api.get(`/jobs`, { params: { q: q || undefined, remote_only: remoteOnly } });
            setJobs(r.data.jobs || []);
        } catch {}
        setLoading(false);
    };

    useEffect(() => { load(); /* eslint-disable-next-line */ }, [remoteOnly]);

    return (
        <div className="px-8 py-8 max-w-7xl mx-auto" data-testid="jobs-page">
            <div className="flex items-end justify-between mb-6 flex-wrap gap-4">
                <div>
                    <div className="overline">Jobs</div>
                    <h1 className="font-display font-black text-4xl tracking-tight mt-2">Smart Recommendations</h1>
                    <p className="text-zinc-500 mt-2 text-sm">Ranked by your skill profile. Click any job for full match analysis.</p>
                </div>
            </div>

            <div className="flex items-center gap-3 mb-6 flex-wrap">
                <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 flex-1 min-w-[260px]">
                    <MagnifyingGlass size={16} className="text-zinc-500" />
                    <input
                        value={q}
                        onChange={(e) => setQ(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && load()}
                        placeholder="Search title, company, or stack…"
                        className="bg-transparent flex-1 text-sm focus:outline-none"
                        data-testid="jobs-search-input"
                    />
                </div>
                <button
                    onClick={() => setRemoteOnly((v) => !v)}
                    data-testid="filter-remote-btn"
                    className={`px-4 py-2 rounded-lg text-sm border transition-colors ${
                        remoteOnly
                            ? "bg-zinc-50 text-black border-zinc-50"
                            : "border-zinc-800 text-zinc-300 hover:border-zinc-700"
                    }`}
                >
                    Remote only
                </button>
                <button
                    onClick={load}
                    data-testid="jobs-search-btn"
                    className="bg-zinc-900 border border-zinc-800 hover:border-zinc-700 px-4 py-2 rounded-lg text-sm"
                >
                    Search
                </button>
            </div>

            {loading ? (
                <div className="text-zinc-500 text-sm">Scanning the market…</div>
            ) : (
                <div className="grid md:grid-cols-2 gap-4" data-testid="jobs-grid">
                    {jobs.map((j) => (
                        <Link
                            key={j.job_id}
                            to={`/jobs/${j.job_id}`}
                            data-testid={`job-card-${j.job_id}`}
                            className="card-soft p-5 group"
                        >
                            <div className="flex items-start justify-between gap-3 mb-3">
                                <div>
                                    <div className="text-[10px] font-mono-ui uppercase tracking-widest text-zinc-500">{j.company}</div>
                                    <div className="font-display font-bold text-xl mt-1 leading-tight tracking-tight">{j.title}</div>
                                </div>
                                <div className="text-right">
                                    <div className="font-mono-ui text-3xl" style={{ color: scoreColor(j.quick_score) }}>{j.quick_score}</div>
                                    <div className="overline">match</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3 text-xs text-zinc-500 flex-wrap">
                                <span className="flex items-center gap-1"><MapPin size={12} />{j.location}</span>
                                <span className="flex items-center gap-1"><Briefcase size={12} />{j.seniority}</span>
                                {j.salary_range && <span className="text-zinc-400">{j.salary_range}</span>}
                            </div>
                            <p className="text-sm text-zinc-400 mt-3 leading-relaxed line-clamp-2">{j.description}</p>
                            <div className="mt-4 flex flex-wrap gap-1.5">
                                {(j.skills_required || []).slice(0, 5).map((s) => (
                                    <span key={s} className="text-[10px] font-mono-ui px-2 py-0.5 bg-zinc-900 border border-zinc-800 rounded text-zinc-400">{s}</span>
                                ))}
                            </div>
                            <div className="mt-4 flex items-center justify-end text-xs text-zinc-400 group-hover:text-zinc-100 transition-colors">
                                Open analysis <ArrowRight size={12} className="ml-1" />
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}

function scoreColor(s) {
    if (s >= 70) return "#10B981";
    if (s >= 40) return "#FBBF24";
    return "#71717A";
}
