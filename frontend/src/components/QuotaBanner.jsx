import { Link } from "react-router-dom";
import { Warning } from "@phosphor-icons/react";

/**
 * Show when AI quota is exhausted for a feature.
 * Usage:
 *   if (error?.response?.status === 429) {
 *       return <QuotaBanner feature="cv_tailor" plan={plan} />;
 *   }
 */
export default function QuotaBanner({ feature, plan, className = "" }) {
    const LABELS = {
        cv_tailor:             "CV Tailoring",
        ats_score:             "ATS Scoring",
        cover_letter:          "Cover Letter",
        interview_questions:   "Interview Questions",
        interview_evaluate:    "Answer Evaluation",
        company_research:      "Company Research",
        salary_range:          "Salary Lookup",
        evaluate_offer:        "Offer Evaluation",
        negotiate:             "Negotiation Script",
        cost_of_living:        "Cost of Living",
    };

    const featureLabel = LABELS[feature] || feature;
    const isPro        = plan === "pro" || plan === "team";

    return (
        <div className={`quota-banner ${className}`} data-testid="quota-banner">
            <div className="flex items-center gap-2">
                <Warning size={15} weight="fill" />
                <span>
                    Daily {featureLabel} limit reached
                    {isPro ? " (Pro)" : " (Free)"}.
                </span>
            </div>
            {!isPro ? (
                <Link to="/billing">
                    Upgrade to Pro →
                </Link>
            ) : (
                <span style={{ color: "#a1a1aa", fontSize: 12 }}>
                    Resets midnight UTC
                </span>
            )}
        </div>
    );
}

/**
 * Inline quota hit state for use in page components.
 * @example
 *   const [quotaHit, setQuotaHit] = useState(false);
 *   try { ... } catch(e) { if (e.response?.status === 429) setQuotaHit(true); }
 *   {quotaHit && <QuotaInline feature="cv_tailor" />}
 */
export function QuotaInline({ feature, plan }) {
    return (
        <div className="text-center py-10 px-4">
            <Warning size={32} className="mx-auto mb-3 text-yellow-500 opacity-80" weight="fill" />
            <h3 className="font-display font-bold text-lg mb-2">Daily Limit Reached</h3>
            <p className="text-sm text-zinc-500 mb-6 max-w-sm mx-auto">
                You've used your daily {feature?.replace(/_/g, " ")} quota.
                {plan === "free"
                    ? " Upgrade to Pro for 10× more AI actions."
                    : " Your limit resets at midnight UTC."}
            </p>
            {plan === "free" && (
                <Link to="/billing"
                    className="inline-flex items-center gap-2 bg-zinc-50 text-black
                               px-5 py-2.5 rounded-lg text-sm font-semibold
                               hover:bg-zinc-200 transition-colors">
                    Upgrade to Pro →
                </Link>
            )}
        </div>
    );
}
