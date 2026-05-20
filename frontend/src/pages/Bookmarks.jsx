import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { BookmarkSimple, MapPin, ArrowRight, Trash } from "@phosphor-icons/react";

export default function Bookmarks() {
    const [bookmarks, setBookmarks] = useState([]);
    const [loading, setLoading]     = useState(true);

    const load = async () => {
        try {
            const r = await api.get("/bookmarks");
            setBookmarks(r.data.bookmarks || []);
        } catch {}
        setLoading(false);
    };

    useEffect(() => { load(); }, []);

    const remove = async (jobId, e) => {
        e.preventDefault();
        e.stopPropagation();
        await api.delete(`/bookmarks/${jobId}`).catch(() => {});
        setBookmarks(bs => bs.filter(b => b.job_id !== jobId));
    };

    return (
        <div className="px-8 py-8 max-w-4xl mx-auto">
            <div className="mb-8">
                <div className="overline">Saved Jobs</div>
                <h1 className="font-display font-black text-4xl tracking-tight mt-2">Bookmarks</h1>
                <p className="text-zinc-500 text-sm mt-2">Jobs you've saved for later.</p>
            </div>

            {loading && (
                <div className="space-y-3">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="card-soft p-5 animate-pulse">
                            <div className="h-4 bg-zinc-800 rounded w-1/2 mb-2" />
                            <div className="h-3 bg-zinc-800 rounded w-1/3" />
                        </div>
                    ))}
                </div>
            )}

            {!loading && bookmarks.length === 0 && (
                <div className="text-center py-16 text-zinc-500">
                    <BookmarkSimple size={32} className="mx-auto mb-3 opacity-30" weight="duotone" />
                    <p className="text-sm mb-4">No saved jobs yet.</p>
                    <Link to="/jobs"
                        className="text-xs text-zinc-400 hover:text-zinc-200 transition-colors">
                        Browse jobs →
                    </Link>
                </div>
            )}

            <div className="space-y-3">
                {bookmarks.map(b => {
                    const j = b.job || {};
                    return (
                        <Link key={b.bookmark_id} to={`/jobs/${b.job_id}`}
                            className="card-soft p-5 flex items-start gap-4 group
                                       hover:border-zinc-700 transition-colors block">
                            <div className="flex-1 min-w-0">
                                <div className="flex items-start justify-between gap-3 mb-1">
                                    <h3 className="font-semibold text-base leading-tight truncate">
                                        {j.title || "Job"}
                                    </h3>
                                    {j.quick_score !== undefined && (
                                        <span className="font-mono-ui text-sm flex-shrink-0"
                                              style={{ color: "#10B981" }}>
                                            {j.quick_score}%
                                        </span>
                                    )}
                                </div>
                                <p className="text-sm text-zinc-400 mb-1">{j.company}</p>
                                {j.location && (
                                    <div className="flex items-center gap-1 text-xs text-zinc-500">
                                        <MapPin size={11} />
                                        {j.location}
                                    </div>
                                )}
                                {j.salary_range && (
                                    <p className="text-xs text-zinc-500 mt-1">{j.salary_range}</p>
                                )}
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                                <button onClick={e => remove(b.job_id, e)}
                                    className="p-2 rounded-lg text-zinc-600 hover:text-red-400
                                               hover:bg-red-400/10 transition-colors"
                                    title="Remove bookmark">
                                    <Trash size={14} />
                                </button>
                                <ArrowRight size={14} className="text-zinc-600 group-hover:text-zinc-300 transition-colors" />
                            </div>
                        </Link>
                    );
                })}
            </div>
        </div>
    );
}
