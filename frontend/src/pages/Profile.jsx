import { useEffect, useState, useCallback, useRef } from "react";
import { api } from "../lib/api";
import { Sparkle, UploadSimple, EnvelopeSimple, CheckCircle, Warning } from "@phosphor-icons/react";

export default function Profile() {
    const [profile, setProfile] = useState(null);
    const [parsing, setParsing] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [uploadError, setUploadError] = useState(null);
    const [saved, setSaved] = useState(false);
    const [sendingTest, setSendingTest] = useState(false);
    const [testResult, setTestResult] = useState(null);
    const fileInputRef = useRef(null);

    const load = useCallback(async () => {
        try {
            const r = await api.get("/profile");
            setProfile(r.data || { cv_text: "", headline: "", skills: [], target_roles: [] });
        } catch (err) {
            console.error("profile load failed:", err);
            setProfile({ cv_text: "", headline: "", skills: [], target_roles: [] });
        }
    }, []);

    useEffect(() => {
        load();
    }, [load]);

    const parseCV = async () => {
        setParsing(true);
        try {
            const r = await api.post("/profile/parse-cv", { cv_text: profile.cv_text });
            setProfile(r.data);
            flashSaved();
        } catch (err) {
            console.error("parse-cv failed:", err);
        }
        setParsing(false);
    };

    const uploadPdf = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true);
        setUploadError(null);
        const fd = new FormData();
        fd.append("file", file);
        try {
            const r = await api.post("/profile/upload-cv", fd, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            setProfile(r.data);
            flashSaved();
        } catch (err) {
            console.error("upload-cv failed:", err);
            const detail = err.response?.data?.detail;
            setUploadError(typeof detail === "string" ? detail : "Upload failed. Please try a text-based PDF.");
        }
        setUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    const save = async () => {
        const { cv_text, headline, skills, target_roles, target_locations, salary_min, years_experience } = profile;
        const r = await api.put("/profile", { cv_text, headline, skills, target_roles, target_locations, salary_min, years_experience });
        setProfile(r.data);
        flashSaved();
    };

    const flashSaved = () => {
        setSaved(true);
        setTimeout(() => setSaved(false), 1800);
    };

    const toggleDaily = async () => {
        const next = !profile.daily_matches;
        setProfile({ ...profile, daily_matches: next });
        try {
            await api.put("/profile/notifications", { daily_matches: next });
            flashSaved();
        } catch (err) {
            console.error("toggle daily failed:", err);
            setProfile({ ...profile, daily_matches: !next });
        }
    };

    const sendTestDigest = async () => {
        setSendingTest(true);
        setTestResult(null);
        try {
            const r = await api.post("/profile/notifications/test", {});
            setTestResult(r.data);
        } catch (err) {
            console.error("test digest failed:", err);
            setTestResult({ sent: false, reason: err.response?.data?.detail || "Failed" });
        }
        setSendingTest(false);
    };

    if (!profile) return <div className="p-8 text-zinc-500">Loading…</div>;

    return (
        <div className="px-8 py-8 max-w-5xl mx-auto" data-testid="profile-page">
            <div className="overline">Identity</div>
            <h1 className="font-display font-black text-4xl tracking-tight mt-2 mb-8">Your Profile</h1>

            {/* Daily digest toggle */}
            <div className="card-soft p-5 mb-6" data-testid="notifications-card">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                        <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center flex-shrink-0">
                            <EnvelopeSimple size={18} weight="duotone" color="#007AFF" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="font-display font-bold text-lg tracking-tight">Get daily job matches</div>
                            <div className="text-sm text-zinc-400 mt-0.5">
                                We'll email you the top 3 new jobs matching your CV — every 24h. Fresh data from Adzuna, Jooble and Remotive.
                            </div>
                        </div>
                    </div>
                    {/* Toggle */}
                    <button
                        onClick={toggleDaily}
                        data-testid="daily-matches-toggle"
                        aria-pressed={!!profile.daily_matches}
                        className={`relative w-12 h-7 rounded-full transition-colors flex-shrink-0 ${
                            profile.daily_matches ? "bg-emerald-500" : "bg-zinc-700"
                        }`}
                    >
                        <span
                            className={`absolute top-0.5 left-0.5 w-6 h-6 rounded-full bg-zinc-50 transition-transform ${
                                profile.daily_matches ? "translate-x-5" : ""
                            }`}
                        />
                    </button>
                </div>
                {profile.daily_matches && (
                    <div className="mt-4 pt-4 border-t border-zinc-800 flex items-center gap-2 flex-wrap">
                        <button
                            onClick={sendTestDigest}
                            disabled={sendingTest}
                            data-testid="send-test-digest"
                            className="border border-zinc-700 hover:border-zinc-500 transition-colors rounded-lg px-3 py-1.5 text-xs disabled:opacity-50"
                        >
                            {sendingTest ? "Sending…" : "Send a test now"}
                        </button>
                        {profile.last_email_sent && (
                            <span className="text-xs text-zinc-500 font-mono-ui">
                                last sent {new Date(profile.last_email_sent).toLocaleString()}
                            </span>
                        )}
                        {testResult && (
                            <span
                                data-testid="test-digest-result"
                                className={`text-xs flex items-center gap-1 ${testResult.sent ? "text-emerald-400" : "text-amber-400"}`}
                            >
                                {testResult.sent ? <CheckCircle size={12} weight="fill" /> : <Warning size={12} weight="fill" />}
                                {testResult.sent
                                    ? `Sent (${testResult.jobs_sent} jobs)`
                                    : testResult.reason || "Not sent"}
                            </span>
                        )}
                    </div>
                )}
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
                <div className="card-soft p-6">
                    <label className="overline">Headline</label>
                    <input
                        className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 mt-2 text-sm focus:outline-none focus:border-zinc-600"
                        value={profile.headline || ""}
                        onChange={(e) => setProfile({ ...profile, headline: e.target.value })}
                        data-testid="profile-headline-input"
                    />

                    <label className="overline mt-5 block">Years of experience</label>
                    <input
                        type="number"
                        className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 mt-2 text-sm focus:outline-none focus:border-zinc-600"
                        value={profile.years_experience || ""}
                        onChange={(e) => setProfile({ ...profile, years_experience: e.target.value ? parseInt(e.target.value) : null })}
                        data-testid="profile-years-input"
                    />

                    <label className="overline mt-5 block">Skills (comma separated)</label>
                    <input
                        className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 mt-2 text-sm focus:outline-none focus:border-zinc-600"
                        value={(profile.skills || []).join(", ")}
                        onChange={(e) => setProfile({ ...profile, skills: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
                        data-testid="profile-skills-input"
                    />

                    <label className="overline mt-5 block">Target roles</label>
                    <input
                        className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 mt-2 text-sm focus:outline-none focus:border-zinc-600"
                        value={(profile.target_roles || []).join(", ")}
                        onChange={(e) => setProfile({ ...profile, target_roles: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
                        data-testid="profile-roles-input"
                    />

                    <button
                        onClick={save}
                        data-testid="profile-save-btn"
                        className="mt-6 bg-zinc-50 text-black hover:bg-zinc-200 transition-colors rounded-lg px-4 py-2 text-sm font-medium"
                    >
                        Save profile
                    </button>
                    {saved && <span className="ml-3 text-xs text-emerald-400">Saved</span>}
                </div>

                <div className="card-soft p-6">
                    <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                        <label className="overline">CV / Resume</label>
                        <div className="flex items-center gap-2">
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="application/pdf"
                                onChange={uploadPdf}
                                className="hidden"
                                data-testid="cv-file-input"
                            />
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                disabled={uploading}
                                data-testid="upload-pdf-btn"
                                className="border border-zinc-700 text-zinc-200 hover:border-zinc-500 transition-colors rounded-lg px-3 py-1.5 text-xs flex items-center gap-2 disabled:opacity-50"
                            >
                                <UploadSimple size={12} weight="bold" />
                                {uploading ? "Uploading…" : "Upload PDF"}
                            </button>
                            <button
                                onClick={parseCV}
                                disabled={parsing || !profile.cv_text?.trim()}
                                data-testid="parse-cv-btn"
                                className="bg-blue-600/10 text-blue-400 border border-blue-500/20 hover:bg-blue-600/20 transition-colors rounded-lg px-3 py-1.5 text-xs flex items-center gap-2 disabled:opacity-50"
                            >
                                <Sparkle size={12} weight="fill" />
                                {parsing ? "Parsing…" : "Parse with Claude"}
                            </button>
                        </div>
                    </div>
                    {profile.cv_filename && (
                        <div className="text-xs text-zinc-500 mb-2 font-mono-ui" data-testid="cv-filename">
                            Uploaded: {profile.cv_filename}
                        </div>
                    )}
                    {uploadError && (
                        <div className="mb-2 p-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs" data-testid="upload-error">
                            {uploadError}
                        </div>
                    )}
                    <textarea
                        className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm font-mono leading-relaxed focus:outline-none focus:border-zinc-600 min-h-[400px]"
                        value={profile.cv_text || ""}
                        onChange={(e) => setProfile({ ...profile, cv_text: e.target.value })}
                        placeholder="Paste your CV here, or upload a PDF above…"
                        data-testid="profile-cv-textarea"
                    />
                </div>
            </div>
        </div>
    );
}
