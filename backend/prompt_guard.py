"""Prompt injection protection for all LLM calls.

Implements structured delimiters and input sanitization to prevent
user-controlled content from overriding system instructions.
"""
import re
import logging

logger = logging.getLogger(__name__)

# Patterns that suggest prompt injection attempts
_INJECTION_PATTERNS = [
    r"ignore (previous|all|the above) instructions?",
    r"(forget|disregard) (everything|all|the) (above|previous|prior)",
    r"you are (now|actually) (a|an) ",
    r"(act|pretend|behave) as (if )?you (are|were)",
    r"your (new|actual|real|true) (role|purpose|task|instruction)",
    r"(return|output|print|give me) (the )?(system prompt|instructions)",
    r"(translate|convert|rewrite) (the )?(above|this) (to|as)",
    r"<!--.*-->",           # HTML comments
    r"\[INST\]",             # Llama instruction tokens
    r"<\|.*\|>",             # Common special tokens
]

_COMPILED = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _INJECTION_PATTERNS]


def detect_injection(text: str, field: str = "input") -> bool:
    """Return True if potential prompt injection detected."""
    if not text:
        return False
    for pattern in _COMPILED:
        if pattern.search(text):
            logger.warning("Potential prompt injection in %s: %.100s", field, text)
            return True
    return False


def sanitize_user_input(text: str, max_length: int = 3000) -> str:
    """Sanitize user input for safe inclusion in prompts.
    
    - Truncates to max_length
    - Wraps in clear delimiters
    - Logs injection attempts (but does NOT block — LLM handles it)
    """
    if not text:
        return ""
    text = text[:max_length].strip()
    detect_injection(text)
    return text


def wrap_user_content(label: str, content: str, max_length: int = 3000) -> str:
    """Wrap user content with XML-style delimiters to separate from instructions."""
    safe = sanitize_user_input(content, max_length)
    return f"<{label}>\n{safe}\n</{label}>"


def build_safe_prompt(sections: dict[str, tuple[str, int]]) -> str:
    """Build a safe prompt with labeled, delimited sections.
    
    Args:
        sections: {label: (content, max_length)}
    
    Returns:
        Structured prompt string with delimiters
    
    Example:
        build_safe_prompt({
            "job_description": (job_text, 2000),
            "candidate_cv": (cv_text, 2500),
        })
    """
    parts = []
    for label, (content, max_len) in sections.items():
        parts.append(wrap_user_content(label, content, max_len))
    return "\n\n".join(parts)
