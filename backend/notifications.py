"""In-app notification helper — imported by routes and XP engine."""
from datetime import datetime, timezone
from db import notifications
from models import new_id
import logging

logger = logging.getLogger(__name__)

VALID_TYPES = {
    "new_match", "interview_detected", "streak_reward",
    "onboarding_complete", "digest_ready", "system_warning", "level_up",
}


async def push_notification(
    user_id: str,
    notif_type: str,
    title: str,
    message: str,
    metadata: dict | None = None,
) -> None:
    """Persist one notification. Fire-and-forget — never raises."""
    try:
        await notifications.insert_one({
            "notification_id": new_id("ntf"),
            "user_id":         user_id,
            "type":            notif_type if notif_type in VALID_TYPES else "system_warning",
            "title":           title,
            "message":         message,
            "metadata":        metadata or {},
            "read":            False,
            "created_at":      datetime.now(timezone.utc).isoformat(),
        })
    except Exception as ex:
        logger.warning("push_notification failed (%s): %s", notif_type, ex)
