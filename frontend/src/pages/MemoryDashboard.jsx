import React, { useEffect, useState } from "react";
import axios from "axios";

const BACKEND = process.env.REACT_APP_BACKEND_URL || "";

const EPISODE_COLORS = {
  milestone:  { bg: "#d1fae5", text: "#065f46", border: "#6ee7b7" },
  decision:   { bg: "#dbeafe", text: "#1e40af", border: "#93c5fd" },
  failure:    { bg: "#fee2e2", text: "#991b1b", border: "#fca5a5" },
  session:    { bg: "#f3e8ff", text: "#6b21a8", border: "#d8b4fe" },
  insight:    { bg: "#fef3c7", text: "#92400e", border: "#fcd34d" },
};

const EPISODE_ICONS = {
  milestone: "🏆", decision: "🎯", failure: "⚡", session: "💬", insight: "💡",
};

export default function MemoryDashboard() {
  const [stats, setStats]       = useState(null);
  const [episodes, setEpisodes] = useState([]);
  const [working, setWorking]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [filter, setFilter]     = useState("");
  const [error, setError]       = useState("");

  const token = localStorage.getItem("session_token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchAll();
  }, []);

  async function fetchAll() {
    setLoading(true);
    setError("");
    try {
      const [statsR, epR, wkR] = await Promise.all([
        axios.get(`${BACKEND}/api/memory/stats`, { headers }),
        axios.get(`${BACKEND}/api/memory/episodes?k=30`, { headers }),
        axios.get(`${BACKEND}/api/memory/working`, { headers }),
      ]);
      setStats(statsR.data);
      setEpisodes(epR.data.episodes || []);
      setWorking(wkR.data.snippets || []);
    } catch (ex) {
      setError("Failed to load memory data.");
    } finally {
      setLoading(false);
    }
  }

  async function deleteEpisode(id) {
    try {
      await axios.delete(`${BACKEND}/api/memory/episodes/${id}`, { headers });
      setEpisodes(eps => eps.filter(e => e.episode_id !== id));
    } catch { /* ignore */ }
  }

  async function triggerConsolidation() {
    try {
      await axios.post(`${BACKEND}/api/memory/consolidate`, {}, { headers });
      alert("Memory consolidation started — AI notes will update shortly.");
    } catch { /* ignore */ }
  }

  const filtered = filter
    ? episodes.filter(e => e.episode_type === filter)
    : episodes;

  if (loading) return (
    <div style={{ padding: 32, textAlign: "center", color: "#6b7280" }}>
      Loading memory system...
    </div>
  );

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "24px 16px" }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#111827", marginBottom: 4 }}>
          Career Memory
        </h1>
        <p style={{ color: "#6b7280", fontSize: 14 }}>
          Persistent intelligence from your career journey.
        </p>
        {error && (
          <div style={{ background: "#fee2e2", color: "#991b1b", padding: "8px 12px",
                        borderRadius: 8, marginTop: 12, fontSize: 13 }}>
            {error}
          </div>
        )}
      </div>

      {/* Stats row */}
      {stats && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
                      gap: 12, marginBottom: 28 }}>
          {[
            { label: "Episodes",      value: stats.episodes,      icon: "📚" },
            { label: "Career Events", value: stats.career_events, icon: "📊" },
            { label: "Activities",    value: stats.activity_logs, icon: "⚡" },
            { label: "Session Items", value: working.length,      icon: "💭" },
          ].map(({ label, value, icon }) => (
            <div key={label} style={{ background: "#f9fafb", border: "1px solid #e5e7eb",
                                      borderRadius: 10, padding: "14px 16px" }}>
              <div style={{ fontSize: 20, marginBottom: 4 }}>{icon}</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: "#111827" }}>{value ?? "—"}</div>
              <div style={{ fontSize: 12, color: "#6b7280" }}>{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* AI Notes */}
      {stats?.ai_notes && (
        <div style={{ background: "#fffbeb", border: "1px solid #fcd34d",
                      borderRadius: 10, padding: 16, marginBottom: 24 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#92400e", marginBottom: 6 }}>
            🧠 AI Career Intelligence Notes
          </div>
          <p style={{ fontSize: 13, color: "#78350f", lineHeight: 1.6, margin: 0 }}>
            {stats.ai_notes}
          </p>
          {stats.notes_updated_at && (
            <div style={{ fontSize: 11, color: "#b45309", marginTop: 8 }}>
              Updated {stats.notes_updated_at.slice(0, 10)}
            </div>
          )}
        </div>
      )}

      {/* Active Session */}
      {working.length > 0 && (
        <div style={{ background: "#f0fdf4", border: "1px solid #86efac",
                      borderRadius: 10, padding: 16, marginBottom: 24 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#166534", marginBottom: 8 }}>
            ⚡ Active Session Context
          </div>
          {working.map((s, i) => (
            <div key={i} style={{ fontSize: 12, color: "#15803d", marginBottom: 4 }}>• {s}</div>
          ))}
        </div>
      )}

      {/* Episodes */}
      <div style={{ display: "flex", justifyContent: "space-between",
                    alignItems: "center", marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {["", "milestone", "decision", "failure", "session", "insight"].map(t => (
            <button key={t} onClick={() => setFilter(t)}
              style={{
                padding: "5px 12px", borderRadius: 20, fontSize: 12,
                cursor: "pointer", border: "1px solid",
                background: filter === t ? "#111827" : "white",
                color: filter === t ? "white" : "#374151",
                borderColor: filter === t ? "#111827" : "#d1d5db",
              }}>
              {t ? `${EPISODE_ICONS[t]} ${t}` : "All"}
            </button>
          ))}
        </div>
        <button onClick={triggerConsolidation}
          style={{ padding: "6px 14px", borderRadius: 8, fontSize: 12,
                   background: "#6366f1", color: "white", border: "none", cursor: "pointer" }}>
          🔄 Consolidate
        </button>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {filtered.length === 0 && (
          <div style={{ color: "#6b7280", fontSize: 13, textAlign: "center", padding: 32 }}>
            No episodes yet. They'll appear automatically as you use Career OS.
          </div>
        )}
        {filtered.map(ep => {
          const color = EPISODE_COLORS[ep.episode_type] || EPISODE_COLORS.session;
          const icon  = EPISODE_ICONS[ep.episode_type] || "📌";
          return (
            <div key={ep.episode_id}
              style={{ border: `1px solid ${color.border}`, borderRadius: 10,
                       background: color.bg, padding: "14px 16px",
                       display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 16 }}>{icon}</span>
                  <span style={{ fontWeight: 600, fontSize: 14, color: color.text }}>
                    {ep.title}
                  </span>
                  <span style={{ fontSize: 11, background: "white", color: color.text,
                                 padding: "1px 7px", borderRadius: 20, border: `1px solid ${color.border}` }}>
                    {ep.episode_type}
                  </span>
                </div>
                <p style={{ fontSize: 13, color: "#374151", margin: "0 0 6px 24px",
                            lineHeight: 1.5 }}>
                  {ep.summary}
                </p>
                <div style={{ fontSize: 11, color: "#9ca3af", marginLeft: 24 }}>
                  {ep.created_at?.slice(0, 10)} · importance {Math.round((ep.importance || 0) * 100)}%
                  {ep.tags?.length > 0 && ` · ${ep.tags.join(", ")}`}
                </div>
              </div>
              <button onClick={() => deleteEpisode(ep.episode_id)}
                style={{ marginLeft: 12, color: "#9ca3af", background: "none",
                         border: "none", cursor: "pointer", fontSize: 16, padding: 4 }}
                title="Delete">
                ×
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
