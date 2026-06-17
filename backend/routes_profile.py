"""Profile / CV / identity graph.

CV parsing routes now flow through orchestrator.run() so the AI
has full career context when extracting structured data — it can
infer target roles more accurately when it knows the user's history.
"""
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from datetime import datetime, timezone
from pypdf import PdfReader
from db import profiles
from auth import get_current_user
from llm_schemas import parse_llm_json
from orchestrator import orchestrator
from activity import log_activity
from xp import award_xp
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/profile", tags=["profile"])

MAX_PDF_BYTES = 5 * 1024 * 1024  # 5 MB

_CV_PARSE_PROMPT = (
    "You are an expert CV parser with full knowledge of this user's career history. "
    "Extract structured profile data from the CV text below. "
    "Use the user's career memory to infer realistic target roles if not explicitly stated. "
    "Return ONLY valid JSON:\n"
    '{"headline": "1-line professional headline", '
    '"skills": ["lowercase skill"], '
    '"target_roles": ["3-5 realistic target roles based on CV + career context"], '
    '"years_experience": int, '
    '"languages": ["language if mentioned"], '
    '"education": "highest relevant degree/cert if present"}'
)


async def _parse_and_update_profile(
    user_id: str,
    cv_text: str,
    extra_update: dict | None = None,
) -> dict:
    """
    Core CV parse logic — shared by parse_cv and upload_cv.
    Runs through orchestrator so career context enriches the extraction.
    """
    try:
        text = await orchestrator.run(
            user_id=user_id,
            feature="cv_parse",
            task="reasoning",
            feature_prompt=_CV_PARSE_PROMPT,
            user_message=f"CV TEXT:\n{cv_text[:4000]}",
            session_id=f"cv_parse_{user_id}",
            context_depth="standard",
        )
        data = parse_llm_json(text)
    except Exception as ex:
        logger.warning("CV parse LLM failed (user=%s): %s", user_id, ex)
        data = {}

    update: dict = {
        "cv_text":          cv_text,
        "headline":         data.get("headline", "Professional"),
        "skills":           [s.lower() for s in (data.get("skills") or [])][:30],
        "target_roles":     (data.get("target_roles") or [])[:5],
        "years_experience": data.get("years_experience"),
        "updated_at":       datetime.now(timezone.utc).isoformat(),
    }
    if data.get("languages"):
        update["languages"] = data["languages"]
    if data.get("education"):
        update["education"] = data["education"]
    if extra_update:
        update.update(extra_update)

    await profiles.update_one(
        {"user_id": user_id},
        {"$set": update, "$setOnInsert": {"user_id": user_id}},
        upsert=True,
    )

    await log_activity(
        user_id, "cv_uploaded",
        "CV parsed and profile updated",
        f"Extracted {len(update['skills'])} skills, "
        f"{len(update['target_roles'])} target roles",
        {"skills_count": len(update["skills"])},
    )
    await award_xp(user_id, "cv_uploaded")

    return await profiles.find_one({"user_id": user_id}, {"_id": 0}) or {}


# ─────────────────────────────────────────────
# READ / UPDATE
# ─────────────────────────────────────────────

@router.get("")
async def get_profile(user=Depends(get_current_user)):
    p = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return p or {}


@router.put("")
async def update_profile(payload: dict, user=Depends(get_current_user)):
    # SECURITY: Whitelist — prevents injecting plan/trial/token fields via
    # an arbitrary JSON body (e.g. {"plan": "pro", "trial_active": true}).
    ALLOWED_FIELDS = {
        "full_name", "location", "country", "phone", "bio",
        "title", "headline", "summary", "skills", "languages",
        "experience", "education", "certifications", "years_experience",
        "preferences", "career_goals", "target_roles",
        "target_industries", "target_salary_min", "target_salary_max",
        "remote_preference", "willing_to_relocate", "cv_text",
        "linkedin_url", "github_url", "portfolio_url", "daily_matches",
    }
    safe_payload = {k: v for k, v in payload.items() if k in ALLOWED_FIELDS}
    safe_payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    await profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": safe_payload, "$setOnInsert": {"user_id": user["user_id"]}},
        upsert=True,
    )
    await log_activity(
        user["user_id"], "profile_updated",
        "Profile updated",
        "Profile information was updated",
        {"fields": list(safe_payload.keys())},
    )
    return await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}


# ─────────────────────────────────────────────
# CV PARSE (text input)
# ─────────────────────────────────────────────

@router.post("/parse-cv")
async def parse_cv(payload: dict, user=Depends(get_current_user)):
    """Parse CV text with orchestrator — career context enriches extraction."""
    cv_text = (payload.get("cv_text") or "").strip()
    if not cv_text:
        raise HTTPException(400, "cv_text required")
    return await _parse_and_update_profile(user["user_id"], cv_text)


# ─────────────────────────────────────────────
# CV UPLOAD (PDF)
# ─────────────────────────────────────────────

@router.post("/upload-cv")
async def upload_cv(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """Upload a PDF CV. Extracts text via pypdf, parses with orchestrator."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")

    contents = await file.read()
    if len(contents) > MAX_PDF_BYTES:
        raise HTTPException(400, "PDF too large (5 MB max).")
    if not contents:
        raise HTTPException(400, "Empty file.")

    try:
        reader = PdfReader(io.BytesIO(contents))
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                continue
        cv_text = "\n".join(pages).strip()
    except Exception as ex:
        raise HTTPException(400, f"Failed to parse PDF: {ex}")

    if len(cv_text) < 100:
        raise HTTPException(
            400,
            "Could not extract enough text from this PDF "
            "(may be an image-only scan). "
            "Try a text-based PDF or paste your CV manually.",
        )

    return await _parse_and_update_profile(
        user["user_id"],
        cv_text,
        extra_update={"cv_filename": file.filename, "cv_bytes": len(contents)},
    )
