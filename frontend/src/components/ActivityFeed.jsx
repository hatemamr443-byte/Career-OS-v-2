import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { CheckCircle, FileText, User, Flame, Star, Bell } from "@phosphor-icons/react";

const EVENT_META = {
    job_applied:    { icon: FileText,     color: "#10B981", label: "Applied"   },
    job_saved:      { icon: Star,         color: "#FBBF24", label: "Saved"     },
    status_changed: { icon: CheckCircle,  color: "#3B82F6", label: "Updated"   },
    profile_updated:{ icon: User,         color: "#8B5CF6", label: "Profile"   },
    onboarding_step:{ icon: Star,         color: "#F59E0B", label: "Progress"  },
    streak_reward:  { icon: Flame,        color: "#FF5C00", label: "Streak"    },
};

function timeAgo(iso) {
    const secs = Math.floor((Date.now() - new Date(iso)) / 1000);
    if (secs < 60)   return "just now";
    if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
    if (secs < 86400)return `${Math.floor(secs / 3600)}h ago`;
    return `${Math.floor(secs / 86400)}d ago`;
}

export default function ActivityFeed({ limit = 8 }) {
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.get(`/insights/activity?limit=${limit}`)
            .then(r => setEvents(r.data.events || []))
            .catch(() => {})
            .finally(() => setLoading(false));
    }, [limit]);

    if (loading) {
        return (
            <div className="space-y-3">
                {[...Array(4)].map((_, i) => (
                    <div key={i} className="flex gap-3 animate-pulse">
                        <div className="w-8 h-8 rounded-full bg-zinc-800 flex-shrink-0" />
                        <div className="flex-1 space-y-1">
                            <div className="h-3 bg-zinc-800 rounded w-3/4" />
                            <div className="h-3 bg-zinc-800 rounded w-1/3" />
                        </div>
                    </div>
                ))}
            </div>
        );
    }

    if (!events.length) {
        return (
            <div className="text-center py-6 text-zinc-500">
                <Bell size={28} className="mx-auto mb-2 opacity-40" />
                <p className="text-sm">No activity yet. Start applying to jobs!</p>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {events.map((ev) => {
                const meta = EVENT_META[ev.event_type] || EVENT_META.status_changed;
                const IconComp = meta.icon;
                return (
                    <div key={ev.activity_id} className="flex gap-3 items-start group">
                        <div
                            className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center"
                            style={{ background: `${meta.color}20`, border: `1px solid ${meta.color}40` }}
                        >
                            <IconComp size={14} weight="fill" color={meta.color} />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-zinc-200 leading-tight truncate">
                                {ev.title}
                            </p>
                            <p className="text-xs text-zinc-500 mt-0.5">{timeAgo(ev.created_at)}</p>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
