import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

/**
 * Terms of Service — public page, no auth required.
 * Pairs with /privacy. Linked from CookieConsent and the footer.
 */
export default function Terms() {
    const updated = "February 2026";
    return (
        <div data-testid="terms-page" className="min-h-screen bg-neutral-50">
            <div className="max-w-3xl mx-auto px-6 py-12">
                <Link
                    to="/"
                    data-testid="terms-back-link"
                    className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-8"
                >
                    <ArrowLeft size={16} /> Back to Career OS
                </Link>

                <header className="mb-10">
                    <p className="text-xs uppercase tracking-[0.18em] text-neutral-500 font-semibold">
                        Legal
                    </p>
                    <h1
                        data-testid="terms-page-title"
                        className="mt-2 text-4xl sm:text-5xl font-bold tracking-tight text-neutral-900"
                    >
                        Terms of Service
                    </h1>
                    <p className="mt-3 text-sm text-neutral-500">
                        Last updated · {updated}
                    </p>
                </header>

                <article className="prose prose-neutral max-w-none text-neutral-700 leading-relaxed space-y-8">
                    <section>
                        <h2 className="text-xl font-semibold text-neutral-900">
                            1. Acceptance of Terms
                        </h2>
                        <p>
                            By accessing or using Career OS (the “Service”), you agree to be
                            bound by these Terms of Service. If you do not agree, please do
                            not use the Service. We may update these Terms; material changes
                            will be communicated via email or in-app notice.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-neutral-900">
                            2. What Career OS Is
                        </h2>
                        <p>
                            Career OS is an AI-powered career intelligence system. It analyses
                            job opportunities, tailors CVs, simulates interviews, evaluates
                            salary positioning, and helps you plan your career strategically.
                            It is <strong>not</strong> a recruiter, employment agency, or
                            guarantor of job outcomes.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-neutral-900">
                            3. AI-Generated Content
                        </h2>
                        <p>
                            Career OS uses large language models (currently Claude Sonnet 4.5,
                            GPT, and Gemini families) to produce recommendations, scores, and
                            written content. AI output is probabilistic and can be incorrect,
                            biased, or out-of-date. You are responsible for reviewing all
                            content before submitting it to employers. We disclose AI use
                            transparently in every feature.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-neutral-900">
                            4. Your Account & Data
                        </h2>
                        <p>
                            You retain ownership of your CV, application data, and personal
                            information. We process it solely to provide the Service. Under
                            GDPR (and equivalent laws), you can export or permanently delete
                            your data at any time from Profile → Privacy, or by emailing
                            <span className="font-medium"> privacy@career-os.io</span>.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-neutral-900">
                            5. Acceptable Use
                        </h2>
                        <ul className="list-disc pl-6 space-y-1">
                            <li>No fabricating qualifications or work history.</li>
                            <li>No spamming employers using generated content at scale.</li>
                            <li>No reverse-engineering the AI orchestration layer.</li>
                            <li>No automated scraping of the platform.</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-neutral-900">
                            6. Subscriptions & Billing
                        </h2>
                        <p>
                            Paid plans renew automatically until cancelled. You can cancel any
                            time from the Billing page; you retain access until the end of the
                            current period. Refunds are handled on a case-by-case basis under
                            applicable consumer-protection law.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-neutral-900">
                            7. Disclaimer of Warranties
                        </h2>
                        <p>
                            The Service is provided “as is.” We make no warranty that AI
                            recommendations will result in job offers, salary increases, or
                            specific career outcomes.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-neutral-900">
                            8. Limitation of Liability
                        </h2>
                        <p>
                            To the maximum extent permitted by law, Career OS is not liable
                            for indirect, incidental, or consequential damages arising from
                            use of the Service. Total liability in any 12-month period is
                            limited to the amount you paid us during that period.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-neutral-900">
                            9. Governing Law
                        </h2>
                        <p>
                            These Terms are governed by the laws of the jurisdiction where
                            Career OS is registered. Disputes will be resolved in good faith
                            first; failing that, in the competent courts of that jurisdiction.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-semibold text-neutral-900">
                            10. Contact
                        </h2>
                        <p>
                            Questions? Email{" "}
                            <span className="font-medium">support@career-os.io</span> for
                            general matters, or{" "}
                            <span className="font-medium">privacy@career-os.io</span> for
                            data-protection requests.
                        </p>
                    </section>
                </article>

                <div className="mt-12 flex items-center gap-4 text-sm text-neutral-500">
                    <Link
                        to="/privacy"
                        data-testid="terms-link-privacy"
                        className="underline underline-offset-2 hover:text-neutral-900"
                    >
                        Privacy Policy
                    </Link>
                    <span>·</span>
                    <Link
                        to="/"
                        data-testid="terms-link-home"
                        className="underline underline-offset-2 hover:text-neutral-900"
                    >
                        Home
                    </Link>
                </div>
            </div>
        </div>
    );
}
