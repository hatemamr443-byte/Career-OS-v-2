"""Email intelligence: AI-classified threads."""
from fastapi import APIRouter, Depends, HTTPException
from db import emails
from auth import get_current_user
from llm_service import llm_call, parse_json_loose

router = APIRouter(prefix="/api/emails", tags=["emails"])


CLASSES = ["interview", "rejection", "offer", "recruiter", "follow_up", "other"]


@router.get("")
async def list_emails(user=Depends(get_current_user)):
    docs = await emails.find({"user_id": user["user_id"]}, {"_id": 0}).sort("received_at", -1).to_list(200)
    # group by thread_id
    threads = {}
    for d in docs:
        tid = d["thread_id"]
        threads.setdefault(tid, []).append(d)
    thread_list = []
    for tid, msgs in threads.items():
        msgs.sort(key=lambda x: x["received_at"])
        last = msgs[-1]
        thread_list.append({
            "thread_id": tid,
            "messages": msgs,
            "last_message": last,
            "subject": msgs[0]["subject"],
            "from_name": msgs[0]["from_name"],
            "classification": last.get("classification", "other"),
            "received_at": last["received_at"],
            "is_read": all(m.get("is_read") for m in msgs),
            "linked_job_id": last.get("linked_job_id"),
        })
    thread_list.sort(key=lambda x: x["received_at"], reverse=True)
    return {"threads": thread_list}


@router.post("/{email_id}/classify")
async def classify_email(email_id: str, user=Depends(get_current_user)):
    e = await emails.find_one({"email_id": email_id, "user_id": user["user_id"]}, {"_id": 0})
    if not e:
        raise HTTPException(404, "Email not found")

    system = (
        "You classify recruiting emails. Return ONLY JSON: "
        '{"classification": "interview"|"rejection"|"offer"|"recruiter"|"follow_up"|"other", '
        '"intent": "1-sentence intent", "next_steps": ["..."]}'
    )
    user_prompt = f"FROM: {e['from_name']} <{e['from_addr']}>\nSUBJECT: {e['subject']}\nBODY:\n{e['body']}"
    try:
        text = await llm_call(
            task="fast",
            system=system,
            user=user_prompt,
            session_id=f"email_{email_id}",
        )
        data = parse_json_loose(text)
        cls = data.get("classification", "other")
        if cls not in CLASSES:
            cls = "other"
        intent = data.get("intent", "")
        next_steps = data.get("next_steps", []) or []
    except Exception:
        # heuristic fallback
        body = (e["subject"] + " " + e["body"]).lower()
        if "offer" in body and ("congrat" in body or "extend" in body):
            cls = "offer"
        elif "reject" in body or "moved forward with other" in body or "not selected" in body:
            cls = "rejection"
        elif "interview" in body or "schedule" in body or "screen" in body:
            cls = "interview"
        elif "intro" in body or "chat" in body:
            cls = "recruiter"
        else:
            cls = "other"
        intent = ""
        next_steps = []

    await emails.update_one(
        {"email_id": email_id},
        {"$set": {"classification": cls, "intent": intent, "next_steps": next_steps}},
    )
    e.update({"classification": cls, "intent": intent, "next_steps": next_steps})
    # Publish classification-specific events for cross-feature orchestration
    try:
        from event_bus import event_bus
        class_event_map = {
            "recruiter": "recruiter_reachout",
            "interview": "interview_invited",
            "offer":     "offer_email_received",
            "rejection": "rejection_email_received",
        }
        bus_event = class_event_map.get(cls)
        if bus_event:
            await event_bus.publish(bus_event, user["user_id"], {
                "email_id":    email_id,
                "from_name":   e.get("from_name"),
                "from_addr":   e.get("from_addr"),
                "subject":     e.get("subject"),
                "intent":      intent,
                "next_steps":  next_steps,
            })
    except Exception:
        pass
    return e


@router.post("/classify-all")
async def classify_all(user=Depends(get_current_user)):
    """Bulk classify all unclassified emails for the user."""
    cursor = emails.find(
        {"user_id": user["user_id"], "classification": "other"}, {"_id": 0}
    )
    count = 0
    docs = await cursor.to_list(50)
    for e in docs:
        try:
            await classify_email(e["email_id"], user)
            count += 1
        except Exception:
            pass
    return {"classified": count}


@router.post("/{email_id}/read")
async def mark_read(email_id: str, user=Depends(get_current_user)):
    await emails.update_one(
        {"email_id": email_id, "user_id": user["user_id"]},
        {"$set": {"is_read": True}},
    )
    return {"ok": True}
