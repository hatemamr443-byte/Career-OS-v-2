import { useState, useEffect } from "react";
import { api } from "../lib/api";
import { ArrowLeft, ClipboardText } from "@phosphor-icons/react";
import { Link } from "react-router-dom";

export default function CVVersions() {
    const [versions, setVersions] = useState([]);
    const [left, setLeft]         = useState(null);
    const [right, setRight]       = useState(null);
    const [loading, setLoading]   = useState(true);

    useEffect(() => {
        api.get("/cv/versions")
            .then(r => {
                const v = r.data.versions || [];
                setVersions(v);
                if (v.length >= 1) setLeft(v[0]);
                if (v.length >= 2) setRight(v[1]);
            })
            .catch(() => {})
            .finally(() => setLoading(false));
    }, []);

    const loadFull = async (ver, side) => {
        try {
            const r = await api.get(`/cv/versions/${ver.version_id}`);
            side === "left" ? setLeft(r.data) : setRight(r.data);
        } catch {}
    };

    const copy = (text) => navigator.clipboard.writeText(text || "");

    if (loading) return (
        <div className="px-6 py-8 max-w-7xl mx-auto">
            <div className="h-6 bg-zinc-800 rounded w-48 animate-pulse mb-4" />
            <div className="h-96 bg-zinc-800 rounded animate-pulse" />
        </div>
    );

    return (
        <div className="px-6 py-8 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex items-center gap-3 mb-8">
                <Link to="/cv-tailor"
                    className="text-zinc-500 hover:text-zinc-200 transition-colors">
                    <ArrowLeft size={18} />
                </Link>
                <div>
                    <div className="overline">CV Intelligence</div>
                    <h1 className="font-display font-black text-3xl tracking-tight">
                        Version Compare
                    </h1>
                </div>
            </div>

            {versions.length === 0 && (
                <div className="text-center py-20 text-zinc-500">
                    <p className="text-sm mb-3">No saved CV versions yet.</p>
                    <Link to="/cv-tailor"
                        className="text-xs text-zinc-400 hover:text-zinc-200 transition-colors">
                        Create your first tailored CV →
                    </Link>
                </div>
            )}

            {versions.length > 0 && (
                <>
                    {/* Version selectors */}
                    <div className="grid md:grid-cols-2 gap-4 mb-6">
                        {[
                            { label: "Version A", current: left,  side: "left"  },
                            { label: "Version B", current: right, side: "right" },
                        ].map(({ label, current, side }) => (
                            <div key={side}>
                                <label className="overline mb-2 block">{label}</label>
                                <select
                                    value={current?.version_id || ""}
                                    onChange={e => {
                                        const v = versions.find(x => x.version_id === e.target.value);
                                        if (v) loadFull(v, side);
                                    }}
                                    className="w-full px-3 py-2.5 bg-zinc-900 border border-zinc-800
                                               rounded-lg text-sm text-zinc-200
                                               focus:outline-none focus:border-zinc-700"
                                >
                                    <option value="">Select version…</option>
                                    {versions.map(v => (
                                        <option key={v.version_id} value={v.version_id}>
                                            {v.job_title || "Untitled"} — {v.job_company || ""}
                                            {" "}({new Date(v.created_at).toLocaleDateString()})
                                        </option>
                                    ))}
                                </select>
                            </div>
                        ))}
                    </div>

                    {/* Side-by-side diff view */}
                    {(left || right) && (
                        <div className="grid md:grid-cols-2 gap-4">
                            {[
                                { ver: left,  label: "Version A", color: "#3B82F6" },
                                { ver: right, label: "Version B", color: "#10B981" },
                            ].map(({ ver, label, color }) => (
                                <div key={label} className="card-soft overflow-hidden">
                                    {/* Header */}
                                    <div className="flex items-center justify-between px-4 py-3
                                                    border-b border-zinc-800"
                                         style={{ borderLeftColor: color, borderLeftWidth: 3 }}>
                                        <div>
                                            <p className="text-xs font-semibold" style={{ color }}>
                                                {label}
                                            </p>
                                            {ver && (
                                                <p className="text-xs text-zinc-500 mt-0.5">
                                                    {ver.job_title || "Untitled"}
                                                    {ver.job_company ? ` — ${ver.job_company}` : ""}
                                                </p>
                                            )}
                                        </div>
                                        {ver?.tailored_cv && (
                                            <button
                                                onClick={() => copy(ver.tailored_cv)}
                                                className="flex items-center gap-1 text-xs text-zinc-400
                                                           hover:text-zinc-200 transition-colors"
                                            >
                                                <ClipboardText size={13} /> Copy
                                            </button>
                                        )}
                                    </div>

                                    {/* CV text */}
                                    {ver?.tailored_cv ? (
                                        <pre className="text-xs text-zinc-300 whitespace-pre-wrap
                                                        leading-relaxed p-4 max-h-[520px]
                                                        overflow-y-auto bg-zinc-950">
                                            {ver.tailored_cv}
                                        </pre>
                                    ) : (
                                        <div className="h-40 flex items-center justify-center
                                                        text-zinc-600 text-sm">
                                            Select a version above
                                        </div>
                                    )}

                                    {/* Keywords added */}
                                    {ver?.keywords_added?.length > 0 && (
                                        <div className="px-4 py-3 border-t border-zinc-800 bg-zinc-900/50">
                                            <p className="text-xs text-zinc-500 mb-1.5">
                                                Keywords added ({ver.keywords_added.length})
                                            </p>
                                            <div className="flex flex-wrap gap-1">
                                                {ver.keywords_added.slice(0, 12).map((k, i) => (
                                                    <span key={i}
                                                        className="text-[10px] px-1.5 py-0.5 rounded"
                                                        style={{
                                                            background: `${color}18`,
                                                            border: `1px solid ${color}30`,
                                                            color,
                                                        }}>
                                                        {k}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Changes comparison */}
                    {left?.changes_made?.length > 0 && right?.changes_made?.length > 0 && (
                        <div className="mt-6 card-soft p-5">
                            <h3 className="font-display font-bold mb-4">Changes Comparison</h3>
                            <div className="grid md:grid-cols-2 gap-4">
                                {[
                                    { ver: left,  color: "#3B82F6", label: "A" },
                                    { ver: right, color: "#10B981", label: "B" },
                                ].map(({ ver, color, label }) => (
                                    <div key={label}>
                                        <p className="text-xs font-semibold mb-2"
                                           style={{ color }}>
                                            Version {label} changes
                                        </p>
                                        <ul className="space-y-1">
                                            {(ver.changes_made || []).map((c, i) => (
                                                <li key={i} className="text-xs text-zinc-400
                                                                        flex gap-2">
                                                    <span style={{ color }}>•</span>{c}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
