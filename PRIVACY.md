# Privacy Policy — Career OS

**Last updated:** May 2026

## Who We Are

Career OS ("we", "us", "our") is an AI-powered career intelligence platform operated from Lisbon, Portugal.
Contact: privacy@career-os.io

---

## What Data We Collect

### Account Data
- Name, email address (from Google OAuth)
- Profile photo (from Google, optional)

### Career Profile Data
- CV / resume text (uploaded by you)
- Professional skills, target roles, work preferences
- Salary expectations, years of experience
- Career goals and notes

### Activity Data
- Job applications you track in the platform
- Actions taken (jobs saved, applied, status changes)
- AI tool usage (CV tailoring, interview prep, salary lookups)
- Gamification progress (XP, levels, streaks)

### Gmail Data (if connected)
- Email metadata only: sender, subject, date, snippet
- AI classification labels applied to each email
- **We never read full email bodies beyond the snippet**
- **We never store OAuth refresh tokens in plaintext**
- **We never send emails on your behalf**

### Usage Analytics (if consented)
- Page views, feature interactions (via PostHog)
- No sensitive career data flows to PostHog

---

## How We Use Your Data

| Purpose | Legal Basis |
|---------|-------------|
| Providing the AI career features you request | Contract performance |
| Personalizing AI recommendations over time | Legitimate interest |
| Sending account and feature emails | Contract performance |
| Sending marketing emails (optional) | Consent |
| Error monitoring and debugging | Legitimate interest |
| Usage analytics to improve the product | Legitimate interest |

---

## AI Processing Disclosure

Career OS uses AI to:
- Score job opportunities against your profile
- Rewrite your CV for specific roles
- Generate interview questions and evaluate answers
- Classify recruiter emails
- Provide salary intelligence

AI outputs are **recommendations only** — not decisions. You remain in full control of all career actions.

**AI providers used:** Anthropic, OpenAI, Google (Gemini). Data sent to these providers is governed by their respective privacy policies. We minimize data transmitted to only what is necessary for each task.

---

## Data Retention

| Data Type | Retention Period |
|-----------|-----------------|
| Account data | Until you delete your account |
| Application history | Until you delete your account |
| CV versions | Until you delete them or your account |
| Activity logs | 12 months rolling |
| Email metadata | 90 days |
| XP / gamification | Until account deletion |
| AI usage logs | 30 days |

---

## Your Rights (GDPR)

As an EU resident, you have the right to:

| Right | How to exercise |
|-------|----------------|
| **Access** your data | `GET /api/me/data-summary` |
| **Export** your data | `GET /api/me/export-data` (downloads ZIP) |
| **Delete** your data | `DELETE /api/me/account` (irreversible) |
| **Correct** your data | Update via Profile settings |
| **Object** to processing | Email privacy@career-os.io |
| **Withdraw consent** | `PATCH /api/me/consent` |

We respond to data requests within **30 days**.

---

## Data Sharing

We **do not** sell your data to third parties.

We share data only with:
- **AI providers** (Anthropic, OpenAI, Google) — for AI feature processing
- **Stripe** — for payment processing
- **Resend** — for email delivery
- **Sentry** — for error monitoring (no PII in error logs)
- **PostHog** — for analytics (anonymized, opt-in)

---

## Cookies

We use only:
- **Session cookies** — for authentication (httpOnly, secure)
- **PostHog cookies** — for analytics (if consented)

No advertising cookies. No tracking pixels.

---

## Security

- All data encrypted in transit (HTTPS/TLS)
- MongoDB Atlas encryption at rest
- OAuth tokens stored with encryption
- Regular security reviews
- Principle of least privilege on all data access

---

## Children

Career OS is not intended for users under 18. We do not knowingly collect data from minors.

---

## Changes to This Policy

We will notify users of material changes via email at least 14 days before they take effect.

---

## Contact

**Data Controller:** Career OS
**Email:** privacy@career-os.io
**Address:** Lisbon, Portugal
## Right to Erasure (GDPR Art.17)
