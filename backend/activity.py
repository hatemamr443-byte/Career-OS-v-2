"""Activity logging helper — imported by all routes that produce user events."""
from datetime import datetime, timezone
from db import activity_logs
from models import new_id
import logging

logger = logging.getLogger(__name__)


async def log_activity(
    user_id: str,
    event_type: str,
    title: str,
    description: str,
    metadata: dict | None = None,
) -> None:
    """Persist one user activity event. Fire-and-forget — never raises."""
    try:
        await activity_logs.insert_one({
            "activity_id": new_id("act"),
            "user_id":     user_id,
            "event_type":  event_type,
            "title":       title,
            "description": description,
            "metadata":    metadata or {},
            "created_at":  datetime.now(timezone.utc).isoformat(),
        })
    except Exception as ex:
        logger.warning("activity_log failed (%s): %s", event_type, ex)
