import { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { Link } from "react-router-dom";
import { MagnifyingGlass, MapPin, Briefcase, ArrowRight, CaretLeft, CaretRight, BookmarkSimple } from "@phosphor-icons/react";
import UsageBanner from "../components/UsageBanner";

export default function Jobs() {
    const [jobs, setJobs] = useState([]);
    const [q, setQ] = useState("");
    const [remoteOnly, setRemoteOnly] = useState(false);
    const [loading, setLoading] = useState(true);
    const [ingesting, setIngesting] = useState(false);
    const [ingestResult, setIngestResult] = useState(null);
    const [page, setPage] = useState(1);
    const [pagination, setPagination] = useState(null);
    const [bookmarked, setBookmarked] = useState(new Set());

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const r = await api.get(`/jobs`, { params: { q: q || undefined, remote_only: remoteOnly, page, size: 20 } });
            setJobs(r.data.jobs || []);
            setPagination(r.data.pagination || null);
        } catch (err) {
            console.error("jobs load failed:", err);
        }
        setLoading(false);
    }, [q, remoteOnly, page]);

    const ingest = async () => {
        setIngesting(true);
        setIngestResult(null);
        try {
            const r = await api.post("/jobs/ingest", { query: q || "engineering", limit: 15 });
            setIngestResult(r.data);
            setPage(1);
            await load();
        } catch (err) {
            console.error("ingest failed:", err);
            setIngestResult({ error: err.response?.data?.detail || "Ingest failed" });
        }
        setIngesting(false);
    };

    const toggleBookmark = async (jobId, e) => {
        e.preventDefault();
        try {
            if (bookmarked.has(jobId)) {
                await api.delete(`/bookmarks/${jobId}`);
                setBookmarked(b => { const n = new Set(b); n.delete(jobId); return n; });
            } else {
                await api.post(`/bookmarks/${jobId}`);
                setBookmarked(b => new Set([...b, jobId]));
            }
        } catch {}
    };

    useEffect(() => {
        load();
    }, [remoteOnly, page, load]);

    // Reset page on search
    const handleSearch = (e) => {
        e.preventDefault();
        setPage(1);
        load();
    };

    return (
        <div className="px-8 py-8 max-w-7xl mx-auto" data-testid="jobs-page">
            <UsageBanner context="jobs" />
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
                <button
                    onClick={ingest}
                    disabled={ingesting}
                    data-testid="jobs-ingest-btn"
                    className="bg-blue-600/10 text-blue-400 border border-blue-500/20 hover:bg-blue-600/20 transition-colors rounded-lg px-4 py-2 text-sm disabled:opacity-50"
                >
                    {ingesting ? "Pulling…" : "Pull fresh jobs"}
                </button>
            </div>

            {ingestResult && !ingestResult.error && ingestResult.by_source && (
                <div className="mb-6 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-sm" data-testid="ingest-result">
                    <span className="font-mono-ui text-emerald-400">+{ingestResult.total_inserted}</span>
                    <span className="text-zinc-400 ml-2">new jobs from </span>
                    {Object.entries(ingestResult.by_source).map(([src, stats], i, arr) => (
                        <span key={src} className="text-zinc-300">
                            {src.replace("_", " ")} <span className="text-zinc-500 font-mono-ui">({stats.inserted}/{stats.fetched})</span>
                            {i < arr.length - 1 ? ", " : ""}
                        </span>
                    ))}
                </div>
            )}

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
                                    <div className="text-[10px] font-mono-ui uppercase tracking-widest text-zinc-500 flex items-center gap-2">
                                        {j.company}
                                        {j.source && j.source !== "mock" && (
                                            <span className="px-1.5 py-0.5 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded text-[9px]" data-testid={`source-badge-${j.source}`}>
                                                live · {j.source}
                                            </span>
                                        )}
                                    </div>
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
                            <div className="mt-4 flex items-center justify-between">
                                <button
                                    onClick={(e) => toggleBookmark(j.job_id, e)}
                                    className={`flex items-center gap-1 text-xs transition-colors ${bookmarked.has(j.job_id) ? "text-yellow-400" : "text-zinc-600 hover:text-zinc-300"}`}
                                    title={bookmarked.has(j.job_id) ? "Remove bookmark" : "Bookmark"}
                                >
                                    <BookmarkSimple size={14} weight={bookmarked.has(j.job_id) ? "fill" : "regular"} />
                                    {bookmarked.has(j.job_id) ? "Saved" : "Save"}
                                </button>
                                <div className="flex items-center text-xs text-zinc-400 group-hover:text-zinc-100 transition-colors">
                                    Open analysis <ArrowRight size={12} className="ml-1" />
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}

            {/* Pagination */}
            {pagination && pagination.pages > 1 && (
                <div className="flex items-center justify-center gap-2 mt-8 pb-8">
                    <button
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={!pagination.has_prev}
                        className="w-8 h-8 flex items-center justify-center rounded-lg border border-zinc-800 text-zinc-400 hover:text-zinc-100 hover:border-zinc-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                        <CaretLeft size={14} />
                    </button>

                    <div className="flex items-center gap-1">
                        {Array.from({ length: Math.min(pagination.pages, 7) }, (_, i) => {
                            const p = i + 1;
                            return (
                                <button
                                    key={p}
                                    onClick={() => setPage(p)}
                                    className={`w-8 h-8 rounded-lg font-mono-ui text-sm transition-colors ${
                                        p === page
                                            ? "bg-zinc-50 text-black font-medium"
                                            : "text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800"
                                    }`}
                                >
                                    {p}
                                </button>
                            );
                        })}
                        {pagination.pages > 7 && (
                            <span className="text-zinc-600 text-sm px-2">… {pagination.pages}</span>
                        )}
                    </div>

                    <button
                        onClick={() => setPage(p => Math.min(pagination.pages, p + 1))}
                        disabled={!pagination.has_next}
                        className="w-8 h-8 flex items-center justify-center rounded-lg border border-zinc-800 text-zinc-400 hover:text-zinc-100 hover:border-zinc-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                        <CaretRight size={14} />
                    </button>
                </div>
            )}
            {pagination && (
                <p className="text-center text-xs text-zinc-600 pb-4">
                    {pagination.total} jobs · page {pagination.page} of {pagination.pages}
                </p>
            )}
        </div>
    );
}

function scoreColor(s) {
    if (s >= 70) return "#10B981";
    if (s >= 40) return "#FBBF24";
    return "#71717A";
}
