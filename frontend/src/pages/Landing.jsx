import { Link, useNavigate } from "react-router-dom";
import { Sparkle, ArrowRight, Lightning, CheckCircle, Flame, Graph, EnvelopeSimple, Briefcase, ChartLine } from "@phosphor-icons/react";
import { useAuth } from "../context/AuthContext";
import { useEffect } from "react";

const FEATURES = [
    { Icon: Sparkle, title: "AI Decision Engine", body: "Claude Sonnet 4.5 ranks every job by ROI, not by keywords. Apply only when the math is on your side." },
    { Icon: Briefcase, title: "Application Lifecycle Tracker", body: "Discovered → Applied → Interview → Offer. Every transition logged with reason + confidence." },
    { Icon: EnvelopeSimple, title: "Recruiter Inbox Intelligence", body: "Gemini Flash classifies every recruiter email. Intent + next steps surfaced. No more re-reading." },
    { Icon: Flame, title: "Streak & Mission System", body: "Daily AI-generated missions that reinforce good decisions — not random clicks. Duolingo, for your career." },
    { Icon: ChartLine, title: "Pattern Detection", body: "Auto-detect rejection patterns by seniority, role, company. Pivot before you burn out." },
    { Icon: Graph, title: "Identity Graph", body: "Your profile learns your habits — what you avoid, what you accept. Recommendations adapt." },
];

const LOGOS = ["Stripe", "Anthropic", "Linear", "Vercel", "Notion", "Figma"];

