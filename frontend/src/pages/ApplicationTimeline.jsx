import { useState, useEffect } from "react";
import { api } from "../lib/api";
import { Link } from "react-router-dom";
import {
    CalendarBlank, Clock, CheckCircle, XCircle,
    ChatCircle, PhoneCall, Trophy, Circle
} from "@phosphor-icons/react";

const STATUS_META = {
    discovered:   { icon: Circle,       color: "#52525b", label: "Discovered"    },
    saved:        { icon: CalendarBlank, color: "#71717a", label: "Saved"         },
    applied:      { icon: CheckCircle,  color: "#3B82F6", label: "Applied"        },
    under_review: { icon: Clock,        color: "#8B5CF6", label: "Under Review"   },
    phone_screen: { icon: PhoneCall,    color: "#F59E0B", label: "Phone Screen"   },
    interview:    { icon: ChatCircle,   color: "#FBBF24", label: "Interview"      },
    offer:        { icon: Trophy,       color: "#10B981", label: "Offer"          },
    rejected:     { icon: XCircle,      color: "#EF4444", label: "Rejected"       },
    withdrawn:    { icon: XCircle,      color: "#71717a", label: "Withdrawn"      },
};

function daysBetween(a, b) {
    return Math.round(Math.abs(new Date(b) - new Date(a)) / 86400000);
}

function formatDate(iso) {
    return new Date(iso).toLocaleDateString(undefined, {
        month: "short", day: "numeric", year: "numeric",
    });
}

