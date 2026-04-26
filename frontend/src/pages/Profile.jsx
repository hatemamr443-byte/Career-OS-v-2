import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Sparkle } from "@phosphor-icons/react";

export default function Profile() {
    const [profile, setProfile] = useState(null);
    const [parsing, setParsing] = useState(false);
    const [saved, setSaved] = useState(false);

    useEffect(() => { load(); }, []);
    const load = async () => {
        try {
            const r = await api.get("/profile");
            setProfile(r.data || { cv_text: "", headline: "", skills: [], target_roles: [] });
        } catch {
            setProfile({ cv_text: "", headline: "", skills: [], target_roles: [] });
        }
    };

    const parseCV = async () => {
        setParsing(true);
        try {
            const r = await api.post("/profile/parse-cv", { cv_text: profile.cv_text });
            setProfile(r.data);
            flashSaved();
        } catch {}
        setParsing(false);
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
                    <div className="flex items-center justify-between mb-2">
                        <label className="overline">CV / Resume</label>
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
                    <textarea
                        className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm font-mono leading-relaxed focus:outline-none focus:border-zinc-600 min-h-[400px]"
                        value={profile.cv_text || ""}
                        onChange={(e) => setProfile({ ...profile, cv_text: e.target.value })}
                        placeholder="Paste your CV here…"
                        data-testid="profile-cv-textarea"
                    />
                </div>
            </div>
        </div>
    );
}
