import { useState, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import {
    FileText, MagicWand, CheckCircle, Warning, ArrowRight,
    ClipboardText, Download, Clock, Trash
} from "@phosphor-icons/react";

const TABS = ["tailor", "ats", "cover-letter", "versions"];

export default function CVTailor() {
    const [searchParams] = useSearchParams();
    const [tab, setTab]  = useState("tailor");

    // Tailor state
    const [cvText, setCvText]       = useState("");
    const [jobDesc, setJobDesc]     = useState("");
    const [jobTitle, setJobTitle]   = useState("");
    const [company, setCompany]     = useState("");
    const [tailored, setTailored]   = useState(null);
    const [tailoring, setTailoring] = useState(false);

    // ATS state
    const [atsResult, setAtsResult]   = useState(null);
    const [atsLoading, setAtsLoading] = useState(false);

    // Cover Letter state
    const [clResult, setClResult]   = useState(null);
    const [clLoading, setClLoading] = useState(false);
    const [clTone, setClTone]       = useState("professional");
    const [clLang, setClLang]       = useState("en");

    // Versions
    const [versions, setVersions]     = useState([]);
    const [verLoading, setVerLoading] = useState(false);

    // Load CV from profile on mount
    useEffect(() => {
        api.get("/profile").then(r => {
            if (r.data?.cv_text) setCvText(r.data.cv_text);
        }).catch(() => {});

        const jobId = searchParams.get("job_id");
        if (jobId) {
            api.get(`/jobs/${jobId}`).then(r => {
                const j = r.data?.job || r.data;
                if (j) {
                    setJobDesc(j.description || "");
                    setJobTitle(j.title || "");
                    setCompany(j.company || "");
                }
            }).catch(() => {});
        }
    }, []);

    const loadVersions = async () => {
        setVerLoading(true);
        const r = await api.get("/cv/versions").catch(() => ({ data: { versions: [] } }));
        setVersions(r.data.versions || []);
        setVerLoading(false);
    };

    useEffect(() => {
        if (tab === "versions") loadVersions();
    }, [tab]);

    // ── Tailor ──────────────────────────────────────────────────
    const handleTailor = async () => {
        if (!cvText || !jobDesc) return;
        setTailoring(true);
        setTailored(null);
        try {
            const r = await api.post("/cv/tailor", {
                cv_text: cvText, job_description: jobDesc,
                job_title: jobTitle, company,
            });
            setTailored(r.data);
        } catch { alert("Tailoring failed. Try again."); }
        setTailoring(false);
    };

    // ── ATS Score ───────────────────────────────────────────────
    const handleATS = async () => {
        if (!cvText || !jobDesc) return;
        setAtsLoading(true);
        setAtsResult(null);
        try {
            const r = await api.post("/cv/ats-score", {
                cv_text: cvText, job_description: jobDesc,
            });
            setAtsResult(r.data);
        } catch { alert("ATS scoring failed."); }
        setAtsLoading(false);
    };

    // ── Cover Letter ─────────────────────────────────────────────
    const handleCoverLetter = async () => {
        if (!cvText) return;
        setClLoading(true);
        setClResult(null);
        try {
            const r = await api.post("/cv/cover-letter", {
                cv_text: cvText, job_description: jobDesc,
                job_title: jobTitle, company,
                tone: clTone, language: clLang,
            });
            setClResult(r.data);
        } catch { alert("Cover letter generation failed."); }
        setClLoading(false);
    };

    const copyText = (text) => {
        navigator.clipboard.writeText(text);
    };

    const scoreColor = (s) => s >= 75 ? "#10B981" : s >= 50 ? "#FBBF24" : "#EF4444";

    return (
        <div className="px-6 py-8 max-w-6xl mx-auto">
            {/* Header */}
            <div className="mb-8">
                <div className="overline">AI-Powered</div>
                <h1 className="font-display font-black text-4xl tracking-tight mt-2">CV Intelligence</h1>
                <p className="text-zinc-500 text-sm mt-2">
                    Tailor your CV, check ATS score, and generate cover letters for any job.
                </p>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 mb-8 border-b border-zinc-800">
                {[
                    { id: "tailor", label: "CV Tailoring" },
                    { id: "ats",    label: "ATS Score" },
                    { id: "cover-letter", label: "Cover Letter" },
                    { id: "versions", label: "Saved Versions" },
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

            {/* Shared Input Area */}
            {tab !== "versions" && (
                <div className="grid md:grid-cols-2 gap-6 mb-6">
                    <div>
                        <label className="overline mb-2 block">Your CV</label>
                        <textarea value={cvText} onChange={e => setCvText(e.target.value)}
                            placeholder="Paste your CV here or load from profile…"
                            className="w-full h-56 bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3
                                       text-sm text-zinc-200 placeholder:text-zinc-600 resize-none
                                       focus:outline-none focus:border-zinc-700 transition-colors" />
                    </div>
                    <div>
                        <label className="overline mb-2 block">Job Description</label>
                        <textarea value={jobDesc} onChange={e => setJobDesc(e.target.value)}
                            placeholder="Paste the job description here…"
                            className="w-full h-56 bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3
                                       text-sm text-zinc-200 placeholder:text-zinc-600 resize-none
                                       focus:outline-none focus:border-zinc-700 transition-colors" />
                        <div className="flex gap-2 mt-2">
                            <input value={jobTitle} onChange={e => setJobTitle(e.target.value)}
                                placeholder="Job title"
                                className="flex-1 px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg
                                           text-xs text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-700" />
                            <input value={company} onChange={e => setCompany(e.target.value)}
                                placeholder="Company"
                                className="flex-1 px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg
                                           text-xs text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-700" />
                        </div>
                    </div>
                </div>
            )}

            {/* ── TAB: TAILOR ─────────────────────────────────── */}
            {tab === "tailor" && (
                <div>
                    <button onClick={handleTailor} disabled={tailoring || !cvText || !jobDesc}
                        className="flex items-center gap-2 bg-zinc-50 text-black px-5 py-2.5
                                   rounded-lg text-sm font-semibold hover:bg-zinc-200 transition-colors
                                   disabled:opacity-40 disabled:cursor-not-allowed mb-6">
                        <MagicWand size={16} weight="fill" />
                        {tailoring ? "Tailoring your CV…" : "Tailor CV for this Job"}
                    </button>

                    {tailored && (
                        <div className="space-y-6">
                            {/* Tailored CV */}
                            <div className="card-soft p-5">
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="font-display font-bold">Tailored CV</h3>
                                    <button onClick={() => copyText(tailored.tailored_cv)}
                                        className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-200">
                                        <ClipboardText size={13} /> Copy
                                    </button>
                                </div>
                                <pre className="text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed
                                                bg-zinc-950 rounded-lg p-4 max-h-80 overflow-y-auto">
                                    {tailored.tailored_cv}
                                </pre>
                            </div>

                            {/* Changes */}
                            <div className="grid md:grid-cols-2 gap-4">
                                <div className="card-soft p-4">
                                    <h4 className="text-sm font-semibold mb-3 text-green-400">✓ Changes Made</h4>
                                    <ul className="space-y-1.5">
                                        {(tailored.changes_made || []).map((c, i) => (
                                            <li key={i} className="text-xs text-zinc-400 flex gap-2">
                                                <span className="text-green-500 flex-shrink-0">•</span>{c}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                                <div className="card-soft p-4">
                                    <h4 className="text-sm font-semibold mb-3 text-blue-400">Keywords Added</h4>
                                    <div className="flex flex-wrap gap-1.5">
                                        {(tailored.keywords_added || []).map((k, i) => (
                                            <span key={i} className="text-xs px-2 py-0.5 rounded bg-blue-500/10
                                                                       border border-blue-500/20 text-blue-400">{k}</span>
                                        ))}
                                    </div>
                                    {tailored.ats_improvement && (
                                        <p className="text-xs text-zinc-500 mt-3">
                                            Estimated ATS improvement: <span className="text-green-400">{tailored.ats_improvement}</span>
                                        </p>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ── TAB: ATS ─────────────────────────────────────── */}
            {tab === "ats" && (
                <div>
                    <button onClick={handleATS} disabled={atsLoading || !cvText || !jobDesc}
                        className="flex items-center gap-2 bg-zinc-50 text-black px-5 py-2.5
                                   rounded-lg text-sm font-semibold hover:bg-zinc-200 transition-colors
                                   disabled:opacity-40 disabled:cursor-not-allowed mb-6">
                        <CheckCircle size={16} weight="fill" />
                        {atsLoading ? "Analyzing…" : "Check ATS Score"}
                    </button>

                    {atsResult && (
                        <div className="space-y-5">
                            {/* Score */}
                            <div className="card-soft p-5 flex items-center gap-6">
                                <div className="text-center">
                                    <div className="text-6xl font-mono-ui font-bold"
                                         style={{ color: scoreColor(atsResult.score) }}>
                                        {atsResult.score}
                                    </div>
                                    <div className="text-xs text-zinc-500 mt-1">ATS Score</div>
                                </div>
                                <div className="flex-1">
                                    <p className="text-sm text-zinc-300 mb-2">{atsResult.summary}</p>
                                    <div className="w-full bg-zinc-800 rounded-full h-2">
                                        <div className="h-2 rounded-full transition-all duration-700"
                                             style={{ width: `${atsResult.score}%`,
                                                      background: scoreColor(atsResult.score) }} />
                                    </div>
                                </div>
                            </div>

                            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                                {[
                                    { title: "Matching Skills", items: atsResult.matching_skills, color: "green" },
                                    { title: "Missing Skills",  items: atsResult.missing_skills,  color: "red" },
                                    { title: "Strengths",       items: atsResult.strengths,        color: "blue" },
                                    { title: "Improvements",    items: atsResult.improvements,     color: "yellow" },
                                ].map(section => (
                                    <div key={section.title} className="card-soft p-4">
                                        <h4 className={`text-xs font-semibold mb-3 text-${section.color}-400`}>
                                            {section.title}
                                        </h4>
                                        <ul className="space-y-1">
                                            {(section.items || []).slice(0, 5).map((item, i) => (
                                                <li key={i} className="text-xs text-zinc-400">• {item}</li>
                                            ))}
                                        </ul>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ── TAB: COVER LETTER ─────────────────────────────── */}
            {tab === "cover-letter" && (
                <div>
                    <div className="flex gap-3 mb-5">
                        {[
                            { id: "professional", label: "Professional" },
                            { id: "enthusiastic", label: "Enthusiastic" },
                            { id: "concise",      label: "Concise" },
                        ].map(t => (
                            <button key={t.id} onClick={() => setClTone(t.id)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                                    clTone === t.id ? "bg-zinc-200 text-black" : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                                }`}>
                                {t.label}
                            </button>
                        ))}
                        <div className="ml-4 flex gap-2">
                            {[{ id: "en", label: "🇬🇧 EN" },
                              { id: "ar", label: "🇸🇦 AR" },
                              { id: "pt", label: "🇵🇹 PT" }].map(l => (
                                <button key={l.id} onClick={() => setClLang(l.id)}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                                        clLang === l.id ? "bg-zinc-200 text-black" : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                                    }`}>
                                    {l.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    <button onClick={handleCoverLetter} disabled={clLoading || !cvText}
                        className="flex items-center gap-2 bg-zinc-50 text-black px-5 py-2.5
                                   rounded-lg text-sm font-semibold hover:bg-zinc-200 transition-colors
                                   disabled:opacity-40 disabled:cursor-not-allowed mb-6">
                        <FileText size={16} weight="fill" />
                        {clLoading ? "Writing…" : "Generate Cover Letter"}
                    </button>

                    {clResult && (
                        <div className="space-y-4">
                            {clResult.subject_line && (
                                <div className="card-soft p-4">
                                    <p className="text-xs text-zinc-500 mb-1">Email Subject</p>
                                    <p className="text-sm font-medium text-zinc-200">{clResult.subject_line}</p>
                                </div>
                            )}
                            <div className="card-soft p-5">
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="font-display font-bold">Cover Letter</h3>
                                    <button onClick={() => copyText(clResult.cover_letter)}
                                        className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-200">
                                        <ClipboardText size={13} /> Copy
                                    </button>
                                </div>
                                <pre className="text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed">
                                    {clResult.cover_letter}
                                </pre>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ── TAB: VERSIONS ───────────────────────────────── */}
            {tab === "versions" && (
                <div>
                    {verLoading && <p className="text-zinc-500 text-sm">Loading versions…</p>}
                    {!verLoading && versions.length === 0 && (
                        <div className="text-center py-12 text-zinc-500">
                            <FileText size={28} className="mx-auto mb-3 opacity-30" />
                            <p className="text-sm">No saved CV versions yet.</p>
                            <p className="text-xs mt-1">Tailor your CV for a job to save a version.</p>
                        </div>
                    )}
                    <div className="space-y-3">
                        {versions.map(v => (
                            <div key={v.version_id} className="card-soft p-4 flex items-center justify-between gap-4">
                                <div>
                                    <p className="font-semibold text-sm">{v.job_title || "Untitled"}</p>
                                    <p className="text-xs text-zinc-500">{v.job_company} · {new Date(v.created_at).toLocaleDateString()}</p>
                                    {v.keywords_added?.length > 0 && (
                                        <p className="text-xs text-zinc-600 mt-1">
                                            +{v.keywords_added.length} keywords added
                                        </p>
                                    )}
                                </div>
                                <div className="flex items-center gap-2">
                                    <button onClick={() => { setTailored(v); setTab("tailor"); }}
                                        className="text-xs text-zinc-400 hover:text-zinc-200 px-3 py-1.5
                                                   border border-zinc-800 rounded-lg transition-colors">
                                        View
                                    </button>
                                    <button onClick={async () => {
                                        await api.delete(`/cv/versions/${v.version_id}`);
                                        loadVersions();
                                    }} className="text-xs text-red-500 hover:text-red-400 p-1.5">
                                        <Trash size={13} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
