import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Link } from "react-router-dom";
import { CheckCircle, WarningCircle } from "@phosphor-icons/react";

export default function ProfileCompleteness() {
    const [data, setData] = useState(null);

    useEffect(() => {
        api.get("/profile/completeness").then(r => setData(r.data)).catch(() => {});
    }, []);

    if (!data) return null;

    const { percent, suggestions, status } = data;
    const color = percent >= 80 ? "#10B981" : percent >= 40 ? "#FBBF24" : "#EF4444";

    return (
        <div className="card-soft p-4 space-y-3">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    {percent >= 80
                        ? <CheckCircle size={16} weight="fill" color="#10B981" />
                        : <WarningCircle size={16} weight="fill" color={color} />
                    }
                    <span className="text-sm font-semibold text-zinc-200">Profile Strength</span>
                </div>
                <span className="font-mono-ui text-sm" style={{ color }}>{percent}%</span>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-zinc-800 rounded-full h-1.5">
                <div
                    className="h-1.5 rounded-full transition-all duration-700"
                    style={{ width: `${percent}%`, background: color }}
                />
            </div>

            {/* Suggestions */}
            {suggestions.length > 0 && percent < 100 && (
                <div className="space-y-1">
                    {suggestions.slice(0, 2).map((s, i) => (
                        <p key={i} className="text-xs text-zinc-500">• {s}</p>
                    ))}
                    <Link to="/profile" className="text-xs text-zinc-400 hover:text-white transition-colors">
                        Edit profile →
                    </Link>
                </div>
            )}
            {percent >= 100 && (
                <p className="text-xs text-green-400">Your profile is complete ✓</p>
            )}
        </div>
    );
}
