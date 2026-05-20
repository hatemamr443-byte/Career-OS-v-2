"""Stripe billing: Pro / Team monthly plans (one-time charge, 30 days access)."""
import os
import stripe as stripe_sdk
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
)

from db import users, db as mongo_db
from auth import get_current_user
from models import new_id

router = APIRouter(prefix="/api/billing", tags=["billing"])

# Fixed plans — defined server-side only (security)
PLANS = {
    "pro":  {"name": "Pro",  "amount": 19.00, "currency": "usd", "days": 30},
    "team": {"name": "Team", "amount": 49.00, "currency": "usd", "days": 30},
}

TRIAL_DAYS          = 7      # Free trial duration
REFERRAL_BONUS_DAYS = 30     # Days of Pro awarded to referrer on conversion

payment_transactions = mongo_db.payment_transactions
referrals            = mongo_db.referrals


def _stripe(http_request: Request) -> StripeCheckout:
    api_key = os.environ.get("STRIPE_API_KEY", "")
    host_url = str(http_request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    return StripeCheckout(api_key=api_key, webhook_url=webhook_url)


# ─────────────────────────────────────────────
# FREE TRIAL
# ─────────────────────────────────────────────

@router.post("/start-trial")
async def start_trial(user=Depends(get_current_user)):
    """Activate a 7-day free Pro trial. One per user, no credit card needed."""
    user_doc = await users.find_one({"user_id": user["user_id"]}) or {}

    if user_doc.get("trial_used"):
        raise HTTPException(400, "You have already used your free trial.")

    if (user_doc.get("plan") or "free") != "free":
        raise HTTPException(400, "Your account already has an active plan.")

    trial_end = datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS)
    await users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "trial_active":    True,
            "trial_used":      True,
            "trial_ends_at":   trial_end.isoformat(),
        }},
    )

    # Log activity
    try:
        from activity import log_activity
        await log_activity(
            user["user_id"], "trial_started",
            "Free trial activated!",
            f"7-day Pro trial started. Ends {trial_end.strftime('%b %d')}.",
            {"trial_ends_at": trial_end.isoformat()},
        )
    except Exception:
        pass

    return {
        "ok":           True,
        "trial_active": True,
        "trial_ends_at": trial_end.isoformat(),
        "message":       f"Your 7-day Pro trial is now active! It ends on {trial_end.strftime('%B %d, %Y')}.",
    }


@router.get("/trial-status")
async def trial_status(user=Depends(get_current_user)):
    """Check if user has an active trial."""
    user_doc = await users.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    trial_active = bool(user_doc.get("trial_active"))
    trial_ends   = user_doc.get("trial_ends_at")

    # Auto-expire trial
    if trial_active and trial_ends:
        try:
            end = datetime.fromisoformat(trial_ends)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            if end < datetime.now(timezone.utc):
                trial_active = False
                await users.update_one(
                    {"user_id": user["user_id"]},
                    {"$set": {"trial_active": False}},
                )
        except Exception:
            pass

    return {
        "trial_active": trial_active,
        "trial_used":   bool(user_doc.get("trial_used")),
        "trial_ends_at": trial_ends,
        "can_start_trial": not user_doc.get("trial_used"),
    }


# ─────────────────────────────────────────────
# REFERRAL SYSTEM
# ─────────────────────────────────────────────

@router.post("/referral/generate")
async def generate_referral(user=Depends(get_current_user)):
    """Generate or retrieve the user's unique referral code."""
    existing = await referrals.find_one(
        {"referrer_id": user["user_id"]}, {"_id": 0}
    )
    if existing:
        return {"referral_code": existing["code"], "referral_url": _referral_url(existing["code"])}

    code = new_id("ref")[:12]   # Short code
    await referrals.insert_one({
        "code":         code,
        "referrer_id":  user["user_id"],
        "conversions":  0,
        "pending":      [],
        "rewarded":     [],
        "created_at":   datetime.now(timezone.utc).isoformat(),
    })
    return {"referral_code": code, "referral_url": _referral_url(code)}


