import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { CurrencyDollar, ChartBar, HandCoins, Airplane, ClipboardText } from "@phosphor-icons/react";

export default function SalaryIntel() {
    const [searchParams] = useSearchParams();
    const [tab, setTab] = useState("range");

    // Shared
    const [role, setRole]           = useState("");
    const [location, setLocation]   = useState("");
    const [experience, setExperience] = useState(0);
    const [currency, setCurrency]   = useState("EUR");

    // Range
    const [rangeResult, setRangeResult] = useState(null);
    const [loadingRange, setLoadingRange] = useState(false);

    // Offer
    const [offerSalary, setOfferSalary]   = useState("");
    const [offerBenefits, setOfferBenefits] = useState("");
    const [offerResult, setOfferResult]   = useState(null);
    const [loadingOffer, setLoadingOffer] = useState(false);

    // Negotiate
    const [currentOffer, setCurrentOffer] = useState("");
    const [targetSalary, setTargetSalary] = useState("");
    const [negReason, setNegReason]       = useState("market research");
    const [negResult, setNegResult]       = useState(null);
    const [loadingNeg, setLoadingNeg]     = useState(false);

    // Cost of Living
    const [fromCity, setFromCity]     = useState("");
    const [toCity, setToCity]         = useState("Lisbon");
    const [currentSal, setCurrentSal] = useState("");
    const [colResult, setColResult]   = useState(null);
    const [loadingCOL, setLoadingCOL] = useState(false);

    // Load from job / profile
    useEffect(() => {
        const jobId = searchParams.get("job_id");
        if (jobId) {
            api.get(`/jobs/${jobId}`).then(r => {
                const j = r.data?.job || r.data;
                if (j) { setRole(j.title || ""); setLocation(j.location || ""); }
            }).catch(() => {});
        }
        api.get("/profile").then(r => {
            if (!r.data) return;
            setRole(prev => prev || (r.data.target_roles?.[0] ?? ""));
            setLocation(prev => prev || (r.data.target_locations?.[0] ?? ""));
            setExperience(r.data.years_experience || 0);
            setFromCity(r.data.location || "");
            setCurrentSal(prev => prev || (r.data.salary_min ? String(r.data.salary_min) : ""));
        }).catch(() => {});
    }, []);

    // ── Helpers ────────────────────────────────────────────────
    const fmt = n => (n ? parseInt(n).toLocaleString() : "—");

    const verdictMeta = v => ({
        below_market:  { color: "#EF4444", label: "Below Market 👇" },
        at_market:     { color: "#FBBF24", label: "Fair Market Rate ✓" },
        above_market:  { color: "#10B981", label: "Strong Offer 🎉" },
    }[v] || { color: "#71717A", label: v });

    const recommendationColor = r => ({
        accept:    "#10B981",
        negotiate: "#FBBF24",
        decline:   "#EF4444",
    }[r] || "#71717A");

    const copyText = t => navigator.clipboard.writeText(t);

    // ── Handlers ───────────────────────────────────────────────
    const handleRange = async () => {
        if (!role) return;
        setLoadingRange(true); setRangeResult(null);
        try {
            const r = await api.post("/salary/range", { role, location, years_experience: experience });
            setRangeResult(r.data);
        } catch { alert("Salary lookup failed."); }
        setLoadingRange(false);
    };

    const handleOffer = async () => {
        if (!offerSalary || !role) return;
        setLoadingOffer(true); setOfferResult(null);
        try {
            const r = await api.post("/salary/evaluate-offer", {
                offered_salary: parseFloat(offerSalary),
                currency,
                role, location,
                benefits: offerBenefits.split(",").map(s => s.trim()).filter(Boolean),
            });
            setOfferResult(r.data);
        } catch { alert("Offer evaluation failed."); }
        setLoadingOffer(false);
    };

    const handleNegotiate = async () => {
        if (!currentOffer || !targetSalary) return;
        setLoadingNeg(true); setNegResult(null);
        try {
            const r = await api.post("/salary/negotiate", {
                current_offer: parseFloat(currentOffer),
                target_salary: parseFloat(targetSalary),
                currency, role, reason: negReason,
            });
            setNegResult(r.data);
        } catch { alert("Negotiation script failed."); }
        setLoadingNeg(false);
    };

    const handleCOL = async () => {
        if (!fromCity || !toCity || !currentSal) return;
        setLoadingCOL(true); setColResult(null);
        try {
            const r = await api.get(
                `/salary/cost-of-living?from_city=${encodeURIComponent(fromCity)}&to_city=${encodeURIComponent(toCity)}&current_salary=${currentSal}`
            );
            setColResult(r.data);
        } catch { alert("Cost of living comparison failed."); }
        setLoadingCOL(false);
    };

    // ── Shared inputs ──────────────────────────────────────────
    const sharedInputs = (
        <div className="flex flex-wrap gap-3 mb-6">
            <input value={role} onChange={e => setRole(e.target.value)}
                placeholder="Role / Job title *"
                className="flex-1 min-w-36 px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                           text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-700" />
            <input value={location} onChange={e => setLocation(e.target.value)}
                placeholder="Location (e.g. Lisbon)"
                className="flex-1 min-w-36 px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                           text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-700" />
            <input type="number" min={0} max={40} value={experience}
                onChange={e => setExperience(parseInt(e.target.value) || 0)}
                placeholder="Years exp."
                className="w-28 px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                           text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-700" />
            <select value={currency} onChange={e => setCurrency(e.target.value)}
                className="w-24 px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                           text-sm text-zinc-200 focus:outline-none focus:border-zinc-700">
                {["EUR","USD","GBP","AED","SAR"].map(c => <option key={c}>{c}</option>)}
            </select>
        </div>
    );

    return (
        <div className="px-6 py-8 max-w-5xl mx-auto">
            {/* Header */}
            <div className="mb-8">
                <div className="overline">Market Intelligence</div>
                <h1 className="font-display font-black text-4xl tracking-tight mt-2">Salary Intelligence</h1>
                <p className="text-zinc-500 text-sm mt-2">Know your worth. Negotiate with data.</p>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 mb-8 border-b border-zinc-800">
                {[
                    { id: "range",     label: "Market Rates"    },
                    { id: "offer",     label: "Evaluate Offer"  },
                    { id: "negotiate", label: "Negotiate"        },
                    { id: "col",       label: "Cost of Living"  },
                ].map(t => (
                    <button key={t.id} onClick={() => setTab(t.id)}
                        className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                            tab === t.id
                                ? "border-zinc-100 text-zinc-100"
                                : "border-transparent text-zinc-500 hover:text-zinc-300"
                        }`}>
                        {t.label}
                    </button>
                ))}
            </div>

            {/* ── MARKET RATES ────────────────────────────────── */}
            {tab === "range" && (
                <div>
                    {sharedInputs}
                    <button onClick={handleRange} disabled={loadingRange || !role}
                        className="flex items-center gap-2 bg-zinc-50 text-black px-5 py-2.5
                                   rounded-lg text-sm font-semibold hover:bg-zinc-200 transition-colors
                                   disabled:opacity-40 disabled:cursor-not-allowed mb-6">
                        <ChartBar size={16} weight="fill" />
                        {loadingRange ? "Looking up…" : "Get Market Rate"}
                    </button>

                    {rangeResult && (
                        <div className="space-y-5">
                            {/* Main range card */}
                            <div className="card-soft p-6">
                                <div className="flex items-end justify-between mb-4">
                                    <div>
                                        <p className="text-zinc-500 text-sm">{rangeResult.role} · {rangeResult.location || "Global"}</p>
                                        <h3 className="font-display font-bold text-2xl mt-1">
                                            {rangeResult.currency} {fmt(rangeResult.annual_min)} — {fmt(rangeResult.annual_max)}
                                        </h3>
                                        <p className="text-zinc-400 text-sm mt-1">per year</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-xs text-zinc-500">Median</p>
                                        <p className="font-mono-ui text-xl font-bold text-green-400">
                                            {rangeResult.currency} {fmt(rangeResult.annual_median)}
                                        </p>
                                    </div>
                                </div>

                                {/* Progress bar */}
                                <div className="relative h-2 bg-zinc-800 rounded-full overflow-hidden">
                                    <div className="absolute inset-y-0 left-0 bg-gradient-to-r from-red-500 via-yellow-400 to-green-400 w-full rounded-full" />
                                </div>
                                <div className="flex justify-between text-xs text-zinc-600 mt-1">
                                    <span>Junior</span><span>Mid</span><span>Senior</span>
                                </div>

                                {/* Monthly / Hourly */}
                                <div className="grid grid-cols-3 gap-4 mt-5 pt-5 border-t border-zinc-800">
                                    {[
                                        { label: "Monthly",  val: `${rangeResult.currency} ${fmt(rangeResult.monthly_min)}–${fmt(rangeResult.monthly_max)}` },
                                        { label: "Hourly",   val: `${rangeResult.currency} ${fmt(rangeResult.hourly_min)}–${fmt(rangeResult.hourly_max)}` },
                                        { label: "Confidence", val: rangeResult.confidence || "—" },
                                    ].map(item => (
                                        <div key={item.label}>
                                            <p className="text-xs text-zinc-500">{item.label}</p>
                                            <p className="font-mono-ui text-sm font-semibold text-zinc-200 mt-0.5">{item.val}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Level breakdown */}
                            {rangeResult.comparison && (
                                <div className="grid grid-cols-3 gap-3">
                                    {[
                                        { label: "Junior",  val: rangeResult.comparison.junior },
                                        { label: "Mid",     val: rangeResult.comparison.mid    },
                                        { label: "Senior",  val: rangeResult.comparison.senior },
                                    ].map(item => (
                                        <div key={item.label} className="card-soft p-4 text-center">
                                            <p className="text-xs text-zinc-500 mb-1">{item.label}</p>
                                            <p className="font-mono-ui text-lg font-bold text-zinc-200">
                                                {rangeResult.currency} {fmt(item.val)}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Factors */}
                            {rangeResult.factors?.length > 0 && (
                                <div className="card-soft p-4">
                                    <h4 className="text-xs font-semibold text-zinc-400 mb-2">Factors Affecting Salary</h4>
                                    <div className="flex flex-wrap gap-2">
                                        {rangeResult.factors.map((f, i) => (
                                            <span key={i} className="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">{f}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* ── EVALUATE OFFER ──────────────────────────────── */}
            {tab === "offer" && (
                <div>
                    {sharedInputs}
                    <div className="flex gap-3 mb-4">
                        <input type="number" value={offerSalary} onChange={e => setOfferSalary(e.target.value)}
                            placeholder={`Offered salary (${currency}/year) *`}
                            className="flex-1 px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                                       text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-700" />
                        <input value={offerBenefits} onChange={e => setOfferBenefits(e.target.value)}
                            placeholder="Benefits (comma-separated: health, remote, equity…)"
                            className="flex-1 px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                                       text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-700" />
                    </div>
                    <button onClick={handleOffer} disabled={loadingOffer || !offerSalary || !role}
                        className="flex items-center gap-2 bg-zinc-50 text-black px-5 py-2.5
                                   rounded-lg text-sm font-semibold hover:bg-zinc-200 transition-colors
                                   disabled:opacity-40 disabled:cursor-not-allowed mb-6">
                        <CurrencyDollar size={16} weight="fill" />
                        {loadingOffer ? "Evaluating…" : "Is This Offer Fair?"}
                    </button>

                    {offerResult && (
                        <div className="space-y-4">
                            {/* Verdict */}
                            <div className="card-soft p-6 flex items-center gap-6">
                                <div className="text-center flex-shrink-0">
                                    <p className="font-display font-bold text-3xl"
                                       style={{ color: verdictMeta(offerResult.verdict).color }}>
                                        {offerResult.percent_vs_market > 0 ? "+" : ""}{offerResult.percent_vs_market}%
                                    </p>
                                    <p className="text-xs mt-1" style={{ color: verdictMeta(offerResult.verdict).color }}>
                                        {verdictMeta(offerResult.verdict).label}
                                    </p>
                                </div>
                                <div className="flex-1">
                                    <p className="font-semibold text-zinc-100 mb-1">{offerResult.bottom_line}</p>
                                    <p className="text-sm text-zinc-400">
                                        Market range: {currency} {fmt(offerResult.market_range?.min)} — {fmt(offerResult.market_range?.max)}
                                        <span className="text-zinc-600"> (median {fmt(offerResult.market_range?.median)})</span>
                                    </p>
                                </div>
                                <div className="flex-shrink-0 text-center">
                                    <p className="text-xs text-zinc-500 mb-1">Recommendation</p>
                                    <p className="font-semibold text-sm uppercase tracking-wider"
                                       style={{ color: recommendationColor(offerResult.recommendation) }}>
                                        {offerResult.recommendation}
                                    </p>
                                    {offerResult.negotiation_room && (
                                        <p className="text-xs text-zinc-600 mt-1">
                                            Room: {offerResult.negotiation_room}
                                        </p>
                                    )}
                                </div>
                            </div>

                            {offerResult.key_points?.length > 0 && (
                                <div className="card-soft p-4">
                                    <h4 className="text-xs font-semibold text-zinc-400 mb-3">Key Insights</h4>
                                    <ul className="space-y-1.5">
                                        {offerResult.key_points.map((p, i) => (
                                            <li key={i} className="text-sm text-zinc-300 flex gap-2">
                                                <span className="text-zinc-600 flex-shrink-0">•</span>{p}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* ── NEGOTIATE ───────────────────────────────────── */}
            {tab === "negotiate" && (
                <div>
                    <div className="grid grid-cols-2 gap-3 mb-4">
                        <div>
                            <label className="text-xs text-zinc-500 mb-1 block">Current offer ({currency})</label>
                            <input type="number" value={currentOffer} onChange={e => setCurrentOffer(e.target.value)}
                                placeholder="e.g. 45000"
                                className="w-full px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                                           text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-700" />
                        </div>
                        <div>
                            <label className="text-xs text-zinc-500 mb-1 block">Your target ({currency})</label>
                            <input type="number" value={targetSalary} onChange={e => setTargetSalary(e.target.value)}
                                placeholder="e.g. 55000"
                                className="w-full px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                                           text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-700" />
                        </div>
                    </div>
                    <div className="flex gap-3 mb-4">
                        <input value={role} onChange={e => setRole(e.target.value)} placeholder="Role"
                            className="flex-1 px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                                       text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-700" />
                        <select value={negReason} onChange={e => setNegReason(e.target.value)}
                            className="flex-1 px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                                       text-sm text-zinc-200 focus:outline-none focus:border-zinc-700">
                            <option value="market research">Market research</option>
                            <option value="competing offer">Competing offer</option>
                            <option value="experience">Experience level</option>
                            <option value="living costs">Cost of living</option>
                        </select>
                    </div>
                    <button onClick={handleNegotiate} disabled={loadingNeg || !currentOffer || !targetSalary}
                        className="flex items-center gap-2 bg-zinc-50 text-black px-5 py-2.5
                                   rounded-lg text-sm font-semibold hover:bg-zinc-200 transition-colors
                                   disabled:opacity-40 disabled:cursor-not-allowed mb-6">
                        <HandCoins size={16} weight="fill" />
                        {loadingNeg ? "Writing script…" : "Generate Negotiation Script"}
                    </button>

                    {negResult && (
                        <div className="space-y-4">
                            {/* Email */}
                            <div className="card-soft p-5">
                                <div className="flex items-center justify-between mb-3">
                                    <div>
                                        <p className="text-xs text-zinc-500">Subject</p>
                                        <p className="text-sm font-semibold text-zinc-200 mt-0.5">
                                            {negResult.email_subject}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-zinc-500">
                                            Success: <span style={{
                                                color: negResult.success_probability === "high" ? "#10B981"
                                                     : negResult.success_probability === "medium" ? "#FBBF24"
                                                     : "#EF4444"
                                            }}>{negResult.success_probability}</span>
                                        </span>
                                        <button onClick={() => copyText(negResult.email_body)}
                                            className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-200 border
                                                       border-zinc-800 rounded-lg px-2 py-1 hover:border-zinc-700 transition-colors">
                                            <ClipboardText size={12} /> Copy
                                        </button>
                                    </div>
                                </div>
                                <pre className="text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed
                                                bg-zinc-950 rounded-lg p-4 max-h-72 overflow-y-auto">
                                    {negResult.email_body}
                                </pre>
                            </div>

                            <div className="grid md:grid-cols-2 gap-4">
                                {negResult.talking_points?.length > 0 && (
                                    <div className="card-soft p-4">
                                        <h4 className="text-xs font-semibold text-blue-400 mb-2">Talking Points (Call)</h4>
                                        <ul className="space-y-1.5">
                                            {negResult.talking_points.map((p, i) => (
                                                <li key={i} className="text-xs text-zinc-400">• {p}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                                {negResult.backup_asks?.length > 0 && (
                                    <div className="card-soft p-4">
                                        <h4 className="text-xs font-semibold text-yellow-400 mb-2">If Salary Fails, Ask For…</h4>
                                        <ul className="space-y-1.5">
                                            {negResult.backup_asks.map((p, i) => (
                                                <li key={i} className="text-xs text-zinc-400">• {p}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                                {negResult.what_not_to_say?.length > 0 && (
                                    <div className="card-soft p-4 md:col-span-2">
                                        <h4 className="text-xs font-semibold text-red-400 mb-2">❌ Never Say This</h4>
                                        <ul className="space-y-1 flex flex-wrap gap-x-6">
                                            {negResult.what_not_to_say.map((p, i) => (
                                                <li key={i} className="text-xs text-zinc-400">• {p}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ── COST OF LIVING ──────────────────────────────── */}
            {tab === "col" && (
                <div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                        <input value={fromCity} onChange={e => setFromCity(e.target.value)}
                            placeholder="From city *"
                            className="px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                                       text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-700" />
                        <input value={toCity} onChange={e => setToCity(e.target.value)}
                            placeholder="To city *"
                            className="px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                                       text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-700" />
                        <input type="number" value={currentSal} onChange={e => setCurrentSal(e.target.value)}
                            placeholder="Current salary *"
                            className="px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                                       text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-700" />
                        <button onClick={handleCOL} disabled={loadingCOL || !fromCity || !toCity || !currentSal}
                            className="flex items-center justify-center gap-2 bg-zinc-50 text-black
                                       rounded-lg text-sm font-semibold hover:bg-zinc-200 transition-colors
                                       disabled:opacity-40 disabled:cursor-not-allowed">
                            <Airplane size={15} weight="fill" />
                            {loadingCOL ? "Comparing…" : "Compare"}
                        </button>
                    </div>

                    {colResult && (
                        <div className="space-y-4">
                            <div className="card-soft p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <div>
                                        <p className="text-zinc-500 text-sm">{colResult.from_city} → {colResult.to_city}</p>
                                        <h3 className="font-display font-bold text-2xl mt-1">
                                            {fmt(colResult.equivalent_salary_to)}
                                        </h3>
                                        <p className="text-zinc-400 text-sm">equivalent salary needed in {colResult.to_city}</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="font-semibold capitalize" style={{
                                            color: colResult.verdict?.includes("higher") ? "#EF4444"
                                                 : colResult.verdict?.includes("lower")  ? "#10B981"
                                                 : "#FBBF24"
                                        }}>{colResult.verdict}</p>
                                        <p className="text-xs text-zinc-500 mt-1">cost of living</p>
                                    </div>
                                </div>

                                {/* Breakdown */}
                                {colResult.breakdown && (
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-4 border-t border-zinc-800">
                                        {Object.entries(colResult.breakdown).map(([k, v]) => (
                                            <div key={k} className="text-center">
                                                <p className="text-xs text-zinc-500 capitalize">{k}</p>
                                                <p className="font-mono-ui text-sm font-bold mt-0.5"
                                                   style={{ color: v?.startsWith("+") ? "#EF4444" : v?.startsWith("-") ? "#10B981" : "#FBBF24" }}>
                                                    {v}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="card-soft p-4">
                                <p className="text-sm text-zinc-300 leading-relaxed">{colResult.recommendation}</p>
                            </div>

                            {colResult.key_differences?.length > 0 && (
                                <div className="card-soft p-4">
                                    <h4 className="text-xs font-semibold text-zinc-400 mb-2">Key Differences</h4>
                                    <ul className="space-y-1">
                                        {colResult.key_differences.map((d, i) => (
                                            <li key={i} className="text-xs text-zinc-400">• {d}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
