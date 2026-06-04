"""
Welcome Email Drip Sequence.
Sends onboarding emails to new users at: day 0, 1, 3, 7.
Called from auth.py on new user creation.
Cron-triggered for day 1/3/7 follow-ups.
"""
import logging
from datetime import datetime, timezone, timedelta
from db import users, emails_sent
from models import new_id
from config import settings

logger = logging.getLogger(__name__)

SENDER  = settings.SENDER_EMAIL or "onboarding@resend.dev"
APP_URL = settings.DASHBOARD_URL or "https://career-os-web.onrender.com"


# ── Email templates ───────────────────────────────────────────────

def _day0_email(name: str) -> dict:
    first = name.split()[0] if name else "there"
    return {
        "subject": f"Welcome to Career OS, {first} 👋",
        "html": f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#09090b;color:#f4f4f5;padding:32px;border-radius:12px">
  <h1 style="font-size:24px;font-weight:800;margin-bottom:8px">Welcome to Career OS 🚀</h1>
  <p style="color:#a1a1aa;margin-bottom:24px">Your AI-powered career operating system is ready.</p>

  <p style="margin-bottom:16px">Hi {first},</p>
  <p style="color:#d4d4d8;line-height:1.7;margin-bottom:24px">
    Career OS helps you track job applications, tailor your CV with AI, and prepare for interviews — all in one place.
  </p>

  <div style="background:#18181b;border-radius:8px;padding:20px;margin-bottom:24px">
    <p style="font-weight:600;margin-bottom:12px">Start here:</p>
    <ol style="color:#a1a1aa;line-height:2;padding-left:20px">
      <li><a href="{APP_URL}/profile" style="color:#86efac;text-decoration:none">Upload your CV</a> — AI parses your skills automatically</li>
      <li><a href="{APP_URL}/jobs" style="color:#86efac;text-decoration:none">Browse jobs</a> — AI scores them against your profile</li>
      <li><a href="{APP_URL}/cv-tailor" style="color:#86efac;text-decoration:none">Tailor your CV</a> — for each application in one click</li>
    </ol>
  </div>

  <a href="{APP_URL}/dashboard"
     style="display:inline-block;background:#f4f4f5;color:#09090b;font-weight:700;
            padding:12px 24px;border-radius:8px;text-decoration:none;font-size:14px">
    Open Career OS →
  </a>

  <p style="color:#52525b;font-size:12px;margin-top:32px">Career OS · Lisbon, Portugal</p>
</div>""",
    }


def _day1_email(name: str, profile_pct: int = 0) -> dict:
    first = name.split()[0] if name else "there"
    return {
        "subject": f"{first}, your profile is {profile_pct}% complete",
        "html": f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#09090b;color:#f4f4f5;padding:32px;border-radius:12px">
  <h2 style="font-size:20px;font-weight:800">Your profile needs attention ⚡</h2>
  <p style="color:#a1a1aa;margin-bottom:20px">A complete profile gets 3x better AI match scores.</p>

  <div style="background:#18181b;border-radius:8px;padding:16px;margin-bottom:20px">
    <div style="display:flex;justify-content:space-between;margin-bottom:8px">
      <span style="font-size:14px">Profile Completeness</span>
      <span style="font-weight:700;color:{'#10B981' if profile_pct >= 80 else '#FBBF24' if profile_pct >= 40 else '#EF4444'}">{profile_pct}%</span>
    </div>
    <div style="background:#3f3f46;border-radius:4px;height:6px">
      <div style="background:{'#10B981' if profile_pct >= 80 else '#FBBF24'};height:6px;border-radius:4px;width:{profile_pct}%"></div>
    </div>
  </div>

  <a href="{APP_URL}/profile"
     style="display:inline-block;background:#f4f4f5;color:#09090b;font-weight:700;
            padding:12px 24px;border-radius:8px;text-decoration:none;font-size:14px">
    Complete Your Profile →
  </a>
</div>""",
    }