export default function Landing() {
    const { user, loading } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        if (!loading && user) navigate("/dashboard", { replace: true });
    }, [user, loading, navigate]);

    const signIn = () => {
        // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
        const redirectUrl = window.location.origin + "/dashboard";
        window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
    };

    return (
        <div className="min-h-screen grain" data-testid="landing-page">
            {/* Nav */}
            <header className="sticky top-0 z-30 backdrop-blur-xl bg-black/60 border-b border-zinc-900">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-md bg-zinc-50 text-black flex items-center justify-center">
                            <Sparkle weight="fill" size={18} />
                        </div>
                        <div className="font-display font-black tracking-tight">Career OS</div>
                    </div>
                    <nav className="hidden md:flex items-center gap-7 text-sm text-zinc-400">
                        <a href="#features" className="hover:text-zinc-100" data-testid="nav-features">Features</a>
                        <Link to="/pricing" className="hover:text-zinc-100" data-testid="nav-pricing">Pricing</Link>
                        <a href="#how" className="hover:text-zinc-100" data-testid="nav-how">How it works</a>
                    </nav>
                    <button
                        onClick={signIn}
                        data-testid="header-signin"
                        className="bg-zinc-50 text-black hover:bg-zinc-200 transition-colors rounded-lg px-4 py-2 text-sm font-medium"
                    >
                        Sign in
                    </button>
                </div>
            </header>

            {/* Hero */}
            <section className="relative dot-grid">
                <div className="max-w-7xl mx-auto px-6 py-24 sm:py-32 grid lg:grid-cols-12 gap-10 items-end">
                    <div className="lg:col-span-7">
                        <div className="overline mb-4 inline-flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#10B981" }} />
                            v0.1 — open beta
                        </div>
                        <h1 className="h1-hero text-5xl sm:text-7xl mb-6">
                            Stop searching.
                            <br />
                            Start <span style={{ color: "#FF5C00" }}>deciding</span>.
                        </h1>
                        <p className="text-zinc-400 text-lg leading-relaxed max-w-xl mb-8">
                            Career OS is not a job board. It's an AI agent that thinks, decides, acts and learns — so every
                            application you make is the right one. Built for serious operators.
                        </p>
                        <div className="flex flex-wrap items-center gap-3">
                            <button
                                onClick={signIn}
                                data-testid="hero-cta"
                                className="bg-zinc-50 text-black hover:bg-zinc-200 transition-colors rounded-xl px-6 py-3.5 font-medium flex items-center gap-2"
                            >
                                Start free <ArrowRight size={16} />
                            </button>
                            <Link
                                to="/pricing"
                                data-testid="hero-pricing"
                                className="border border-zinc-800 hover:border-zinc-700 transition-colors rounded-xl px-6 py-3.5 text-zinc-200"
                            >
                                See pricing
                            </Link>
                        </div>
                        <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-zinc-500">
                            <span className="flex items-center gap-1.5"><CheckCircle size={14} weight="fill" color="#10B981" />Free tier forever</span>
                            <span className="flex items-center gap-1.5"><CheckCircle size={14} weight="fill" color="#10B981" />No credit card</span>
                            <span className="flex items-center gap-1.5"><CheckCircle size={14} weight="fill" color="#10B981" />GDPR-aware</span>
                        </div>
                    </div>

                    {/* Hero stat card */}
                    <div className="lg:col-span-5">
                        <div className="card-soft p-6 space-y-4">
                            <div className="overline">Sample decision</div>
                            <div>
                                <div className="text-[10px] font-mono-ui uppercase tracking-widest text-zinc-500">Stripe</div>
                                <div className="font-display font-bold text-xl mt-1 tracking-tight">Senior Backend Engineer</div>
                                <div className="text-xs text-zinc-500 mt-1">Remote (US) • $180k–$260k</div>
                            </div>
                            <div className="grid grid-cols-3 gap-2">
                                <div className="p-3 bg-zinc-900/60 border border-zinc-800 rounded-lg">
                                    <div className="overline">Score</div>
                                    <div className="font-mono-ui text-2xl" style={{ color: "#10B981" }}>92</div>
                                </div>
                                <div className="p-3 bg-zinc-900/60 border border-zinc-800 rounded-lg">
                                    <div className="overline">Conf.</div>
                                    <div className="font-mono-ui text-2xl" style={{ color: "#007AFF" }}>88</div>
                                </div>
                                <div className="p-3 bg-zinc-900/60 border border-zinc-800 rounded-lg">
                                    <div className="overline">Action</div>
                                    <div className="font-display font-black text-base mt-1" style={{ color: "#10B981" }}>APPLY</div>
                                </div>
                            </div>
                            <div className="text-sm text-zinc-300 leading-relaxed">
                                <span className="text-zinc-500">Reasoning:</span> Stack overlap is exceptional (Python, Go, Kafka). Seniority maps to your 6 years. Salary band sits above your floor.
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Logos row */}
            <section className="border-y border-zinc-900 bg-black/40">
                <div className="max-w-7xl mx-auto px-6 py-8 flex flex-wrap items-center justify-between gap-6 text-zinc-600">
                    <div className="text-xs font-mono-ui uppercase tracking-widest">Jobs sourced from</div>
                    {LOGOS.map((l) => (
                        <div key={l} className="font-display font-bold text-lg text-zinc-500">{l}</div>
                    ))}
                </div>
            </section>

            {/* Features */}
            <section id="features" className="max-w-7xl mx-auto px-6 py-24">
                <div className="overline mb-3">Capabilities</div>
                <h2 className="font-display font-black text-4xl sm:text-5xl tracking-tight max-w-2xl mb-12">
                    Six layers of intelligence. One decision per day.
                </h2>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {FEATURES.map(({ Icon, title, body }) => (
                        <div key={title} className="card-soft p-6" data-testid={`feature-${title.toLowerCase().replace(/\s/g, "-")}`}>
                            <div className="w-10 h-10 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-4">
                                <Icon size={18} weight="duotone" />
                            </div>
                            <div className="font-display font-bold text-lg tracking-tight">{title}</div>
                            <p className="text-zinc-400 text-sm mt-2 leading-relaxed">{body}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* How it works */}
            <section id="how" className="border-t border-zinc-900 dot-grid">
                <div className="max-w-7xl mx-auto px-6 py-24">
                    <div className="overline mb-3">Flow</div>
                    <h2 className="font-display font-black text-4xl sm:text-5xl tracking-tight max-w-2xl mb-12">
                        Three steps. Zero spray-and-pray.
                    </h2>
                    <div className="grid md:grid-cols-3 gap-4">
                        {[
                            { n: "01", t: "Paste your CV", b: "Claude extracts your skills, target roles and seniority into a portable identity graph." },
                            { n: "02", t: "Run the decision engine", b: "Every job gets a score, decision and reasoning. You see what to skip — not just what to chase." },
                            { n: "03", t: "Track outcomes, learn", b: "Lifecycle states + insights expose patterns. Strategy auto-switches when your funnel drops." },
                        ].map((s) => (
                            <div key={s.n} className="card-soft p-6">
                                <div className="font-mono-ui text-3xl text-zinc-600 mb-3">{s.n}</div>
                                <div className="font-display font-bold text-xl tracking-tight">{s.t}</div>
                                <p className="text-zinc-400 text-sm mt-2 leading-relaxed">{s.b}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="border-t border-zinc-900">
                <div className="max-w-4xl mx-auto px-6 py-24 text-center">
                    <h2 className="font-display font-black text-4xl sm:text-5xl tracking-tight mb-6">
                        Your career deserves a system.
                    </h2>
                    <p className="text-zinc-400 text-lg max-w-xl mx-auto mb-8">
                        Free forever. Upgrade only when the ROI is obvious. Cancel any time.
                    </p>
                    <div className="flex flex-wrap items-center justify-center gap-3">
                        <button
                            onClick={signIn}
                            data-testid="cta-bottom"
                            className="bg-zinc-50 text-black hover:bg-zinc-200 transition-colors rounded-xl px-7 py-3.5 font-medium flex items-center gap-2"
                        >
                            <Lightning size={16} weight="fill" />
                            Start free with Google
                        </button>
                        <Link to="/pricing" className="text-zinc-400 hover:text-zinc-100 text-sm" data-testid="cta-pricing-link">
                            View pricing →
                        </Link>
                    </div>
                </div>
            </section>

            <footer className="border-t border-zinc-900">
                <div className="max-w-7xl mx-auto px-6 py-10 flex flex-wrap items-center justify-between gap-4 text-xs text-zinc-600">
                    <div>© Career OS · Built for serious operators.</div>
                    <div className="flex gap-6">
                        <Link to="/pricing">Pricing</Link>
                        <a href="#features">Features</a>
                        <span>GDPR-aware</span>
                    </div>
                </div>
            </footer>
        </div>
    );
}
