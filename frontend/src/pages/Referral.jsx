import { useState, useEffect } from "react";
import { api } from "../lib/api";
import { Users, Gift, ClipboardText, WhatsappLogo, Link as LinkIcon } from "@phosphor-icons/react";

export default function Referral() {
    const [data, setData]       = useState(null);
    const [loading, setLoading] = useState(true);
    const [copied, setCopied]   = useState(false);
    const [applying, setApplying] = useState(false);
    const [codeInput, setCodeInput] = useState("");
    const [codeMsg, setCodeMsg] = useState(null);

    useEffect(() => {
        api.get("/billing/referral/stats")
            .then(r => setData(r.data))
            .catch(() => {})
            .finally(() => setLoading(false));
    }, []);

    const generate = async () => {
        try {
            const r = await api.post("/billing/referral/generate");
            setData(d => ({ ...d, ...r.data }));
        } catch {}
    };

    const copyLink = () => {
        navigator.clipboard.writeText(data?.referral_url || "");
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const shareWhatsApp = () => {
        const msg = encodeURIComponent(
            `Use Career OS to track your job search with AI 🚀\n${data?.referral_url}`
        );
        window.open(`https://wa.me/?text=${msg}`, "_blank");
    };

    const shareLinkedIn = () => {
        const url = encodeURIComponent(data?.referral_url || "");
        window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${url}`, "_blank");
    };

    const apply_code = async () => {
        if (!codeInput.trim()) return;
        setApplying(true);
        setCodeMsg(null);
        try {
            await api.post("/billing/referral/apply", { code: codeInput.trim() });
            setCodeMsg({ ok: true, msg: "Code applied! Bonus days added to your trial." });
        } catch (e) {
            setCodeMsg({ ok: false, msg: e.response?.data?.detail || "Invalid code." });
        }
        setApplying(false);
    };

    return (
        <div className="px-6 py-8 max-w-3xl mx-auto">
            <div className="mb-8">
                <div className="overline">Referrals</div>
                <h1 className="font-display font-black text-4xl tracking-tight mt-2">
                    Invite Friends
                </h1>
                <p className="text-zinc-500 text-sm mt-2">
                    Each friend who upgrades gives you <strong className="text-zinc-200">30 free days of Pro.</strong>
                </p>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-3 gap-4 mb-8">
                {[
                    { label: "Referrals",    value: data?.conversions || 0,   color: "#10B981" },
                    { label: "Days Earned",  value: `${data?.days_earned || 0}d`, color: "#FBBF24" },
                    { label: "Pending",      value: data?.pending || 0,        color: "#3B82F6" },
                ].map(item => (
                    <div key={item.label} className="card-soft p-5 text-center">
                        <p className="font-display font-black text-3xl"
                           style={{ color: item.color }}>{item.value}</p>
                        <p className="text-xs text-zinc-500 mt-1">{item.label}</p>
                    </div>
                ))}
            </div>

            {/* Your referral link */}
            <div className="card-soft p-6 mb-6">
                <h3 className="font-display font-bold mb-4 flex items-center gap-2">
                    <Gift size={18} weight="fill" color="#FBBF24" />
                    Your Referral Link
                </h3>

                {!data?.referral_code ? (
                    <button onClick={generate}
                        className="bg-zinc-50 text-black px-5 py-2.5 rounded-lg
                                   text-sm font-semibold hover:bg-zinc-200 transition-colors">
                        Generate My Link
                    </button>
                ) : (
                    <div className="space-y-4">
                        {/* Link display */}
                        <div className="flex gap-2">
                            <div className="flex-1 px-3 py-2.5 bg-zinc-900 border border-zinc-800
                                            rounded-lg text-sm text-zinc-300 font-mono truncate">
                                {data.referral_url}
                            </div>
                            <button onClick={copyLink}
                                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg
                                            text-sm font-medium transition-colors flex-shrink-0 ${
                                    copied
                                        ? "bg-green-500/20 text-green-400 border border-green-500/30"
                                        : "bg-zinc-800 text-zinc-300 border border-zinc-700 hover:bg-zinc-700"
                                }`}>
                                <ClipboardText size={14} />
                                {copied ? "Copied!" : "Copy"}
                            </button>
                        </div>

                        {/* Share buttons */}
                        <div className="flex gap-2">
                            <button onClick={shareWhatsApp}
                                className="flex items-center gap-2 px-4 py-2 rounded-lg
                                           bg-green-600/15 border border-green-500/20
                                           text-green-400 text-sm hover:bg-green-600/25 transition-colors">
                                <WhatsappLogo size={15} weight="fill" />
                                WhatsApp
                            </button>
                            <button onClick={shareLinkedIn}
                                className="flex items-center gap-2 px-4 py-2 rounded-lg
                                           bg-blue-600/15 border border-blue-500/20
                                           text-blue-400 text-sm hover:bg-blue-600/25 transition-colors">
                                <LinkIcon size={15} weight="fill" />
                                LinkedIn
                            </button>
                        </div>

                        {/* Code only */}
                        <p className="text-xs text-zinc-600">
                            Your code: <span className="font-mono text-zinc-400">
                                {data.referral_code}
                            </span>
                        </p>
                    </div>
                )}
            </div>

            {/* Apply a code */}
            <div className="card-soft p-6 mb-6">
                <h3 className="font-display font-bold mb-4 flex items-center gap-2">
                    <Users size={18} weight="fill" color="#3B82F6" />
                    Have a Referral Code?
                </h3>
                <div className="flex gap-2">
                    <input value={codeInput} onChange={e => setCodeInput(e.target.value)}
                        placeholder="Enter referral code…"
                        className="flex-1 px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                                   text-sm text-zinc-200 placeholder:text-zinc-600
                                   focus:outline-none focus:border-zinc-700" />
                    <button onClick={apply_code} disabled={applying || !codeInput.trim()}
                        className="px-4 py-2.5 bg-zinc-50 text-black font-semibold text-sm
                                   rounded-lg hover:bg-zinc-200 transition-colors
                                   disabled:opacity-40 disabled:cursor-not-allowed">
                        {applying ? "Applying…" : "Apply"}
                    </button>
                </div>
                {codeMsg && (
                    <p className={`text-xs mt-2 ${codeMsg.ok ? "text-green-400" : "text-red-400"}`}>
                        {codeMsg.msg}
                    </p>
                )}
            </div>

            {/* How it works */}
            <div className="card-soft p-6">
                <h3 className="font-display font-bold mb-4">How it works</h3>
                <ol className="space-y-3">
                    {[
                        "Share your referral link with friends looking for a job",
                        "They sign up and try Career OS for free",
                        "When they upgrade to Pro, you get 30 days free",
                        "No limit — refer 10 friends, get 10 months free",
                    ].map((step, i) => (
                        <li key={i} className="flex gap-3 text-sm text-zinc-400">
                            <span className="w-5 h-5 rounded-full bg-zinc-800 flex-shrink-0
                                            flex items-center justify-center text-xs font-mono text-zinc-300">
                                {i + 1}
                            </span>
                            {step}
                        </li>
                    ))}
                </ol>
            </div>
        </div>
    );
}