@router.get("/referral/stats")
async def referral_stats(user=Depends(get_current_user)):
    """Get referral stats for the current user."""
    doc = await referrals.find_one({"referrer_id": user["user_id"]}, {"_id": 0})
    if not doc:
        return {"conversions": 0, "days_earned": 0, "referral_code": None}
    return {
        "referral_code":  doc["code"],
        "referral_url":   _referral_url(doc["code"]),
        "conversions":    doc.get("conversions", 0),
        "days_earned":    doc.get("conversions", 0) * REFERRAL_BONUS_DAYS,
        "pending":        len(doc.get("pending", [])),
    }


@router.post("/referral/apply")
async def apply_referral(payload: dict, user=Depends(get_current_user)):
    """Apply a referral code when a new user signs up."""
    code = (payload.get("code") or "").strip()
    if not code:
        raise HTTPException(400, "Referral code is required.")

    ref_doc = await referrals.find_one({"code": code})
    if not ref_doc:
        raise HTTPException(404, "Invalid referral code.")

    referrer_id = ref_doc["referrer_id"]
    if referrer_id == user["user_id"]:
        raise HTTPException(400, "You cannot refer yourself.")

    # Check not already used
    already = await referrals.find_one({
        "code": code,
        "pending": user["user_id"],
    })
    if already:
        raise HTTPException(400, "You have already used this referral code.")

    # Add to pending (converted when user upgrades)
    await referrals.update_one(
        {"code": code},
        {"$addToSet": {"pending": user["user_id"]}},
    )

    # Give new user a bonus trial day
    await users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"referred_by": code}},
    )

    return {"ok": True, "message": "Referral applied! You get +1 bonus day on your trial."}


async def _reward_referrer(referred_user_id: str) -> None:
    """Called when a referred user upgrades. Gives referrer bonus days."""
    user_doc = await users.find_one({"user_id": referred_user_id}) or {}
    code     = user_doc.get("referred_by")
    if not code:
        return

    ref_doc = await referrals.find_one({"code": code})
    if not ref_doc or referred_user_id in ref_doc.get("rewarded", []):
        return

    referrer_id = ref_doc["referrer_id"]
    bonus_end = datetime.now(timezone.utc) + timedelta(days=REFERRAL_BONUS_DAYS)

    await users.update_one(
        {"user_id": referrer_id},
        {"$set": {
            "plan": "pro",
            "plan_expires_at": bonus_end.isoformat(),
        }},
    )
    await referrals.update_one(
        {"code": code},
        {
            "$inc": {"conversions": 1},
            "$addToSet": {"rewarded": referred_user_id},
            "$pull":     {"pending": referred_user_id},
        },
    )

    try:
        from notifications import push_notification
        await push_notification(
            referrer_id, "streak_reward",
            "Referral reward! 🎉",
            f"Someone you referred upgraded to Pro. You get {REFERRAL_BONUS_DAYS} free days!",
            {"bonus_days": REFERRAL_BONUS_DAYS},
        )
    except Exception:
        pass


def _referral_url(code: str) -> str:
    dashboard = os.environ.get("DASHBOARD_URL", "https://career-os-web.onrender.com")
    return f"{dashboard}?ref={code}"


@router.get("/plans")
async def list_plans():
    return {"plans": [{"id": k, **v} for k, v in PLANS.items()]}


@router.get("/me")
async def my_plan(user=Depends(get_current_user)):
    plan = user.get("plan") or "free"
    expires = user.get("plan_expires_at")
    if expires and isinstance(expires, str):
        try:
            exp = datetime.fromisoformat(expires)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < datetime.now(timezone.utc):
                plan = "free"
        except Exception:
            pass
    return {"plan": plan, "plan_expires_at": expires}


