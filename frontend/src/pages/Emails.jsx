import { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { Sparkle, EnvelopeSimple, Calendar, X, CheckCircle, ArrowSquareOut } from "@phosphor-icons/react";

const CLASS_COLOR = {
    interview:         "#007AFF",
    offer:             "#10B981",
    rejection:         "#EF4444",
    recruiter_reachout:"#FBBF24",
    assessment:        "#F59E0B",
    followup:          "#A855F7",
    ghosted:           "#52525b",
    other:             "#71717A",
};

function GmailCTA({ onConnected }) {
    const [loading, setLoading] = useState(false);

    const connect = async () => {
        setLoading(true);
        try {
            const r = await api.get("/gmail/connect");
            window.location.href = r.data.auth_url;
        } catch {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-16 h-16 rounded-full bg-zinc-800 flex items-center justify-center mb-5">
                <EnvelopeSimple size={28} className="text-zinc-400" weight="duotone" />
            </div>
            <h2 className="font-display font-bold text-2xl mb-3">Connect your Gmail</h2>
            <p className="text-sm text-zinc-500 max-w-sm mb-8 leading-relaxed">
                Career OS reads your recruiter emails and classifies them automatically —
                interviews, rejections, offers, and more.
            </p>
            <button
                onClick={connect}
                disabled={loading}
                className="flex items-center gap-2 bg-zinc-50 text-black px-5 py-2.5
                           rounded-lg text-sm font-medium hover:bg-zinc-200 transition-colors
                           disabled:opacity-60"
            >
                <ArrowSquareOut size={15} />
                {loading ? "Redirecting…" : "Connect Gmail"}
            </button>
            <p className="text-xs text-zinc-600 mt-4">Read-only access. We never send emails on your behalf.</p>
        </div>
    );
}

export default function Emails() {
    const [threads, setThreads]       = useState([]);
    const [active, setActive]         = useState(null);
    const [classifying, setClassifying] = useState(false);
    const [syncing, setSyncing]       = useState(false);
    const [gmailStatus, setGmailStatus] = useState(null); // null=loading, false=not connected, true=connected

    const loadGmailStatus = useCallback(async () => {
        try {
            const r = await api.get("/gmail/status");
            setGmailStatus(r.data.connected);
        } catch {
            setGmailStatus(false);
        }
    }, []);

    const load = useCallback(async () => {
        const r = await api.get("/emails");
        setThreads(r.data.threads || []);
        setActive(curr => curr || (r.data.threads?.length ? r.data.threads[0] : null));
    }, []);

    useEffect(() => {
        loadGmailStatus();
    }, [loadGmailStatus]);

    useEffect(() => {
        if (gmailStatus) load();
    }, [gmailStatus, load]);

    // Handle ?gmail=connected redirect
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        if (params.get("gmail") === "connected") {
            setGmailStatus(true);
            window.history.replaceState({}, "", "/emails");
        }
    }, []);

    const syncGmail = async () => {
        setSyncing(true);
        try {
            await api.post("/gmail/sync");
            await load();
        } catch (err) {
            console.error("sync failed:", err);
        }
        setSyncing(false);
    };

    const classifyAll = async () => {
        setClassifying(true);
        try {
            await api.post("/emails/classify-all");
            await load();
        } catch (err) {
            console.error("classify-all failed:", err);
        }
        setClassifying(false);
    };

    return (
        <div className="px-8 py-8 max-w-7xl mx-auto" data-testid="emails-page">
            <div className="flex items-end justify-between mb-6 flex-wrap gap-3">
                <div>
                    <div className="overline">Inbox Intelligence</div>
                    <h1 className="font-display font-black text-4xl tracking-tight mt-2">Recruiter Threads</h1>
                    <p className="text-zinc-500 mt-2 text-sm">AI-classified, linked to your applications.</p>
                </div>
                {gmailStatus && (
                    <div className="flex items-center gap-2">
                        <button
                            onClick={syncGmail}
                            disabled={syncing}
                            className="bg-zinc-800 text-zinc-300 border border-zinc-700 hover:bg-zinc-700
                                       transition-colors rounded-lg px-4 py-2 text-sm flex items-center gap-2"
                        >
                            {syncing ? "Syncing…" : "Sync Gmail"}
                        </button>
                        <button
                            onClick={classifyAll}
                            disabled={classifying}
                            data-testid="classify-all-btn"
                            className="bg-blue-600/10 text-blue-400 border border-blue-500/20
                                       hover:bg-blue-600/20 transition-colors rounded-lg px-4 py-2
                                       text-sm flex items-center gap-2"
                        >
                            <Sparkle size={14} weight="fill" />
                            {classifying ? "Classifying…" : "Classify all"}
                        </button>
                    </div>
                )}
            </div>

            {/* Gmail CTA — if not connected */}
            {gmailStatus === false && <GmailCTA />}

            {/* Loading */}
            {gmailStatus === null && (
                <div className="text-center py-20 text-zinc-500 text-sm">Loading…</div>
            )}

            {gmailStatus && (
            <div className="grid lg:grid-cols-3 gap-4 h-[calc(100vh-220px)]">
                <div className="card-soft overflow-y-auto" data-testid="thread-list">
                    {threads.length === 0 && (
                        <div className="p-8 text-center text-zinc-500">
                            <EnvelopeSimple size={24} className="mx-auto mb-3 opacity-30" />
                            <p className="text-sm">No emails synced yet.</p>
                            <button onClick={syncGmail} disabled={syncing}
                                className="text-xs text-zinc-400 hover:text-zinc-200 mt-2 transition-colors">
                                {syncing ? "Syncing…" : "Sync now"}
                            </button>
                        </div>
                    )}
                    {threads.map((t) => (
                        <button
                            key={t.thread_id}
                            onClick={() => setActive(t)}
                            data-testid={`thread-${t.thread_id}`}
                            className={`w-full text-left p-4 border-b border-zinc-900 transition-colors ${
                                active?.thread_id === t.thread_id ? "bg-zinc-900" : "hover:bg-zinc-900/50"
                            }`}
                        >
                            <div className="flex items-start justify-between gap-2 mb-1">
                                <div className="font-medium text-sm truncate">{t.from_name}</div>
                                <div
                                    className="text-[9px] font-mono-ui uppercase tracking-widest px-1.5 py-0.5 rounded flex-shrink-0"
                                    style={{ background: CLASS_COLOR[t.classification] + "15", color: CLASS_COLOR[t.classification] }}
                                >
                                    {t.classification}
                                </div>
                            </div>
                            <div className="text-xs text-zinc-300 truncate">{t.subject}</div>
                            <div className="text-[11px] text-zinc-500 mt-1">{new Date(t.received_at).toLocaleDateString()}</div>
                        </button>
                    ))}
                </div>

                <div className="lg:col-span-2 card-soft overflow-y-auto" data-testid="thread-view">
                    {!active ? (
                        <div className="p-10 text-center text-zinc-500">Select a thread</div>
                    ) : (
                        <div className="p-6">
                            <div className="flex items-start justify-between gap-3 mb-5">
                                <div>
                                    <div className="overline mb-2">{active.classification}</div>
                                    <h2 className="font-display font-bold text-2xl tracking-tight">{active.subject}</h2>
                                    <div className="text-zinc-500 text-sm mt-1">{active.from_name} &lt;{active.last_message?.from_addr}&gt;</div>
                                </div>
                                <div
                                    className="px-3 py-1 rounded-full text-xs font-mono-ui uppercase tracking-widest"
                                    style={{ background: CLASS_COLOR[active.classification] + "20", color: CLASS_COLOR[active.classification], border: `1px solid ${CLASS_COLOR[active.classification]}30` }}
                                >
                                    {active.classification}
                                </div>
                            </div>

                            {active.last_message?.intent && (
                                <div className="mb-5 p-3 rounded-lg bg-blue-500/5 border border-blue-500/15 text-sm">
                                    <div className="overline mb-1">AI Intent</div>
                                    <div className="text-zinc-200">{active.last_message.intent}</div>
                                    {active.last_message.next_steps?.length > 0 && (
                                        <div className="mt-2 space-y-1">
                                            <div className="overline">Next Steps</div>
                                            {active.last_message.next_steps.map((s, i) => (
                                                <div key={`step-${s}-${i}`} className="text-sm flex gap-2"><CheckCircle size={14} weight="fill" color="#10B981" />{s}</div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            <div className="space-y-4" data-testid="messages-list">
                                {active.messages.map((m) => (
                                    <div key={m.email_id} className="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800">
                                        <div className="text-xs text-zinc-500 mb-2">
                                            {m.from_name} • {new Date(m.received_at).toLocaleString()}
                                        </div>
                                        <div className="text-zinc-200 whitespace-pre-line leading-relaxed text-sm">{m.body}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
            )}
        </div>
    );
}
