"""Public projection endpoints. No auth required. Backed by the sanitized
views from migration 022."""
import logging

import psycopg
from fastapi import APIRouter, HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["public"])


def _rows(sql: str, args: tuple = ()) -> list[dict]:
    """Run a read-only query against the sanitized public views.

    A database failure must be surfaced as an explicit service error rather
    than an empty result so callers cannot mistake an outage for a genuine
    zero total. The detail returned to clients is intentionally generic; the
    underlying SQL error is logged server-side only.
    """
    try:
        with psycopg.connect(settings.database_url) as conn, conn.cursor(
            row_factory=psycopg.rows.dict_row
        ) as cur:
            cur.execute(sql, args)
            return cur.fetchall()
    except psycopg.Error:
        logger.exception("Public transparency query failed")
        raise HTTPException(
            status_code=503,
            detail="Public transparency data is temporarily unavailable",
        ) from None


@router.get("/organizations/{org_slug}/initiatives")
def list_initiatives(org_slug: str) -> list[dict]:
    return _rows(
        """
        SELECT *
          FROM public_initiative_summary
         WHERE org_slug = %s
         ORDER BY initiative_name
        """,
        (org_slug,),
    )


@router.get("/organizations/{org_slug}/initiatives/{initiative_slug}")
def initiative_detail(org_slug: str, initiative_slug: str) -> dict:
    rows = _rows(
        """
        SELECT *
          FROM public_initiative_summary
         WHERE org_slug = %s AND initiative_slug = %s
        """,
        (org_slug, initiative_slug),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Initiative not found")
    summary = rows[0]
    initiative_id = summary["initiative_id"]

    resources = _rows(
        """
        SELECT *
          FROM public_initiative_resources
         WHERE initiative_id = %s
        """,
        (initiative_id,),
    )
    flags = _rows(
        """
        SELECT *
          FROM public_reconciliation_flags
         WHERE initiative_id = %s
         ORDER BY created_at DESC
         LIMIT 100
        """,
        (initiative_id,),
    )
    anchors = _rows(
        """
        SELECT *
          FROM public_anchor_batches
         WHERE organization_id = (
                 SELECT organization_id
                   FROM initiatives
                  WHERE id = %s
               )
         ORDER BY submitted_at DESC
         LIMIT 20
        """,
        (initiative_id,),
    )

    return {
        "summary": summary,
        "resources": resources,
        "reconciliation_flags": flags,
        "anchor_batches": anchors,
    }


@router.get("/anchors/{batch_id}")
def anchor_public(batch_id: str) -> dict:
    rows = _rows(
        "SELECT * FROM public_anchor_batches WHERE id = %s",
        (batch_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Anchor batch not found or not yet public")
    return rows[0]
