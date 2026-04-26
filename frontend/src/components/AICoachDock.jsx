import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { PaperPlaneTilt, X, Sparkle } from "@phosphor-icons/react";

export default function AICoachDock({ open, onClose }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [sending, setSending] = useState(false);
    const scrollRef = useRef(null);

    useEffect(() => {
        if (!open) return;
        api.get("/coach/messages").then((r) => setMessages(r.data.messages || [])).catch(() => {});
    }, [open]);

    useEffect(() => {
        if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [messages, open]);

    const send = async () => {
        const txt = input.trim();
        if (!txt || sending) return;
        setSending(true);
        const optimistic = [...messages, { role: "user", content: txt, message_id: `tmp_${Date.now()}` }];
        setMessages(optimistic);
        setInput("");
        try {
            const r = await api.post("/coach/chat", { message: txt });
            setMessages([...optimistic, { role: "assistant", content: r.data.reply, message_id: `tmp2_${Date.now()}` }]);
        } catch {
            setMessages([...optimistic, { role: "assistant", content: "Coach is offline. Try again later.", message_id: `err_${Date.now()}` }]);
        } finally {
            setSending(false);
        }
    };

    if (!open) return null;

    return (
        <div
            className="fixed bottom-24 right-6 z-50 w-[380px] max-w-[calc(100vw-3rem)] h-[520px] glass rounded-2xl flex flex-col overflow-hidden shadow-2xl"
            data-testid="ai-coach-panel"
        >
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
                <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-md bg-blue-500/15 border border-blue-500/30 flex items-center justify-center">
                        <Sparkle size={14} weight="fill" color="#007AFF" />
                    </div>
                    <div>
                        <div className="font-display font-bold text-sm">AI Coach</div>
                        <div className="text-[10px] text-zinc-500 font-mono-ui uppercase tracking-widest">Claude Sonnet 4.5</div>
                    </div>
                </div>
                <button onClick={onClose} className="text-zinc-500 hover:text-zinc-100" data-testid="coach-close-btn">
                    <X size={18} />
                </button>
            </div>

            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3" data-testid="coach-messages">
                {messages.length === 0 && (
                    <div className="text-zinc-500 text-sm">
                        Hi — I'm your AI Career Coach. Ask me anything: which jobs to apply for, how to fix your CV, how to prep for interviews. I'll be direct.
                    </div>
                )}
                {messages.map((m) => (
                    <div
                        key={m.message_id}
                        className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                        <div
                            className={`max-w-[85%] px-3 py-2 rounded-2xl text-sm leading-relaxed ${
                                m.role === "user"
                                    ? "bg-zinc-50 text-black"
                                    : "bg-zinc-900 text-zinc-100 border border-zinc-800"
                            }`}
                        >
                            {m.content}
                        </div>
                    </div>
                ))}
                {sending && <div className="text-zinc-500 text-xs">Coach is thinking…</div>}
            </div>

            <div className="p-3 border-t border-white/10 flex items-center gap-2">
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && send()}
                    placeholder="Ask your coach…"
                    data-testid="coach-input"
                    className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-zinc-600"
                />
                <button
                    onClick={send}
                    disabled={sending}
                    data-testid="coach-send-btn"
                    className="bg-zinc-50 text-black px-3 py-2 rounded-lg text-sm font-medium hover:bg-zinc-200 disabled:opacity-50"
                >
                    <PaperPlaneTilt size={14} weight="fill" />
                </button>
            </div>
        </div>
    );
}
