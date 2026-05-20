import { useEffect, useState, useRef } from "react";
import { api } from "../lib/api";
import { Bell, CheckCircle, Flame, Sparkle, Warning, ArrowRight, X } from "@phosphor-icons/react";

const TYPE_ICON = {
    new_match:          { icon: Sparkle,      color: "#3B82F6" },
    interview_detected: { icon: CheckCircle,  color: "#10B981" },
    streak_reward:      { icon: Flame,        color: "#FF5C00" },
    onboarding_complete:{ icon: Sparkle,      color: "#FBBF24" },
    digest_ready:       { icon: ArrowRight,   color: "#8B5CF6" },
    system_warning:     { icon: Warning,      color: "#EF4444" },
};

function timeAgo(iso) {
    const secs = Math.floor((Date.now() - new Date(iso)) / 1000);
    if (secs < 60)   return "just now";
    if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
    if (secs < 86400)return `${Math.floor(secs / 3600)}h ago`;
    return `${Math.floor(secs / 86400)}d ago`;
}

export default function NotificationsDrawer() {
    const [open, setOpen]           = useState(false);
    const [notifs, setNotifs]       = useState([]);
    const [unread, setUnread]       = useState(0);
    const drawerRef                 = useRef(null);

    const load = async () => {
        try {
            const r = await api.get("/notifications?limit=20");
            setNotifs(r.data.notifications || []);
            setUnread(r.data.unread_count || 0);
        } catch { /* fail silently */ }
    };

    useEffect(() => {
        load();
        const id = setInterval(load, 60_000); // poll every 60s
        return () => clearInterval(id);
    }, []);

    // Close on outside click
    useEffect(() => {
        const handler = (e) => {
            if (drawerRef.current && !drawerRef.current.contains(e.target)) setOpen(false);
        };
        if (open) document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, [open]);

    const markRead = async (id) => {
        await api.patch(`/notifications/${id}/read`).catch(() => {});
        setNotifs(ns => ns.map(n => n.notification_id === id ? { ...n, read: true } : n));
        setUnread(u => Math.max(0, u - 1));
    };

    const markAllRead = async () => {
        await api.patch("/notifications/read-all").catch(() => {});
        setNotifs(ns => ns.map(n => ({ ...n, read: true })));
        setUnread(0);
    };

    return (
        <div className="relative" ref={drawerRef}>
            {/* Bell button */}
            <button
                onClick={() => setOpen(o => !o)}
                className="relative w-8 h-8 flex items-center justify-center rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
                data-testid="notifications-bell"
            >
                <Bell size={18} weight="duotone" />
                {unread > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
                        {unread > 9 ? "9+" : unread}
                    </span>
                )}
            </button>

            {/* Drawer */}
            {open && (
                <div className="absolute right-0 top-10 w-80 bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl z-50 overflow-hidden"
                     data-testid="notifications-drawer">
                    {/* Header */}
                    <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
                        <span className="font-display font-bold text-sm">Notifications</span>
                        <div className="flex items-center gap-2">
                            {unread > 0 && (
                                <button onClick={markAllRead} className="text-xs text-zinc-400 hover:text-zinc-200 transition-colors">
                                    Mark all read
                                </button>
                            )}
                            <button onClick={() => setOpen(false)} className="text-zinc-500 hover:text-zinc-300">
                                <X size={14} />
                            </button>
                        </div>
                    </div>

                    {/* List */}
                    <div className="max-h-96 overflow-y-auto">
                        {notifs.length === 0 ? (
                            <div className="text-center py-8 text-zinc-500">
                                <Bell size={24} className="mx-auto mb-2 opacity-30" />
                                <p className="text-sm">No notifications yet</p>
                            </div>
                        ) : (
                            notifs.map((n) => {
                                const meta = TYPE_ICON[n.type] || TYPE_ICON.new_match;
                                const IconComp = meta.icon;
                                return (
                                    <div
                                        key={n.notification_id}
                                        onClick={() => !n.read && markRead(n.notification_id)}
                                        className={`flex gap-3 px-4 py-3 border-b border-zinc-800/50 cursor-pointer hover:bg-zinc-800/50 transition-colors ${!n.read ? "bg-zinc-800/30" : ""}`}
                                    >
                                        <div
                                            className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center mt-0.5"
                                            style={{ background: `${meta.color}18`, border: `1px solid ${meta.color}30` }}
                                        >
                                            <IconComp size={14} weight="fill" color={meta.color} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-zinc-200 leading-tight">{n.title}</p>
                                            <p className="text-xs text-zinc-500 mt-0.5 leading-relaxed">{n.message}</p>
                                            <p className="text-xs text-zinc-600 mt-1">{timeAgo(n.created_at)}</p>
                                        </div>
                                        {!n.read && (
                                            <div className="w-2 h-2 rounded-full bg-blue-400 flex-shrink-0 mt-2" />
                                        )}
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
