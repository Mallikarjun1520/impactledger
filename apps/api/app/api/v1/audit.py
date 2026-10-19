from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.schemas import AuditEventResponse
from app.core.authorization import require_role
from app.infrastructure.database.audit_logs import list_audit_logs
from app.infrastructure.database.organization_members import OrganizationMembership

router = APIRouter()

AUDIT_VIEW_ROLES = ("ADMIN", "AUDITOR")


@router.get("/audit", response_model=list[AuditEventResponse])
def list_audit_logs_endpoint(
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    actor_id: UUID | None = Query(None),
    entity_id: UUID | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    membership: OrganizationMembership = Depends(
        require_role(*AUDIT_VIEW_ROLES)
    ),
):
    return list_audit_logs(
        organization_id=membership.organization_id,
        action=action,
        entity_type=entity_type,
        actor_id=actor_id,
        entity_id=entity_id,
        start=start,
        end=end,
        limit=limit,
        offset=offset,
    )