export default function ApplicationTimeline() {
    const [apps, setApps]       = useState([]);
    const [active, setActive]   = useState(null);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter]   = useState("all");

    useEffect(() => {
        api.get("/applications")
            .then(r => {
                const list = r.data.applications || r.data || [];
                setApps(list);
                if (list.length) setActive(list[0]);
            })
            .catch(() => {})
            .finally(() => setLoading(false));
    }, []);

    const FILTERS = ["all", "applied", "interview", "offer", "rejected"];
    const filtered = filter === "all"
        ? apps
        : apps.filter(a => a.status === filter);

    return (
        <div className="px-6 py-8 max-w-6xl mx-auto">
            <div className="mb-8">
                <div className="overline">Career OS</div>
                <h1 className="font-display font-black text-4xl tracking-tight mt-2">
                    Application Timeline
                </h1>
                <p className="text-zinc-500 text-sm mt-2">
                    Your full job search history, visualised.
                </p>
            </div>

            {/* Filter tabs */}
            <div className="flex gap-2 mb-6 flex-wrap">
                {FILTERS.map(f => (
                    <button key={f} onClick={() => setFilter(f)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors ${
                            filter === f
                                ? "bg-zinc-100 text-black"
                                : "bg-zinc-900 text-zinc-400 border border-zinc-800 hover:text-zinc-200"
                        }`}>
                        {f}
                        <span className="ml-1 text-zinc-500">
                            {f === "all"
                                ? apps.length
                                : apps.filter(a => a.status === f).length}
                        </span>
                    </button>
                ))}
            </div>

            {loading && (
                <div className="space-y-3">
                    {[...Array(5)].map((_, i) => (
                        <div key={i} className="h-16 bg-zinc-900 rounded-xl animate-pulse" />
                    ))}
                </div>
            )}

            {!loading && filtered.length === 0 && (
                <div className="text-center py-16 text-zinc-500">
                    <CalendarBlank size={28} className="mx-auto mb-3 opacity-30" weight="duotone" />
                    <p className="text-sm">No applications yet.</p>
                    <Link to="/jobs"
                        className="text-xs text-zinc-400 hover:text-zinc-200 mt-2 block transition-colors">
                        Browse jobs →
                    </Link>
                </div>
            )}

            <div className="grid lg:grid-cols-5 gap-6">
                {/* Left — Application list */}
                <div className="lg:col-span-2 space-y-2">
                    {filtered.map(app => {
                        const meta = STATUS_META[app.status] || STATUS_META.saved;
                        const IconComp = meta.icon;
                        const isActive = active?.application_id === app.application_id;

                        return (
                            <button key={app.application_id}
                                onClick={() => setActive(app)}
                                className={`w-full text-left px-4 py-3 rounded-xl border transition-all ${
                                    isActive
                                        ? "border-zinc-600 bg-zinc-800"
                                        : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-700"
                                }`}>
                                <div className="flex items-center gap-3">
                                    <IconComp size={15} weight="fill" color={meta.color}
                                        className="flex-shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-zinc-200 truncate">
                                            {app.job?.title || "Unknown role"}
                                        </p>
                                        <p className="text-xs text-zinc-500 truncate">
                                            {app.job?.company || ""}
                                        </p>
                                    </div>
                                    <span className="text-[10px] font-mono-ui flex-shrink-0"
                                          style={{ color: meta.color }}>
                                        {meta.label}
                                    </span>
                                </div>
                            </button>
                        );
                    })}
                </div>

                {/* Right — Timeline detail */}
                {active && (
                    <div className="lg:col-span-3 card-soft p-6">
                        {/* Job header */}
                        <div className="mb-6 pb-4 border-b border-zinc-800">
                            <Link to={`/jobs/${active.job_id}`}
                                className="text-blue-400 hover:text-blue-300 text-xs mb-1 block transition-colors">
                                View job details ↗
                            </Link>
                            <h2 className="font-display font-bold text-xl">
                                {active.job?.title || "Job"}
                            </h2>
                            <p className="text-zinc-400 text-sm mt-0.5">
                                {active.job?.company}
                                {active.job?.location && ` · ${active.job.location}`}
                            </p>
                        </div>

                        {/* Timeline events */}
                        <div className="relative">
                            {/* Vertical line */}
                            <div className="absolute left-4 top-2 bottom-2 w-px bg-zinc-800" />

                            <div className="space-y-5">
                                {(active.timeline || []).length > 0
                                    ? (active.timeline || []).map((event, i) => {
                                        const meta = STATUS_META[event.status] || STATUS_META.saved;
                                        const IconComp = meta.icon;
                                        const prev = active.timeline[i - 1];
                                        const dayDiff = prev
                                            ? daysBetween(prev.timestamp, event.timestamp)
                                            : null;

                                        return (
                                            <div key={i} className="flex gap-4 relative">
                                                {/* Icon dot */}
                                                <div className="w-8 h-8 rounded-full flex-shrink-0
                                                                flex items-center justify-center z-10"
                                                     style={{
                                                         background: `${meta.color}18`,
                                                         border: `2px solid ${meta.color}`,
                                                     }}>
                                                    <IconComp size={14} weight="fill"
                                                        color={meta.color} />
                                                </div>

                                                <div className="flex-1 min-w-0 pb-1">
                                                    <div className="flex items-center justify-between gap-2">
                                                        <p className="font-semibold text-sm"
                                                           style={{ color: meta.color }}>
                                                            {meta.label}
                                                        </p>
                                                        <div className="text-right flex-shrink-0">
                                                            <p className="text-xs text-zinc-400">
                                                                {formatDate(event.timestamp)}
                                                            </p>
                                                            {dayDiff !== null && dayDiff > 0 && (
                                                                <p className="text-[10px] text-zinc-600">
                                                                    +{dayDiff}d
                                                                </p>
                                                            )}
                                                        </div>
                                                    </div>
                                                    {event.reason && (
                                                        <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
                                                            {event.reason}
                                                        </p>
                                                    )}
                                                </div>
                                            </div>
                                        );
                                    })
                                    : (
                                        <div className="flex gap-4">
                                            <div className="w-8 h-8 rounded-full flex-shrink-0
                                                            flex items-center justify-center"
                                                 style={{
                                                     background: "#3B82F618",
                                                     border: "2px solid #3B82F6",
                                                 }}>
                                                <Circle size={14} weight="fill" color="#3B82F6" />
                                            </div>
                                            <div>
                                                <p className="font-semibold text-sm text-blue-400">
                                                    Application created
                                                </p>
                                                <p className="text-xs text-zinc-500 mt-0.5">
                                                    {formatDate(active.created_at)}
                                                </p>
                                            </div>
                                        </div>
                                    )
                                }
                            </div>
                        </div>

                        {/* Duration summary */}
                        {active.timeline?.length > 1 && (
                            <div className="mt-6 pt-4 border-t border-zinc-800 flex gap-6">
                                <div>
                                    <p className="text-xs text-zinc-500">Total duration</p>
                                    <p className="font-mono-ui font-bold text-lg">
                                        {daysBetween(
                                            active.timeline[0].timestamp,
                                            active.timeline[active.timeline.length - 1].timestamp
                                        )}d
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs text-zinc-500">Current stage</p>
                                    <p className="font-semibold text-sm capitalize"
                                       style={{ color: STATUS_META[active.status]?.color }}>
                                        {STATUS_META[active.status]?.label || active.status}
                                    </p>
                                </div>
                                {active.notes && (
                                    <div className="flex-1">
                                        <p className="text-xs text-zinc-500">Notes</p>
                                        <p className="text-xs text-zinc-400 leading-relaxed line-clamp-2">
                                            {active.notes}
                                        </p>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