def _day3_email(name: str) -> dict:
    return {
        "subject": "Have you tried the Chrome Extension? 🔌",
        "html": f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#09090b;color:#f4f4f5;padding:32px;border-radius:12px">
  <h2 style="font-size:20px;font-weight:800">Save any job in one click 🔌</h2>
  <p style="color:#a1a1aa;margin-bottom:20px">
    The Career OS Chrome Extension lets you save jobs from LinkedIn, Indeed, and Glassdoor directly to your tracker.
  </p>

  <div style="background:#18181b;border-radius:8px;padding:20px;margin-bottom:20px">
    <p style="font-weight:600;margin-bottom:8px">What it does:</p>
    <ul style="color:#a1a1aa;line-height:1.8;padding-left:20px">
      <li>Save jobs from any site in 1 click</li>
      <li>Get instant AI match score (ATS)</li>
      <li>Open CV Tailor, Interview Prep, Salary Intel directly</li>
    </ul>
  </div>

  <p style="color:#d4d4d8;margin-bottom:20px">Also — have you tried the <strong style="color:#f4f4f5">CV Tailor</strong>? It rewrites your CV for each job automatically.</p>

  <a href="{APP_URL}/cv-tailor"
     style="display:inline-block;background:#f4f4f5;color:#09090b;font-weight:700;
            padding:12px 24px;border-radius:8px;text-decoration:none;font-size:14px">
    Try CV Tailor →
  </a>
</div>""",
    }


def _day7_email(name: str) -> dict:
    first = name.split()[0] if name else "there"
    return {
        "subject": f"{first}, unlock unlimited AI features 🚀",
        "html": f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#09090b;color:#f4f4f5;padding:32px;border-radius:12px">
  <h2 style="font-size:20px;font-weight:800">You've been with Career OS for a week 🎉</h2>
  <p style="color:#a1a1aa;margin-bottom:20px">Ready to unlock everything?</p>

  <div style="background:#18181b;border-radius:8px;padding:20px;margin-bottom:20px">
    <p style="font-weight:600;margin-bottom:12px">Pro plan — $19/month</p>
    <ul style="color:#a1a1aa;line-height:1.8;padding-left:20px">
      <li>Unlimited AI job matches</li>
      <li>20 CV tailoring sessions/month</li>
      <li>Unlimited interview prep</li>
      <li>Salary intelligence & negotiation</li>
      <li>Priority AI processing</li>
    </ul>
  </div>

  <a href="{APP_URL}/billing"
     style="display:inline-block;background:#f4f4f5;color:#09090b;font-weight:700;
            padding:12px 24px;border-radius:8px;text-decoration:none;font-size:14px">
    Upgrade to Pro →
  </a>

  <p style="color:#52525b;font-size:12px;margin-top:24px">
    Not ready? No problem. Your free account stays active forever.
  </p>
</div>""",
    }


# ── Send logic ────────────────────────────────────────────────────

async def send_welcome_sequence_day0(user_id: str, email: str, name: str) -> None:
    """Send day-0 welcome email immediately on signup."""
    await _send_if_not_sent(user_id, email, "day0", _day0_email(name))


async def run_drip_sequence() -> dict:
    """
    Cron job — runs daily.
    Sends day1 / day3 / day7 emails to users who signed up N days ago.
    """
    now   = datetime.now(timezone.utc)
    sent  = 0
    errors = 0

    for days_ago, template_fn, sequence_key in [
        (1, _day1_email, "day1"),
        (3, _day3_email, "day3"),
        (7, _day7_email, "day7"),
    ]:
        target_date = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d")

        # Find users created on that date who haven't received this email
        async for user in users.find({
            "created_at": {"$regex": f"^{target_date}"},
            "email":      {"$exists": True},
        }, {"_id": 0, "user_id": 1, "email": 1, "name": 1}):
            uid   = user["user_id"]
            email = user.get("email", "")
            name  = user.get("name", "")

            if not email:
                continue

            # For day1 — get profile completeness
            extra = {}
            if sequence_key == "day1":
                from routes_activity import _score_profile
                profile = await __import__("db").profiles.find_one(
                    {"user_id": uid}, {"_id": 0}
                ) or {}
                try:
                    from routes_activity import _score_profile
                    extra["profile_pct"] = _score_profile(profile).get("percent", 0)
                except Exception:
                    extra["profile_pct"] = 0

            content = template_fn(name, **extra) if extra else template_fn(name)

            ok = await _send_if_not_sent(uid, email, sequence_key, content)
            if ok:
                sent += 1
            else:
                errors += 1

    return {"sent": sent, "errors": errors}


async def _send_if_not_sent(user_id: str, email: str, key: str, content: dict) -> bool:
    """Send email only if not already sent for this key. Idempotent."""
    already = await emails_sent.find_one(
        {"user_id": user_id, "sequence_key": key}
    )
    if already:
        return False

    try:
        import resend
        resend.api_key = settings.RESEND_API_KEY or ""
        resend.Emails.send({
            "from":    SENDER,
            "to":      [email],
            "subject": content["subject"],
            "html":    content["html"],
        })
        await emails_sent.insert_one({
            "_id":          new_id("eml_sent"),
            "user_id":      user_id,
            "sequence_key": key,
            "sent_to":      email,
            "sent_at":      datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Welcome email sent: user=%s key=%s", user_id, key)
        return True
    except Exception as ex:
        logger.error("Welcome email failed: user=%s key=%s err=%s", user_id, key, ex)
        return False
