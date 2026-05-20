import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import {
    House, Briefcase, EnvelopeSimple, ChartLine, Graph,
    User as UserIcon, SignOut, Sparkle, CreditCard,
    BookmarkSimple, FileText, ChatCircle, CurrencyDollar,
    CalendarBlank, UsersThree, Warning, Brain, ShieldCheck,
    Flame
} from "@phosphor-icons/react";
import AICoachDock        from "./AICoachDock";
import NotificationsDrawer from "./NotificationsDrawer";
import LanguageSwitcher   from "./LanguageSwitcher";
import { Link }           from "react-router-dom";

const NAV_MAIN = [
    { to: "/dashboard",  label: "Dashboard",   icon: House          },
    { to: "/jobs",       label: "Jobs",         icon: Briefcase      },
    { to: "/bookmarks",  label: "Bookmarks",    icon: BookmarkSimple },
    { to: "/emails",     label: "Inbox",        icon: EnvelopeSimple },
    { to: "/timeline",   label: "Timeline",     icon: CalendarBlank  },
    { to: "/insights",   label: "Insights",     icon: ChartLine      },
    { to: "/career-map", label: "Career Map",   icon: Graph      },
];

const NAV_TOOLS = [
    { to: "/cv-tailor",      label: "CV Tailor",        icon: FileText       },
    { to: "/interview-prep", label: "Interview",        icon: ChatCircle     },
    { to: "/salary",         label: "Salary Intel",     icon: CurrencyDollar },
    { to: "/decision",       label: "Decision Engine",  icon: Brain          },
    { to: "/referral",       label: "Refer Friends",    icon: UsersThree     },
];

const NAV_BOTTOM = [
    { to: "/profile", label: "Profile", icon: UserIcon   },
    { to: "/billing", label: "Billing", icon: CreditCard },
    { to: "/privacy", label: "Privacy", icon: ShieldCheck },
];

