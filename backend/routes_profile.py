"""Profile / CV / identity graph."""
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from datetime import datetime, timezone
from pypdf import PdfReader
from db import profiles
from auth import get_current_user
from llm_service import llm_call, parse_json_loose

router = APIRouter(prefix="/api/profile", tags=["profile"])

MAX_PDF_BYTES = 5 * 1024 * 1024  # 5 MB


@router.get("")
async def get_profile(user=Depends(get_current_user)):
    p = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return p or {}


@router.put("")
async def update_profile(payload: dict, user=Depends(get_current_user)):
    payload.pop("user_id", None)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    await profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": payload, "$setOnInsert": {"user_id": user["user_id"]}},
        upsert=True,
    )
    p = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return p


@router.post("/parse-cv")
async def parse_cv(payload: dict, user=Depends(get_current_user)):
    cv_text = (payload.get("cv_text") or "").strip()
    if not cv_text:
        raise HTTPException(400, "cv_text required")

    system = (
        "You are an expert CV parser. Extract structured profile data. "
        "Return ONLY JSON: "
        '{"headline": "1-line professional headline", '
        '"skills": ["lowercase skills"], '
        '"target_roles": ["3-5 likely target roles"], '
        '"years_experience": int}'
    )
    try:
        text = await llm_call(
            task="reasoning",
            system=system,
            user=cv_text,
            session_id=f"cv_{user['user_id']}",
        )
        data = parse_json_loose(text)
    except Exception:
        data = {}

    update = {
        "cv_text": cv_text,
        "headline": data.get("headline", "Professional"),
        "skills": [s.lower() for s in (data.get("skills") or [])][:30],
        "target_roles": (data.get("target_roles") or [])[:5],
        "years_experience": data.get("years_experience"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": update, "$setOnInsert": {"user_id": user["user_id"]}},
        upsert=True,
    )
    p = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return p


@router.post("/upload-cv")
async def upload_cv(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """Upload a PDF CV. Extracts text via pypdf, parses with Claude, updates profile."""
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
            "Could not extract enough text from this PDF (it may be an image-only scan). Try a text-based PDF or paste your CV manually.",
        )

    # Parse with Claude (same logic as parse_cv)
    system = (
        "You are an expert CV parser. Extract structured profile data. "
        "Return ONLY JSON: "
        '{"headline": "1-line professional headline", '
        '"skills": ["lowercase skills"], '
        '"target_roles": ["3-5 likely target roles"], '
        '"years_experience": int}'
    )
    try:
        text = await llm_call(
            task="reasoning",
            system=system,
            user=cv_text,
            session_id=f"cv_upload_{user['user_id']}",
        )
        data = parse_json_loose(text)
    except Exception:
        data = {}

    update = {
        "cv_text": cv_text,
        "cv_filename": file.filename,
        "cv_bytes": len(contents),
        "headline": data.get("headline", "Professional"),
        "skills": [s.lower() for s in (data.get("skills") or [])][:30],
        "target_roles": (data.get("target_roles") or [])[:5],
        "years_experience": data.get("years_experience"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": update, "$setOnInsert": {"user_id": user["user_id"]}},
        upsert=True,
    )
    p = await profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return p
