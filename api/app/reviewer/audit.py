"""
The audit trail.

Every state change from intake onward writes one row here. The table is
append-only in the database (trigger plus REVOKE), so this module has no update
or delete function - there is nothing to call, by design.

Recording must never be the reason a legitimate action fails: if the write
itself errors we log it loudly and let the operation stand, rather than rolling
back a document the reviewer can see in front of them.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.reviewer.context import ReviewerContext

logger = logging.getLogger(__name__)

# The vocabulary of things worth recording. Kept explicit so the trail stays
# greppable and new event types are a deliberate choice.
CASE_CREATED = "case_created"
CASE_UPDATED = "case_updated"
DOCUMENT_UPLOADED = "document_uploaded"
DOCUMENT_DUPLICATE_REJECTED = "document_duplicate_rejected"
DOCUMENT_CLASSIFIED = "document_classified"
DOCUMENT_CLASSIFICATION_FAILED = "document_classification_failed"
DOCUMENT_TYPE_OVERRIDDEN = "document_type_overridden"
DOCUMENT_VIEWED = "document_viewed"


def record(
    ctx: ReviewerContext,
    event_type: str,
    *,
    case_id: Optional[str] = None,
    object_ref: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Append one event. Failures are logged, never raised."""
    try:
        ctx.db.insert(
            "audit_events",
            {
                "org_id": ctx.org_id,
                "case_id": case_id,
                "actor_user_id": str(ctx.user_id),
                "event_type": event_type,
                "object_ref": object_ref,
                "payload": payload or {},
            },
            returning=False,
        )
    except Exception as exc:
        logger.error(
            "Failed to write audit event %s for case %s: %s", event_type, case_id, exc
        )
