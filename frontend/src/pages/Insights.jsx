import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function Insights() {
    const [data, setData] = useState(null);
    useEffect(() => {
        let cancelled = false;
        api
            .get("/insights")
            .then((r) => {
                if (!cancelled) setData(r.data);
            })
            .catch((err) => console.error("insights load failed:", err));
        return () => {
            cancelled = true;
        };
    }, []);

    if (!data) return <div className="p-8 text-zinc-500">Loading…</div>;
    const t = data.totals;
    const r = data.rates;

    return (
        <div className="px-8 py-8 max-w-6xl mx-auto" data-testid="insights-page">
            <div className="overline">Performance Layer</div>
            <h1 className="font-display font-black text-4xl mt-2 mb-8 tracking-tight">Career Insights</h1>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                <Card label="Applications" value={t.applied + t.under_review + t.interview + t.offer + t.rejected} color="#FAFAFA" />
                <Card label="Interview Rate" value={`${r.interview_rate}%`} color="#007AFF" />
                <Card label="Offer Rate" value={`${r.success_rate}%`} color="#10B981" />
                <Card label="Rejection Rate" value={`${r.rejection_rate}%`} color="#EF4444" />
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
                <div className="card-soft p-6">
                    <div className="overline">Funnel</div>
                    <h3 className="font-display font-bold text-2xl mt-1 mb-5">Pipeline conversion</h3>
                    <div className="space-y-3" data-testid="funnel-chart">
                        {data.funnel.map((s, i) => {
                            const max = data.funnel[0].count || 1;
                            const pct = (s.count / max) * 100;
                            return (
                                <div key={s.stage}>
                                    <div className="flex justify-between mb-1 text-sm">
                                        <span className="text-zinc-300">{s.stage}</span>
                                        <span className="font-mono-ui text-zinc-500">{s.count}</span>
                                    </div>
                                    <div className="h-2 bg-zinc-900 rounded-full overflow-hidden">
                                        <div className="h-full transition-all" style={{ width: `${pct}%`, background: ["#FAFAFA", "#FBBF24", "#007AFF", "#10B981"][i] }} />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                <div className="card-soft p-6">
                    <div className="overline">Pattern Detection</div>
                    <h3 className="font-display font-bold text-2xl mt-1 mb-5">Rejections by seniority</h3>
                    <div className="space-y-3">
                        {Object.entries(data.rejection_pattern_by_seniority).map(([k, v]) => {
                            const total = Object.values(data.rejection_pattern_by_seniority).reduce((a, b) => a + b, 0);
                            const pct = total ? (v / total) * 100 : 0;
                            return (
                                <div key={k}>
                                    <div className="flex justify-between mb-1 text-sm">
                                        <span className="text-zinc-300 capitalize">{k}</span>
                                        <span className="font-mono-ui text-zinc-500">{v}</span>
                                    </div>
                                    <div className="h-2 bg-zinc-900 rounded-full overflow-hidden">
                                        <div className="h-full" style={{ width: `${pct}%`, background: "#EF4444" }} />
                                    </div>
                                </div>
                            );
                        })}
                        {Object.values(data.rejection_pattern_by_seniority).every((v) => v === 0) && (
                            <div className="text-zinc-500 text-sm">No rejections detected — keep going.</div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

function Card({ label, value, color }) {
    return (
        <div className="card-soft p-4">
            <div className="overline">{label}</div>
            <div className="font-mono-ui text-3xl mt-2" style={{ color }}>{value}</div>
        </div>
    );
}
