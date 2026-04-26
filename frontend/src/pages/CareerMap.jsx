import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function CareerMap() {
    const [apps, setApps] = useState([]);
    useEffect(() => {
        api.get("/applications").then((r) => setApps(r.data.applications || [])).catch(() => {});
    }, []);

    const STATUS_FLOW = ["discovered", "applied", "under_review", "interview", "offer", "rejected"];
    const buckets = STATUS_FLOW.reduce((acc, s) => ({ ...acc, [s]: apps.filter((a) => a.status === s) }), {});

    return (
        <div className="px-8 py-8 max-w-7xl mx-auto" data-testid="career-map-page">
            <div className="overline">Identity Graph</div>
            <h1 className="font-display font-black text-4xl mt-2 mb-2 tracking-tight">Career Map</h1>
            <p className="text-zinc-500 text-sm mb-8">Every opportunity in motion. Drag your eye across the funnel.</p>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 dot-grid p-4 rounded-xl border border-zinc-900">
                {STATUS_FLOW.map((s) => (
                    <div key={s} className="space-y-2">
                        <div className="overline px-2">{s.replace(/_/g, " ")}</div>
                        <div className="space-y-2 min-h-[60px]" data-testid={`column-${s}`}>
                            {(buckets[s] || []).map((a) => (
                                <div key={a.application_id} className="card-soft p-3 cursor-pointer hover:border-zinc-700">
                                    <div className="text-[10px] font-mono-ui uppercase tracking-widest text-zinc-500 truncate">{a.job?.company}</div>
                                    <div className="text-sm font-medium leading-tight mt-1 line-clamp-2">{a.job?.title}</div>
                                    <div className="mt-2 text-[11px] text-zinc-500">{a.job?.location}</div>
                                </div>
                            ))}
                            {(buckets[s] || []).length === 0 && (
                                <div className="text-[11px] text-zinc-700 italic px-2">empty</div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
