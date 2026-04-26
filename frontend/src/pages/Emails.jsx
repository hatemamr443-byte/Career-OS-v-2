import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Sparkle, EnvelopeSimple, Calendar, X, CheckCircle } from "@phosphor-icons/react";

const CLASS_COLOR = {
    interview: "#007AFF",
    offer: "#10B981",
    rejection: "#EF4444",
    recruiter: "#FBBF24",
    follow_up: "#A855F7",
    other: "#71717A",
};

export default function Emails() {
    const [threads, setThreads] = useState([]);
    const [active, setActive] = useState(null);
    const [classifying, setClassifying] = useState(false);

    const load = async () => {
        const r = await api.get("/emails");
        setThreads(r.data.threads || []);
        if (!active && r.data.threads?.length) setActive(r.data.threads[0]);
    };

    useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

    const classifyAll = async () => {
        setClassifying(true);
        try {
            await api.post("/emails/classify-all");
            await load();
        } catch {}
        setClassifying(false);
    };

    return (
        <div className="px-8 py-8 max-w-7xl mx-auto" data-testid="emails-page">
            <div className="flex items-end justify-between mb-6 flex-wrap gap-3">
                <div>
                    <div className="overline">Inbox Intelligence</div>
                    <h1 className="font-display font-black text-4xl tracking-tight mt-2">Recruiter Threads</h1>
                    <p className="text-zinc-500 mt-2 text-sm">AI-classified, linked to jobs.</p>
                </div>
                <button
                    onClick={classifyAll}
                    disabled={classifying}
                    data-testid="classify-all-btn"
                    className="bg-blue-600/10 text-blue-400 border border-blue-500/20 hover:bg-blue-600/20 transition-colors rounded-lg px-4 py-2 text-sm flex items-center gap-2"
                >
                    <Sparkle size={14} weight="fill" />
                    {classifying ? "Classifying…" : "Classify all (Gemini Flash)"}
                </button>
            </div>

            <div className="grid lg:grid-cols-3 gap-4 h-[calc(100vh-220px)]">
                <div className="card-soft overflow-y-auto" data-testid="thread-list">
                    {threads.length === 0 && (
                        <div className="p-6 text-zinc-500 text-sm">No emails yet.</div>
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
                                                <div key={i} className="text-sm flex gap-2"><CheckCircle size={14} weight="fill" color="#10B981" />{s}</div>
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
        </div>
    );
}
