import { useEffect, useState, useRef, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { CheckCircle, X, Spinner } from "@phosphor-icons/react";

export default function BillingReturn() {
    const [params] = useSearchParams();
    const sessionId = params.get("session_id");
    const navigate = useNavigate();
    const [state, setState] = useState({ status: "checking", payment_status: "pending" });
    const attempts = useRef(0);

    const poll = useCallback(async () => {
        if (!sessionId) {
            setState({ status: "missing", payment_status: "" });
            return;
        }
        if (attempts.current >= 15) {
            setState((s) => ({ ...s, status: "timeout" }));
            return;
        }
        attempts.current += 1;
        try {
            const r = await api.get(`/billing/status/${sessionId}`);
            setState(r.data);
            if (r.data.payment_status === "paid") return;
            if (r.data.status === "expired") {
                setState((s) => ({ ...s, status: "expired" }));
                return;
            }
            setTimeout(poll, 2000);
        } catch (err) {
            console.error("status poll failed:", err);
            setTimeout(poll, 2000);
        }
    }, [sessionId]);

    useEffect(() => {
        poll();
    }, [poll]);

    return (
        <div className="min-h-screen flex items-center justify-center p-6 grain" data-testid="billing-return">
            <div className="card-soft p-10 max-w-md w-full text-center">
                {state.payment_status === "paid" ? (
                    <>
                        <div className="w-14 h-14 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center mx-auto mb-5">
                            <CheckCircle size={28} weight="fill" color="#10B981" />
                        </div>
                        <div className="overline mb-2">Payment received</div>
                        <h1 className="font-display font-black text-3xl tracking-tight mb-3">
                            Welcome to {state.plan_id === "team" ? "Team" : "Pro"}.
                        </h1>
                        <p className="text-zinc-400 text-sm mb-6">
                            Your plan is active for 30 days. The full decision engine is unlocked.
                        </p>
                        <button
                            onClick={() => navigate("/dashboard")}
                            data-testid="return-to-dashboard"
                            className="w-full bg-zinc-50 text-black hover:bg-zinc-200 transition-colors rounded-lg px-4 py-3 font-medium text-sm"
                        >
                            Open dashboard
                        </button>
                    </>
                ) : state.status === "timeout" ? (
                    <>
                        <div className="w-14 h-14 rounded-full bg-amber-500/15 border border-amber-500/30 flex items-center justify-center mx-auto mb-5">
                            <X size={28} weight="bold" color="#FBBF24" />
                        </div>
                        <div className="overline mb-2">Timed out</div>
                        <h1 className="font-display font-black text-2xl tracking-tight mb-3">
                            Still processing
                        </h1>
                        <p className="text-zinc-400 text-sm mb-6">
                            We didn't get a confirmation yet. Check your email or visit billing.
                        </p>
                        <button onClick={() => navigate("/billing")} data-testid="return-to-billing" className="w-full border border-zinc-800 hover:border-zinc-700 rounded-lg px-4 py-3 text-sm">
                            Go to billing
                        </button>
                    </>
                ) : state.status === "expired" ? (
                    <>
                        <div className="overline mb-2">Expired</div>
                        <h1 className="font-display font-black text-2xl tracking-tight mb-3">Session expired</h1>
                        <button onClick={() => navigate("/pricing")} data-testid="back-to-pricing" className="w-full bg-zinc-50 text-black rounded-lg px-4 py-3 text-sm font-medium">
                            Back to pricing
                        </button>
                    </>
                ) : (
                    <>
                        <div className="w-14 h-14 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center mx-auto mb-5 animate-spin">
                            <Spinner size={24} />
                        </div>
                        <div className="overline mb-2">Verifying</div>
                        <h1 className="font-display font-black text-2xl tracking-tight">Confirming your payment…</h1>
                        <p className="text-zinc-500 text-sm mt-2">Hang tight — usually 2–4 seconds.</p>
                    </>
                )}
            </div>
        </div>
    );
}
