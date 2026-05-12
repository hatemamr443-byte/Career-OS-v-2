"""Resend email service.

Gracefully no-ops when RESEND_API_KEY is not set, so the rest of the system
keeps working until the user pastes their key.
"""
import os
import asyncio
import logging
from typing import Optional

import resend  # noqa: E402

log = logging.getLogger("emailer")


def _configured() -> bool:
    key = os.environ.get("RESEND_API_KEY", "").strip()
    return bool(key)


async def send_email(*, to: str, subject: str, html: str, text: Optional[str] = None) -> dict:
    """Returns {sent: bool, id?: str, reason?: str}. Never raises."""
    key = os.environ.get("RESEND_API_KEY", "").strip()
    sender = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
    if not key:
        log.warning("RESEND_API_KEY not configured — email to %s skipped.", to)
        return {"sent": False, "reason": "RESEND_API_KEY not configured"}

    resend.api_key = key
    params = {
        "from": sender,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if text:
        params["text"] = text

    try:
        # Resend SDK is synchronous — run in thread to keep FastAPI non-blocking
        result = await asyncio.to_thread(resend.Emails.send, params)
        return {"sent": True, "id": (result or {}).get("id")}
    except Exception as ex:
        log.error("Resend send failed for %s: %s", to, ex)
        return {"sent": False, "reason": str(ex)}


def render_daily_digest(user_name: str, jobs: list, dashboard_url: str) -> tuple[str, str]:
    """Returns (html, text) for the daily-digest email. Pure function, easy to test."""
    rows_html = []
    rows_text = []
    for j in jobs[:3]:
        title = (j.get("title") or "Untitled role")
        company = (j.get("company") or "Unknown")
        location = (j.get("location") or "")
        score = j.get("quick_score", "—")
        apply_url = j.get("source_url") or dashboard_url
        rows_html.append(f"""
        <tr>
          <td style="padding:18px 24px;border-top:1px solid #27272a;">
            <div style="font-size:13px;color:#71717a;letter-spacing:0.16em;text-transform:uppercase;font-family:'JetBrains Mono',monospace;">
              {company}
            </div>
            <a href="{apply_url}" style="font-size:20px;font-weight:800;color:#fafafa;text-decoration:none;line-height:1.2;letter-spacing:-0.02em;display:block;margin-top:6px;">
              {title}
            </a>
            <div style="font-size:13px;color:#a1a1aa;margin-top:6px;">
              {location}
              &nbsp;·&nbsp;
              <span style="color:#10b981;font-family:'JetBrains Mono',monospace;font-weight:600;">match {score}</span>
            </div>
            <a href="{apply_url}" style="display:inline-block;margin-top:14px;background:#fafafa;color:#0a0a0b;padding:8px 16px;border-radius:8px;text-decoration:none;font-size:13px;font-weight:600;">
              Open job →
            </a>
          </td>
        </tr>
        """)
        rows_text.append(f"• {title} — {company} ({location}) · match {score}\n  {apply_url}")

    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#0a0a0b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table cellpadding="0" cellspacing="0" width="100%" style="background:#0a0a0b;padding:40px 16px;">
    <tr><td align="center">
      <table cellpadding="0" cellspacing="0" width="560" style="max-width:560px;background:#141414;border:1px solid #27272a;border-radius:16px;overflow:hidden;">
        <tr><td style="padding:32px 24px 16px;">
          <div style="font-size:12px;color:#71717a;letter-spacing:0.22em;text-transform:uppercase;font-family:'JetBrains Mono',monospace;">
            Daily Brief · Career OS
          </div>
          <h1 style="margin:12px 0 4px;font-size:30px;color:#fafafa;font-weight:900;letter-spacing:-0.03em;line-height:1.05;">
            3 new jobs match your CV today.
          </h1>
          <p style="margin:8px 0 0;color:#a1a1aa;font-size:15px;line-height:1.5;">
            Hand-picked from Adzuna, Jooble and Remotive in the last 24 hours. Hi {user_name or "there"} —
            the decision engine ranked these highest against your profile.
          </p>
        </td></tr>
        {''.join(rows_html)}
        <tr><td style="padding:24px;background:#0a0a0b;border-top:1px solid #27272a;text-align:center;">
          <a href="{dashboard_url}" style="color:#fafafa;text-decoration:none;font-size:14px;font-weight:600;">
            Open your dashboard →
          </a>
          <div style="margin-top:16px;font-size:11px;color:#52525b;">
            You're receiving this because daily matches is ON. Turn it off any time on your <a href="{dashboard_url.rstrip('/')}/profile" style="color:#71717a;">Profile</a>.
          </div>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

    text = (
        "3 new jobs match your CV today\n"
        "───────────────────────────────\n\n"
        + "\n\n".join(rows_text)
        + f"\n\nOpen your dashboard: {dashboard_url}\n"
    )
    return html, text
