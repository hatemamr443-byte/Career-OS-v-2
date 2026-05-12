import { useEffect, useState, useCallback, useRef } from "react";
import { api } from "../lib/api";
import { Sparkle, UploadSimple } from "@phosphor-icons/react";

export default function Profile() {
    const [profile, setProfile] = useState(null);
    const [parsing, setParsing] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [uploadError, setUploadError] = useState(null);
    const [saved, setSaved] = useState(false);
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

    if (!profile) return <div className="p-8 text-zinc-500">Loading…</div>;

    return (
        <div className="px-8 py-8 max-w-5xl mx-auto" data-testid="profile-page">
            <div className="overline">Identity</div>
            <h1 className="font-display font-black text-4xl tracking-tight mt-2 mb-8">Your Profile</h1>

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
