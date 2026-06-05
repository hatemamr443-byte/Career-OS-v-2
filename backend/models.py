"""Pydantic models for AI Career OS."""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone
import uuid


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    auth_provider: str = "google"  # abstraction: 'google' | 'jwt'
    xp: int = 0
    level: int = 1
    streak: int = 0
    last_active_date: Optional[str] = None  # YYYY-MM-DD
    created_at: datetime = Field(default_factory=now_utc)


class Profile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    cv_text: str = ""
    headline: str = ""
    skills: List[str] = []
    target_roles: List[str] = []
    target_locations: List[str] = []
    salary_min: Optional[int] = None
    years_experience: Optional[int] = None
    # Identity Graph
    behavior: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=now_utc)


class Job(BaseModel):
    model_config = ConfigDict(extra="ignore")
    job_id: str
    title: str
    company: str
    location: str
    remote: bool = False
    salary_range: Optional[str] = None
    description: str
    skills_required: List[str] = []
    seniority: str = "mid"  # junior | mid | senior | lead
    source: str = "mock"  # mock | manual | indeed | linkedin
    source_url: Optional[str] = None
    posted_at: datetime = Field(default_factory=now_utc)
    fetched_at: datetime = Field(default_factory=now_utc)


class MatchResult(BaseModel):
    score: int  # 0-100
    confidence: int  # 0-100
    decision: Literal["apply", "consider", "skip"]
    reasoning: str
    strengths: List[str] = []
    gaps: List[str] = []
    expected_outcome: str = ""


class Application(BaseModel):
    model_config = ConfigDict(extra="ignore")
    application_id: str
    user_id: str
    job_id: str
    status: Literal["discovered", "applied", "under_review", "interview", "offer", "rejected"] = "discovered"
    timeline: List[Dict[str, Any]] = []  # [{status, timestamp, reason, confidence}]
    match: Optional[Dict[str, Any]] = None
    notes: str = ""
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class EmailMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email_id: str
    user_id: str
    thread_id: str
    from_addr: str
    from_name: str
    subject: str
    body: str
    received_at: datetime = Field(default_factory=now_utc)
    # AI extracted
    classification: str = "other"  # interview | rejection | offer | recruiter | follow_up | other
    intent: str = ""
    next_steps: List[str] = []
    linked_job_id: Optional[str] = None
    linked_application_id: Optional[str] = None
    is_read: bool = False


class Mission(BaseModel):
    model_config = ConfigDict(extra="ignore")
    mission_id: str
    user_id: str
    date: str  # YYYY-MM-DD
    title: str
    description: str
    action_type: str  # apply | review | update_cv | reflect | research
    target_id: Optional[str] = None  # job_id or application_id
    xp_reward: int = 10
    completed: bool = False
    completed_at: Optional[datetime] = None
    reasoning: str = ""  # why this mission, AI generated


class CoachMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message_id: str
    user_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime = Field(default_factory=now_utc)


# ─── Billing Models ──────────────────────────────────────────
class CheckoutRequest(BaseModel):
    """Request to create a Stripe checkout session."""
    plan_id: Literal["pro", "team"]  # Only valid plans allowed
    origin_url: str  # Return URL after checkout


class ReferralApplyRequest(BaseModel):
    """Request to apply a referral code."""
    code: str  # Referral code to apply


# ── Input Validation Models (replacing raw dict parameters) ──────

class CVScoreRequest(BaseModel):
    """Request to score a CV against a job description."""
    cv_text: str = Field(default="", description="CV/resume text")
    job_description: str = Field(default="", description="Job description to score against")
    job_id: Optional[str] = Field(default=None, description="Optional job ID to pull description from DB")


class CoverLetterRequest(BaseModel):
    """Request to generate a cover letter."""
    cv_text: str = Field(default="", description="CV/resume text")
    job_description: str = Field(default="", description="Target job description")
    job_id: Optional[str] = Field(default=None, description="Optional job ID")
    job_title: str = Field(default="Target Role", description="Job title")
    company: str = Field(default="", description="Company name")
    tone: str = Field(default="professional", description="Letter tone")


class ExtensionJobRequest(BaseModel):
    """Request from browser extension to save a job."""
    title: str = Field(..., min_length=1, description="Job title")
    company: str = Field(default="", description="Company name")
    url: str = Field(default="", description="Job listing URL")
    description: str = Field(default="", description="Job description")
    location: str = Field(default="", description="Job location")
    salary: str = Field(default="", description="Salary info")


class CoachChatRequest(BaseModel):
    """Request to send a message to the career coach."""
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    context: str = Field(default="", description="Additional context")


class CareerROIRequest(BaseModel):
    """Request for career ROI analysis."""
    job_title: str = Field(..., min_length=1, description="Target job title")
    company: str = Field(default="", description="Target company")
    salary: float = Field(default=0, ge=0, description="Expected salary")
    current_salary: float = Field(default=0, ge=0, description="Current salary")


class NotificationUpdateRequest(BaseModel):
    """Request to update notification preferences."""
    email_notifications: bool = Field(default=True)
    push_notifications: bool = Field(default=True)
    job_alerts: bool = Field(default=True)
    weekly_digest: bool = Field(default=True)
