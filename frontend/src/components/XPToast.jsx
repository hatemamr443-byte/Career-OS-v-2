import { useEffect, useState } from "react";

/**
 * XPToast — shows a brief "+25 XP" popup after meaningful actions.
 * Usage: <XPToast amount={25} label="Applied" visible={showXP} onDone={() => setShowXP(false)} />
 */
export default function XPToast({ amount, label, visible, onDone }) {
  const [out, setOut] = useState(false);

  useEffect(() => {
    if (!visible) return;
    setOut(false);
    const hide = setTimeout(() => setOut(true), 2000);
    const done = setTimeout(() => onDone?.(), 2600);
    return () => { clearTimeout(hide); clearTimeout(done); };
  }, [visible, onDone]);

  if (!visible) return null;

  return (
    <div
      className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3
                 bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl
                 transition-all duration-500"
      style={{
        opacity: out ? 0 : 1,
        transform: out ? "translateY(8px)" : "translateY(0)",
      }}
      data-testid="xp-toast"
    >
      <div className="w-8 h-8 rounded-full bg-yellow-400/15 border border-yellow-400/30
                      flex items-center justify-center text-base">
        ⚡
      </div>
      <div>
        <p className="font-mono-ui text-sm font-bold text-yellow-400">+{amount} XP</p>
        {label && <p className="text-xs text-zinc-500">{label}</p>}
      </div>
    </div>
  );
}