export default function Layout() {
    const { user, loading, logout } = useAuth();
    const navigate = useNavigate();
    const [stats, setStats] = useState({ xp: 0, level: 1, streak: 0, progress: { percent: 0 } });
    const [coachOpen, setCoachOpen] = useState(false);

    useEffect(() => {
        if (!loading && !user) navigate("/", { replace: true });
    }, [user, loading, navigate]);

    useEffect(() => {
        if (!user) return;
        api.get("/me/stats").then((r) => setStats(r.data)).catch((err) => console.error("stats load failed:", err));
    }, [user]);

    if (loading || !user) {
        return <div className="min-h-screen flex items-center justify-center text-zinc-500">Loading…</div>;
    }

    return (
        <div className="min-h-screen flex grain" data-testid="app-shell">
            {/* Sidebar */}
            <aside className="w-64 border-r border-zinc-900 bg-black/40 flex flex-col" data-testid="sidebar">
                <div className="px-6 py-6 border-b border-zinc-900">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-md bg-zinc-50 text-black flex items-center justify-center font-display font-black">
                            <Sparkle weight="fill" size={18} />
                        </div>
                        <div>
                            <div className="font-display font-black text-lg leading-none tracking-tight">Career OS</div>
                            <div className="overline mt-1">v0.1 — beta</div>
                        </div>
                    </div>
                </div>

                <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
                    {NAV_MAIN.map(({ to, label, icon: Icon }) => (
                        <NavLink
                            key={to}
                            to={to}
                            data-testid={`nav-${label.toLowerCase().replace(/\s/g, "-")}`}
                            className={({ isActive }) =>
                                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                                    isActive
                                        ? "bg-zinc-50 text-black font-medium"
                                        : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900"
                                }`
                            }
                        >
                            <Icon size={18} weight="duotone" />
                            <span>{label}</span>
                        </NavLink>
                    ))}

                    {/* AI Tools section */}
                    <div className="pt-4 pb-1 px-3">
                        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
                            AI Tools
                        </p>
                    </div>
                    {NAV_TOOLS.map(({ to, label, icon: Icon }) => (
                        <NavLink
                            key={to}
                            to={to}
                            data-testid={`nav-${label.toLowerCase().replace(/\s/g, "-")}`}
                            className={({ isActive }) =>
                                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                                    isActive
                                        ? "bg-zinc-50 text-black font-medium"
                                        : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900"
                                }`
                            }
                        >
                            <Icon size={18} weight="duotone" />
                            <span>{label}</span>
                        </NavLink>
                    ))}

                    {/* Account section */}
                    <div className="pt-4 pb-1 px-3">
                        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
                            Account
                        </p>
                    </div>
                    {NAV_BOTTOM.map(({ to, label, icon: Icon }) => (
                        <NavLink
                            key={to}
                            to={to}
                            data-testid={`nav-${label.toLowerCase().replace(/\s/g, "-")}`}
                            className={({ isActive }) =>
                                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                                    isActive
                                        ? "bg-zinc-50 text-black font-medium"
                                        : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900"
                                }`
                            }
                        >
                            <Icon size={18} weight="duotone" />
                            <span>{label}</span>
                        </NavLink>
                    ))}
                </nav>

                {/* User card */}
                <div className="p-3 border-t border-zinc-900 space-y-2">
                    <div className="card-soft p-3 flex items-center gap-3" data-testid="streak-card">
                        <div className="streak-pulse w-9 h-9 rounded-full bg-orange-500/15 border border-orange-500/40 flex items-center justify-center">
                            <Flame size={18} weight="fill" color="#FF5C00" />
                        </div>
                        <div className="flex-1">
                            <div className="font-mono-ui text-lg leading-none" style={{ color: "#FF5C00" }}>
                                {stats.streak}
                            </div>
                            <div className="text-[11px] text-zinc-500">day streak</div>
                        </div>
                        <div className="text-right">
                            <div className="font-mono-ui text-sm" style={{ color: "#FBBF24" }} data-testid="user-xp">
                                {stats.xp} XP
                            </div>
                            <div className="text-[11px] text-zinc-500">Lv {stats.level}</div>
                        </div>
                    </div>

                    <div className="flex items-center gap-2 px-2 py-1.5">
                        {user.picture ? (
                            <img src={user.picture} alt="" className="w-7 h-7 rounded-full" />
                        ) : (
                            <div className="w-7 h-7 rounded-full bg-zinc-800 flex items-center justify-center text-xs">
                                {(user.name || "?")[0]}
                            </div>
                        )}
                        <div className="flex-1 min-w-0">
                            <div className="text-xs truncate">{user.name}</div>
                            <div className="text-[10px] text-zinc-500 truncate">{user.email}</div>
                        </div>
                        <button
                            onClick={logout}
                            className="text-zinc-500 hover:text-zinc-100 p-1"
                            data-testid="logout-btn"
                            title="Logout"
                        >
                            <SignOut size={16} />
                        </button>
                    </div>
                </div>
            </aside>

            {/* Main */}
            <main className="flex-1 overflow-x-hidden relative" data-testid="main-content">
                {/* Top bar */}
                <div className="flex items-center justify-between px-6 py-3 border-b border-zinc-900 bg-black/20">
                    <TrialBanner user={user} />
                    <div className="flex items-center gap-3 ms-auto">
                        <LanguageSwitcher />
                        <NotificationsDrawer />
                    </div>
                </div>
                <Outlet />
                <button
                    onClick={() => setCoachOpen((s) => !s)}
                    data-testid="coach-toggle-btn"
                    className="fixed bottom-6 right-6 z-40 px-4 py-3 rounded-full glass hover:bg-zinc-50 hover:text-black text-sm font-medium flex items-center gap-2 transition-colors"
                >
                    <Sparkle size={16} weight="fill" />
                    AI Coach
                </button>
                <AICoachDock open={coachOpen} onClose={() => setCoachOpen(false)} />
            </main>
        </div>
    );
}

// ── Trial Banner ──────────────────────────────────────────────────
function TrialBanner({ user }) {
    const [trial, setTrial]     = useState(null);
    const [dismissed, setDismissed] = useState(false);

    useEffect(() => {
        if (!user) return;
        api.get("/billing/trial-status").then(r => setTrial(r.data)).catch(() => {});
    }, [user]);

    if (!trial || dismissed) return null;

    // Show "start trial" if eligible and on free plan
    if (trial.can_start_trial && !trial.trial_active) {
        return (
            <div className="quota-banner flex-1 max-w-lg">
                <div className="flex items-center gap-2">
                    <Warning size={14} weight="fill" color="#FBBF24" />
                    <span>You're on the Free plan.</span>
                </div>
                <div className="flex items-center gap-3">
                    <Link to="/billing" className="text-yellow-300 text-xs font-semibold hover:underline">
                        Start 7-day free trial →
                    </Link>
                    <button onClick={() => setDismissed(true)}
                        className="text-yellow-600 hover:text-yellow-400 text-xs">✕</button>
                </div>
            </div>
        );
    }

    // Show trial expiry countdown
    if (trial.trial_active && trial.trial_ends_at) {
        const daysLeft = Math.max(0, Math.ceil(
            (new Date(trial.trial_ends_at) - Date.now()) / 86400000
        ));
        if (daysLeft <= 3) {
            return (
                <div className="quota-banner flex-1 max-w-lg">
                    <span>⚡ Trial ends in {daysLeft} day{daysLeft !== 1 ? "s" : ""}.</span>
                    <Link to="/billing">Upgrade to keep Pro →</Link>
                </div>
            );
        }
    }

    return null;
}
