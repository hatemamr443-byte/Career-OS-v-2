import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { ChatCircle, CheckCircle, Warning, Buildings, ArrowRight, Star } from "@phosphor-icons/react";

export default function InterviewPrep() {
    const [searchParams] = useSearchParams();

    // State
    const [tab, setTab]             = useState("prep");
    const [jobDesc, setJobDesc]     = useState("");
    const [jobTitle, setJobTitle]   = useState("");
    const [company, setCompany]     = useState("");
    const [questions, setQuestions] = useState([]);
    const [session, setSession]     = useState(null);
    const [generating, setGenerating] = useState(false);

    // Practice mode
    const [activeQ, setActiveQ]     = useState(null);
    const [answer, setAnswer]       = useState("");
    const [evaluation, setEval]     = useState(null);
    const [evaluating, setEvaluating] = useState(false);

    // Company research
    const [research, setResearch]   = useState(null);
    const [researching, setResearching] = useState(false);

    useEffect(() => {
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

    const handleGenerate = async () => {
        if (!jobTitle && !jobDesc) return;
        setGenerating(true);
        setQuestions([]);
        setSession(null);
        try {
            const r = await api.post("/interview/questions", {
                job_description: jobDesc,
                job_title: jobTitle,
                company,
                count: 10,
            });
            setQuestions(r.data.questions || []);
            setSession(r.data.session_id);
        } catch { alert("Failed to generate questions."); }
        setGenerating(false);
    };

    const handleEvaluate = async () => {
        if (!activeQ || !answer.trim()) return;
        setEvaluating(true);
        setEval(null);
        try {
            const r = await api.post("/interview/evaluate", {
                question: activeQ.question,
                answer,
                session_id: session,
                question_id: activeQ.id,
            });
            setEval(r.data);
        } catch { alert("Evaluation failed."); }
        setEvaluating(false);
    };

    const handleResearch = async () => {
        if (!company) return;
        setResearching(true);
        setResearch(null);
        try {
            const r = await api.get(`/interview/company-research?company=${encodeURIComponent(company)}&role=${encodeURIComponent(jobTitle)}`);
            setResearch(r.data);
        } catch { alert("Research failed."); }
        setResearching(false);
    };

    const scoreColor = (s) => s >= 8 ? "#10B981" : s >= 5 ? "#FBBF24" : "#EF4444";
    const diffColor  = (d) => d === "hard" ? "#EF4444" : d === "medium" ? "#FBBF24" : "#10B981";

    return (
        <div className="px-6 py-8 max-w-6xl mx-auto">
            <div className="mb-8">
                <div className="overline">AI Interview Coach</div>
                <h1 className="font-display font-black text-4xl tracking-tight mt-2">Interview Prep</h1>
                <p className="text-zinc-500 text-sm mt-2">Practice with AI-generated questions tailored to the job.</p>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 mb-8 border-b border-zinc-800">
                {[
                    { id: "prep",     label: "Question Generator" },
                    { id: "practice", label: "Practice Mode" },
                    { id: "research", label: "Company Research" },
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

            {/* Job Input */}
            {(tab === "prep" || tab === "practice") && (
                <div className="grid md:grid-cols-3 gap-3 mb-6">
                    <input value={jobTitle} onChange={e => setJobTitle(e.target.value)}
                        placeholder="Job title *"
                        className="px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                                   text-sm text-zinc-200 placeholder:text-zinc-600
                                   focus:outline-none focus:border-zinc-700" />
                    <input value={company} onChange={e => setCompany(e.target.value)}
                        placeholder="Company"
                        className="px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                                   text-sm text-zinc-200 placeholder:text-zinc-600
                                   focus:outline-none focus:border-zinc-700" />
                    <button onClick={handleGenerate} disabled={generating || !jobTitle}
                        className="flex items-center justify-center gap-2 bg-zinc-50 text-black
                                   rounded-lg text-sm font-semibold hover:bg-zinc-200 transition-colors
                                   disabled:opacity-40 disabled:cursor-not-allowed">
                        <ChatCircle size={15} weight="fill" />
                        {generating ? "Generating…" : "Generate Questions"}
                    </button>
                </div>
            )}

            {/* ── PREP TAB ──────────────────────────────────── */}
            {tab === "prep" && (
                <div>
                    {/* Job description input */}
                    <textarea value={jobDesc} onChange={e => setJobDesc(e.target.value)}
                        placeholder="Paste job description for more targeted questions…"
                        className="w-full h-28 bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3
                                   text-sm text-zinc-200 placeholder:text-zinc-600 resize-none
                                   focus:outline-none focus:border-zinc-700 mb-6" />

                    {questions.length === 0 && !generating && (
                        <div className="text-center py-12 text-zinc-500">
                            <ChatCircle size={28} className="mx-auto mb-3 opacity-30" />
                            <p className="text-sm">Enter a job title and click Generate</p>
                        </div>
                    )}

                    <div className="space-y-3">
                        {questions.map((q, i) => (
                            <div key={q.id} className="card-soft p-4">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="font-mono-ui text-xs text-zinc-600">#{i + 1}</span>
                                            <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">{q.type}</span>
                                            <span className="text-xs" style={{ color: diffColor(q.difficulty) }}>
                                                {q.difficulty}
                                            </span>
                                        </div>
                                        <p className="text-sm font-medium text-zinc-200 leading-relaxed">{q.question}</p>
                                        {q.tips && (
                                            <p className="text-xs text-zinc-500 mt-2">💡 {q.tips}</p>
                                        )}
                                    </div>
                                    <button onClick={() => { setActiveQ(q); setAnswer(""); setEval(null); setTab("practice"); }}
                                        className="flex-shrink-0 text-xs text-zinc-400 hover:text-zinc-200 border
                                                   border-zinc-800 rounded-lg px-3 py-1.5 hover:border-zinc-700 transition-colors">
                                        Practice
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ── PRACTICE TAB ─────────────────────────────── */}
            {tab === "practice" && (
                <div>
                    {!activeQ && questions.length === 0 && (
                        <div className="text-center py-12 text-zinc-500">
                            <p className="text-sm">Generate questions first, then select one to practice.</p>
                        </div>
                    )}

                    {!activeQ && questions.length > 0 && (
                        <div className="space-y-2">
                            <p className="text-sm text-zinc-500 mb-4">Select a question to practice:</p>
                            {questions.map((q, i) => (
                                <button key={q.id} onClick={() => { setActiveQ(q); setAnswer(""); setEval(null); }}
                                    className="w-full text-left card-soft p-4 hover:border-zinc-700 transition-colors">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="font-mono-ui text-xs text-zinc-600">#{i + 1}</span>
                                        <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">{q.type}</span>
                                    </div>
                                    <p className="text-sm text-zinc-200">{q.question}</p>
                                </button>
                            ))}
                        </div>
                    )}

                    {activeQ && (
                        <div className="space-y-5">
                            {/* Question */}
                            <div className="card-soft p-5 border-l-4 border-blue-500">
                                <div className="flex items-center gap-2 mb-3">
                                    <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">{activeQ.type}</span>
                                    <span className="text-xs text-zinc-600">{activeQ.why_asked}</span>
                                </div>
                                <p className="font-medium text-zinc-100 text-base">{activeQ.question}</p>
                                {activeQ.tips && (
                                    <p className="text-xs text-zinc-500 mt-3">💡 Tip: {activeQ.tips}</p>
                                )}
                            </div>

                            {/* Answer */}
                            <div>
                                <label className="overline mb-2 block">Your Answer</label>
                                <textarea value={answer} onChange={e => setAnswer(e.target.value)}
                                    placeholder="Type your answer here… (Use STAR method: Situation, Task, Action, Result)"
                                    className="w-full h-40 bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3
                                               text-sm text-zinc-200 placeholder:text-zinc-600 resize-none
                                               focus:outline-none focus:border-zinc-700" />
                                <div className="flex gap-3 mt-3">
                                    <button onClick={handleEvaluate} disabled={evaluating || !answer.trim()}
                                        className="flex items-center gap-2 bg-zinc-50 text-black px-4 py-2
                                                   rounded-lg text-sm font-semibold hover:bg-zinc-200 transition-colors
                                                   disabled:opacity-40">
                                        <Star size={14} weight="fill" />
                                        {evaluating ? "Evaluating…" : "Get AI Feedback"}
                                    </button>
                                    <button onClick={() => { setActiveQ(null); setEval(null); }}
                                        className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors">
                                        ← Back to questions
                                    </button>
                                </div>
                            </div>

                            {/* Evaluation */}
                            {evaluation && (
                                <div className="space-y-4">
                                    <div className="card-soft p-5 flex items-center gap-4">
                                        <div className="text-center">
                                            <div className="text-5xl font-mono-ui font-bold"
                                                 style={{ color: scoreColor(evaluation.score) }}>
                                                {evaluation.score}/10
                                            </div>
                                            <div className={`text-xs mt-1 font-semibold ${
                                                evaluation.verdict === "strong" ? "text-green-400" :
                                                evaluation.verdict === "acceptable" ? "text-yellow-400" : "text-red-400"
                                            }`}>{evaluation.verdict}</div>
                                        </div>
                                        <p className="flex-1 text-sm text-zinc-300 leading-relaxed">{evaluation.feedback}</p>
                                    </div>

                                    <div className="grid md:grid-cols-2 gap-4">
                                        {evaluation.strengths?.length > 0 && (
                                            <div className="card-soft p-4">
                                                <h4 className="text-xs font-semibold text-green-400 mb-2">What worked</h4>
                                                <ul className="space-y-1">
                                                    {evaluation.strengths.map((s, i) => (
                                                        <li key={i} className="text-xs text-zinc-400">✓ {s}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        {evaluation.improvements?.length > 0 && (
                                            <div className="card-soft p-4">
                                                <h4 className="text-xs font-semibold text-yellow-400 mb-2">Improve this</h4>
                                                <ul className="space-y-1">
                                                    {evaluation.improvements.map((s, i) => (
                                                        <li key={i} className="text-xs text-zinc-400">• {s}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>

                                    {evaluation.better_answer && (
                                        <div className="card-soft p-4">
                                            <h4 className="text-xs font-semibold text-blue-400 mb-2">A stronger answer</h4>
                                            <p className="text-sm text-zinc-300 leading-relaxed">{evaluation.better_answer}</p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* ── RESEARCH TAB ────────────────────────────── */}
            {tab === "research" && (
                <div>
                    <div className="flex gap-3 mb-6">
                        <input value={company} onChange={e => setCompany(e.target.value)}
                            placeholder="Company name *"
                            className="flex-1 px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                                       text-sm text-zinc-200 placeholder:text-zinc-600
                                       focus:outline-none focus:border-zinc-700" />
                        <input value={jobTitle} onChange={e => setJobTitle(e.target.value)}
                            placeholder="Role (optional)"
                            className="flex-1 px-3 py-2.5 bg-zinc-900 border border-zinc-800 rounded-lg
                                       text-sm text-zinc-200 placeholder:text-zinc-600
                                       focus:outline-none focus:border-zinc-700" />
                        <button onClick={handleResearch} disabled={researching || !company}
                            className="flex items-center gap-2 bg-zinc-50 text-black px-4 py-2.5
                                       rounded-lg text-sm font-semibold hover:bg-zinc-200 transition-colors
                                       disabled:opacity-40">
                            <Buildings size={15} weight="fill" />
                            {researching ? "Researching…" : "Research"}
                        </button>
                    </div>

                    {research && (
                        <div className="space-y-4">
                            <div className="card-soft p-5">
                                <h3 className="font-display font-bold mb-2">{research.company}</h3>
                                <p className="text-sm text-zinc-300 leading-relaxed">{research.company_overview}</p>
                            </div>

                            <div className="grid md:grid-cols-2 gap-4">
                                {[
                                    { title: "Culture Notes",         items: research.culture_notes,           color: "blue"   },
                                    { title: "Interview Process",     items: research.typical_interview_process, color: "purple" },
                                    { title: "Things to Mention",     items: research.things_to_mention,        color: "green"  },
                                    { title: "Common Questions",      items: research.common_interview_questions, color: "yellow" },
                                    { title: "Employee Themes",       items: research.glassdoor_themes,          color: "zinc"   },
                                    { title: "Prep Tips",             items: research.prep_tips,                 color: "blue"   },
                                ].map(s => s.items?.length > 0 && (
                                    <div key={s.title} className="card-soft p-4">
                                        <h4 className={`text-xs font-semibold text-${s.color}-400 mb-3`}>{s.title}</h4>
                                        <ul className="space-y-1.5">
                                            {s.items.map((item, i) => (
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
        </div>
    );
}
