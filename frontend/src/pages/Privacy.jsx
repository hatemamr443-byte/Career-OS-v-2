import { useState, useEffect } from "react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { ShieldCheck, DownloadSimple, Trash, Warning } from "@phosphor-icons/react";

export default function Privacy() {
    const { user }              = useAuth();
    const [summary, setSummary] = useState(null);
    const [deleting, setDeleting] = useState(false);
    const [confirm, setConfirm] = useState("");

    useEffect(() => {
        api.get("/me/data-summary").then(r => setSummary(r.data)).catch(() => {});
    }, []);

    const exportData = () => {
        window.open(
            `${process.env.REACT_APP_BACKEND_URL}/api/me/export-data`,
            "_blank"
        );
    };

    const delete_account = async () => {
        if (confirm !== "DELETE") return;
        setDeleting(true);
        try {
            await api.delete("/me/account");
            window.location.href = "/?deleted=1";
        } catch {
            setDeleting(false);
        }
    };

    return (
        <div className="px-6 py-8 max-w-2xl mx-auto">
            <div className="mb-8">
                <div className="overline">Account</div>
                <h1 className="font-display font-black text-4xl tracking-tight mt-2">
                    Privacy & Data
                </h1>
                <p className="text-zinc-500 text-sm mt-2">
                    GDPR-compliant. Your data belongs to you.
                </p>
            </div>

            {/* Data Summary */}
            {summary && (
                <div className="card-soft p-5 mb-6">
                    <div className="flex items-center gap-2 mb-4">
                        <ShieldCheck size={16} weight="fill" color="#10B981" />
                        <h3 className="font-semibold text-sm">What we hold about you</h3>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        {Object.entries(summary.data_held || {}).map(([k, v]) => (
                            <div key={k} className="flex justify-between text-xs py-1.5
                                                     border-b border-zinc-800">
                                <span className="text-zinc-500 capitalize">
                                    {k.replace(/_/g, " ")}
                                </span>
                                <span className="font-mono-ui text-zinc-300">{v}</span>
                            </div>
                        ))}
                    </div>
                    <p className="text-xs text-zinc-600 mt-3">
                        Member since: {summary.member_since
                            ? new Date(summary.member_since).toLocaleDateString()
                            : "unknown"}
                    </p>
                </div>
            )}

            {/* Export */}
            <div className="card-soft p-5 mb-4">
                <div className="flex items-center justify-between">
                    <div>
                        <h3 className="font-semibold text-sm mb-1">Export your data</h3>
                        <p className="text-xs text-zinc-500">
                            Download a ZIP of all your Career OS data.
                        </p>
                    </div>
                    <button onClick={exportData}
                        className="flex items-center gap-2 bg-zinc-800 border border-zinc-700
                                   text-zinc-200 text-sm px-4 py-2 rounded-lg
                                   hover:bg-zinc-700 transition-colors flex-shrink-0">
                        <DownloadSimple size={14} weight="fill" />
                        Export
                    </button>
                </div>
            </div>

            {/* Consent */}
            <div className="card-soft p-5 mb-6">
                <h3 className="font-semibold text-sm mb-3">Privacy preferences</h3>
                {[
                    { key: "analytics",       label: "Usage analytics",      desc: "Help improve Career OS" },
                    { key: "marketing_emails", label: "Marketing emails",     desc: "Product updates and tips" },
                ].map(pref => (
                    <div key={pref.key} className="flex items-center justify-between py-2
                                                    border-b border-zinc-800 last:border-0">
                        <div>
                            <p className="text-sm text-zinc-200">{pref.label}</p>
                            <p className="text-xs text-zinc-500">{pref.desc}</p>
                        </div>
                        <input type="checkbox" defaultChecked
                            onChange={async e => {
                                await api.patch("/me/consent", { [pref.key]: e.target.checked })
                                    .catch(() => {});
                            }}
                            className="w-4 h-4 accent-zinc-200" />
                    </div>
                ))}
            </div>

            {/* Delete Account */}
            <div className="card-soft p-5 border border-red-500/20">
                <div className="flex items-center gap-2 mb-3">
                    <Warning size={15} weight="fill" color="#EF4444" />
                    <h3 className="font-semibold text-sm text-red-400">Delete account</h3>
                </div>
                <p className="text-xs text-zinc-500 mb-4">
                    Permanently deletes your account and all data. This cannot be undone.
                </p>
                <div className="space-y-2">
                    <input value={confirm} onChange={e => setConfirm(e.target.value)}
                        placeholder='Type "DELETE" to confirm'
                        className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800
                                   rounded-lg text-sm text-zinc-200 placeholder:text-zinc-600
                                   focus:outline-none focus:border-red-500/50" />
                    <button onClick={delete_account}
                        disabled={confirm !== "DELETE" || deleting}
                        className="w-full flex items-center justify-center gap-2
                                   bg-red-500/10 border border-red-500/30 text-red-400
                                   text-sm py-2 rounded-lg hover:bg-red-500/20 transition-colors
                                   disabled:opacity-30 disabled:cursor-not-allowed">
                        <Trash size={14} weight="fill" />
                        {deleting ? "Deleting…" : "Delete my account permanently"}
                    </button>
                </div>
            </div>

            <p className="text-xs text-zinc-600 mt-6 text-center">
                Questions? Email{" "}
                <a href="mailto:privacy@career-os.io"
                   className="text-zinc-400 hover:text-zinc-200 transition-colors">
                    privacy@career-os.io
                </a>
            </p>
        </div>
    );
}
