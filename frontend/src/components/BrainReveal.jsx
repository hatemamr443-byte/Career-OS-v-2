import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Sparkle, ArrowRight, X, Info } from "@phosphor-icons/react";

/**
 * Brain Reveal — thin, contextual surface for orchestration outputs.
 *
 * Design principles (locked by spec):
 *   - calm, strategic guidance — not AI overload
 *   - one consistent voice across all cards
 *   - source signals + confidence (transparency)
 *   - passive intelligence (this never triggers a fresh AI call)
 *   - dismissible per-card
 *   - max 5 cards, intentionally bounded
 *
 * Inserted ABOVE existing Dashboard content. Renders nothing when empty.
 */

const TONE_STYLES = {
    neutral:  { dot: "#FBBF24", ring: "ring-zinc-700/50",   accent: "text-zinc-100" },
    positive: { dot: "#10B981", ring: "ring-emerald-500/30", accent: "text-emerald-200" },
    caution:  { dot: "#FF5C00", ring: "ring-orange-500/30",  accent: "text-orange-200" },
};

export default function BrainReveal() {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState(null);

    const load = useCallback(async () => {
        try {
            const r = await api.get("/orchestrator/insights");
            setItems(r.data.insights || []);
        } catch (err) {
            // Silent: insights are a passive surface — never block the dashboard
            if (err?.response?.status && err.response.status !== 401) {
                console.warn("brain reveal load failed:", err);
            }
            setItems([]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const dismiss = async (id) => {
        // Optimistic remove
        setItems((prev) => prev.filter((it) => it.id !== id));
        try {
            await api.post(`/orchestrator/insights/${encodeURIComponent(id)}/dismiss`);
        } catch (err) {
            // If it fails, silently log — user already saw the card disappear
            console.warn("dismiss failed:", err);
        }
    };

    if (loading || !items.length) return null;

    return (
        <section
            data-testid="brain-reveal-strip"
            aria-label="Career OS insights"
            className="mb-6"
        >
            <div className="flex items-center gap-2 mb-3 text-zinc-400">
                <Sparkle size={14} weight="duotone" color="#FBBF24" />
                <span className="overline">Career OS noticed</span>
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {items.map((it) => {
                    const tone = TONE_STYLES[it.tone] || TONE_STYLES.neutral;
                    const isOpen = expanded === it.id;
                    return (
                        <article
                            key={it.id}
                            data-testid={`brain-reveal-card-${it.kind}`}
                            className={`relative card-soft p-4 ring-1 ${tone.ring} transition-shadow hover:ring-2`}
                        >
                            {/* Tone dot */}
                            <div className="flex items-start gap-2.5 mb-2">
                                <span
                                    className="mt-1.5 h-1.5 w-1.5 rounded-full flex-shrink-0"
                                    style={{ background: tone.dot }}
                                    aria-hidden
                                />
                                <h3 className={`text-sm font-medium leading-snug pr-6 ${tone.accent}`}>
                                    {it.headline}
                                </h3>
                                <button
                                    type="button"
                                    onClick={() => dismiss(it.id)}
                                    data-testid={`brain-reveal-dismiss-${it.kind}`}
                                    aria-label="Dismiss"
                                    className="absolute top-3 right-3 h-6 w-6 inline-flex items-center justify-center rounded-full text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/60 transition-colors"
                                >
                                    <X size={12} />
                                </button>
                            </div>

                            <p className="text-xs text-zinc-400 leading-relaxed pl-4 mb-3">
                                {it.detail}
                            </p>

                            <div className="flex items-center justify-between gap-2 pl-4">
                                <Link
                                    to={it.suggested_action?.route || "#"}
                                    data-testid={`brain-reveal-action-${it.kind}`}
                                    className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-100 hover:text-white transition-colors"
                                >
                                    {it.suggested_action?.label || "Open"}
                                    <ArrowRight size={11} />
                                </Link>

                                <button
                                    type="button"
                                    onClick={() => setExpanded(isOpen ? null : it.id)}
                                    data-testid={`brain-reveal-why-${it.kind}`}
                                    className="inline-flex items-center gap-1 text-[10px] font-mono-ui uppercase tracking-widest text-zinc-500 hover:text-zinc-300"
                                    aria-expanded={isOpen}
                                >
                                    <Info size={10} />
                                    {isOpen ? "Hide" : "Why this?"}
                                </button>
                            </div>

                            {isOpen && (
                                <div
                                    data-testid={`brain-reveal-reasoning-${it.kind}`}
                                    className="mt-3 pt-3 border-t border-zinc-800/80 pl-4 text-[11px] text-zinc-500 leading-relaxed space-y-1"
                                >
                                    <div className="font-mono-ui uppercase tracking-widest text-[9px] text-zinc-600">
                                        Signals · confidence {it.confidence}%
                                    </div>
                                    <ul className="space-y-0.5">
                                        {(it.source_signals || []).map((s, i) => (
                                            <li key={i}>· {s}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </article>
                    );
                })}
            </div>
        </section>
    );
}
