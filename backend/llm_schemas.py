"""Pydantic schemas for LLM output validation.

All LLM responses MUST be validated through these schemas before
reaching database or business logic. Prevents stored XSS and
bad data from corrupting the system.
"""
import json
import re
import logging
from typing import Any, Optional, Type
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ── Safe JSON parsing (replaces parse_json_loose) ────────────────

def parse_llm_json(text: str, schema: Type[BaseModel] | None = None) -> dict:
    """Parse LLM JSON output safely with optional schema validation.
    
    Args:
        text: Raw LLM output text
        schema: Optional Pydantic model to validate against
    
    Returns:
        Validated dict or empty dict on failure
    """
    if not text or not text.strip():
        return {}

    raw: dict = {}

    # Try direct JSON parse
    try:
        raw = json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try JSON fence extraction
    if not raw:
        fence = re.search(r"```(?:json)?\s*(\{[^`]+\})\s*```", text, re.DOTALL)
        if fence:
            try:
                raw = json.loads(fence.group(1))
            except json.JSONDecodeError:
                pass

    # Last resort: greedy match (non-nested only for safety)
    if not raw:
        m = re.search(r"\{[^{}]+\}", text, re.DOTALL)
        if m:
            try:
                raw = json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

    if not raw:
        logger.warning("parse_llm_json: could not extract JSON from LLM output")
        return {}

    # Validate against schema if provided
    if schema:
        try:
            validated = schema.model_validate(raw)
            return validated.model_dump()
        except Exception as e:
            logger.warning("parse_llm_json: schema validation failed: %s", e)
            # Return raw but sanitize strings to prevent XSS
            return _sanitize_dict(raw)

    return _sanitize_dict(raw)


def _sanitize_dict(data: Any, depth: int = 0) -> Any:
    """Recursively sanitize dict values to prevent XSS."""
    if depth > 10:  # Prevent infinite recursion
        return data
    if isinstance(data, dict):
        return {k: _sanitize_dict(v, depth + 1) for k, v in data.items() if isinstance(k, str)}
    if isinstance(data, list):
        return [_sanitize_dict(item, depth + 1) for item in data[:100]]  # Limit list size
    if isinstance(data, str):
        # Strip dangerous HTML/script patterns
        sanitized = re.sub(r"<script[^>]*>.*?</script>", "", data, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"on\w+\s*=\s*[\"'][^\"']*[\"']", "", sanitized, flags=re.IGNORECASE)
        return sanitized[:10000]  # Limit string length
    if isinstance(data, (int, float, bool)) or data is None:
        return data
    return str(data)[:1000]


# ── LLM Output Schemas ────────────────────────────────────────────

class ATSScoreOutput(BaseModel):
    """Schema for ATS scoring LLM output."""
    score: int = Field(default=0, ge=0, le=100)
    matching_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    format_issues: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    summary: str = Field(default="", max_length=1000)

    @field_validator("score", mode="before")
    @classmethod
    def clamp_score(cls, v: Any) -> int:
        try:
            return max(0, min(100, int(v)))
        except (TypeError, ValueError):
            return 0


class MatchScoreOutput(BaseModel):
    """Schema for job match scoring LLM output."""
    score: int = Field(default=50, ge=0, le=100)
    confidence: int = Field(default=50, ge=0, le=100)
    decision: str = Field(default="consider")
    reasoning: str = Field(default="", max_length=2000)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    salary_estimate: Optional[str] = Field(default=None, max_length=200)
    growth_potential: Optional[str] = Field(default=None, max_length=500)

    @field_validator("score", "confidence", mode="before")
    @classmethod
    def clamp_score(cls, v: Any) -> int:
        try:
            return max(0, min(100, int(v)))
        except (TypeError, ValueError):
            return 50

    @field_validator("decision", mode="before")
    @classmethod
    def validate_decision(cls, v: Any) -> str:
        valid = {"apply", "consider", "skip", "strong_apply", "avoid"}
        s = str(v).lower().strip()
        return s if s in valid else "consider"


class CoverLetterOutput(BaseModel):
    """Schema for cover letter LLM output."""
    letter: str = Field(default="", max_length=5000)
    subject: str = Field(default="", max_length=200)


class MissionOutput(BaseModel):
    """Schema for daily mission LLM output."""
    missions: list[dict] = Field(default_factory=list)


class InsightOutput(BaseModel):
    """Schema for career insights LLM output."""
    totals: Optional[dict] = None
    funnel: Optional[dict] = None
    insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
