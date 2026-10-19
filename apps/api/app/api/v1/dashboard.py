import psycopg
from fastapi import APIRouter, Depends

from app.api.v1.schemas import DashboardSummaryResponse
from app.core.authorization import get_current_membership
from app.core.config import settings
from app.infrastructure.database.organization_members import OrganizationMembership

router = APIRouter()


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    membership: OrganizationMembership = Depends(get_current_membership),
):
    org_id = membership.organization_id

    with psycopg.connect(settings.database_url) as conn, conn.cursor() as cursor:
        # Contribution totals
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0), COUNT(*)
            FROM contributions
            WHERE organization_id = %s
            """,
            (org_id,),
        )
        total_contributions, contribution_count = cursor.fetchone()

        # Allocation totals
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0), COUNT(*)
            FROM allocations
            WHERE organization_id = %s AND status != 'CANCELLED'
            """,
            (org_id,),
        )
        total_allocated, allocation_count = cursor.fetchone()

        # Distribution totals
        cursor.execute(
            """
            SELECT COALESCE(SUM(quantity), 0), COUNT(*)
            FROM distributions
            WHERE organization_id = %s
            """,
            (org_id,),
        )
        total_distributed_quantity, distribution_count = cursor.fetchone()

        # Inventory item count
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM resource_batches
            WHERE organization_id = %s
            """,
            (org_id,),
        )
        inventory_items = cursor.fetchone()[0]

    return DashboardSummaryResponse(
        total_contributions=float(total_contributions),
        contribution_count=contribution_count,
        total_allocated=float(total_allocated),
        allocation_count=allocation_count,
        distribution_count=distribution_count,
        total_distributed_quantity=float(total_distributed_quantity),
        inventory_items=inventory_items,
    )