@router.post("/checkout")
async def create_checkout(
    payload: dict,
    http_request: Request,
    user=Depends(get_current_user),
):
    plan_id = payload.get("plan_id")
    origin_url = payload.get("origin_url", "").rstrip("/")
    if plan_id not in PLANS:
        raise HTTPException(400, "Invalid plan")
    if not origin_url:
        raise HTTPException(400, "origin_url required")

    plan = PLANS[plan_id]
    success_url = f"{origin_url}/billing/return?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/billing"

    stripe = _stripe(http_request)
    metadata = {
        "user_id": user["user_id"],
        "email": user["email"],
        "plan_id": plan_id,
        "source": "career_os_web",
    }
    req = CheckoutSessionRequest(
        amount=float(plan["amount"]),
        currency=plan["currency"],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
    )
    session = await stripe.create_checkout_session(req)

    # Record pending transaction BEFORE redirect
    await payment_transactions.insert_one({
        "transaction_id": new_id("txn"),
        "session_id": session.session_id,
        "user_id": user["user_id"],
        "email": user["email"],
        "plan_id": plan_id,
        "amount": float(plan["amount"]),
        "currency": plan["currency"],
        "payment_status": "pending",
        "status": "initiated",
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": session.url, "session_id": session.session_id}


@router.get("/status/{session_id}")
async def check_status(
    session_id: str,
    http_request: Request,
    user=Depends(get_current_user),
):
    txn = await payment_transactions.find_one(
        {"session_id": session_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not txn:
        raise HTTPException(404, "Transaction not found")

    # Try Stripe retrieve. Emergent Stripe proxy may not support it; fall back to DB state
    # (which the webhook keeps current). Webhook is the source of truth either way.
    payment_status = txn.get("payment_status", "pending")
    overall_status = txn.get("status", "initiated")

    _ = _stripe(http_request)
    try:
        session = stripe_sdk.checkout.Session.retrieve(session_id)
        payment_status = getattr(session, "payment_status", None) or payment_status
        overall_status = getattr(session, "status", None) or overall_status
        await payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "payment_status": payment_status,
                "status": overall_status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
    except Exception:
        # Fall back to DB state; webhook will update it independently
        pass

    # Activate plan only if first-time success (idempotent)
    already_paid = txn.get("payment_status") == "paid"
    if payment_status == "paid" and not already_paid:
        plan_id = txn["plan_id"]
        days = PLANS[plan_id]["days"]
        expires_at = datetime.now(timezone.utc) + timedelta(days=days)
        await users.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"plan": plan_id, "plan_expires_at": expires_at.isoformat()}},
        )

    return {
        "payment_status": payment_status,
        "status": overall_status,
        "plan_id": txn["plan_id"],
        "amount": txn["amount"],
        "currency": txn["currency"],
    }


@router.post("/cancel")
async def cancel_subscription(user=Depends(get_current_user)):
    """Downgrade user to Free immediately. (No Stripe sub to cancel — we charge one-time per 30 days.)"""
    current_plan = user.get("plan") or "free"
    if current_plan == "free":
        return {"ok": True, "plan": "free", "message": "Already on Free plan."}

    await users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "plan": "free",
            "plan_expires_at": None,
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
            "previous_plan": current_plan,
        }},
    )
    return {"ok": True, "plan": "free", "message": f"Downgraded from {current_plan} to free. Thanks for trying Career OS."}


# Webhook endpoint (Stripe sends here)
webhook_router = APIRouter(tags=["billing"])


@webhook_router.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    api_key = os.environ.get("STRIPE_API_KEY", "")
    host_url = str(request.base_url).rstrip("/")
    stripe = StripeCheckout(api_key=api_key, webhook_url=f"{host_url}/api/webhook/stripe")
    try:
        event = await stripe.handle_webhook(body, sig)
    except Exception as ex:
        raise HTTPException(400, f"Webhook error: {ex}")

    # Idempotent activation on payment_intent.succeeded / checkout.session.completed
    if event.payment_status == "paid" and event.session_id:
        txn = await payment_transactions.find_one(
            {"session_id": event.session_id}, {"_id": 0}
        )
        if txn and txn.get("payment_status") != "paid":
            plan_id = txn["plan_id"]
            days = PLANS.get(plan_id, {}).get("days", 30)
            expires_at = datetime.now(timezone.utc) + timedelta(days=days)
            await users.update_one(
                {"user_id": txn["user_id"]},
                {"$set": {"plan": plan_id, "plan_expires_at": expires_at.isoformat()}},
            )
            await payment_transactions.update_one(
                {"session_id": event.session_id},
                {"$set": {
                    "payment_status": "paid",
                    "status": "completed",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
    return {"received": True}
