"""Evidence upload + link (rulebook §11, ADR-007).

The bytes go to Supabase Storage via the service-role key; the row records
metadata + SHA-256. OCR is invoked synchronously against the noop provider
by default; a future scheduled worker will re-run it against the configured
provider.
"""
from __future__ import annotations

import hashlib
from uuid import UUID, uuid4

import httpx
import psycopg
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from psycopg.types.json import Jsonb

from app.core.authorization import get_current_membership
from app.core.config import settings
from app.domain.events import DomainEventInput, DomainEventType
from app.infrastructure.database.domain_events import _record_in_txn
from app.infrastructure.database.organization_members import OrganizationMembership
from app.services.ocr import OcrRequest, build_ocr_provider

router = APIRouter(prefix="/organizations/{org_id}/evidence", tags=["evidence"])

_BUCKET = "evidence"


def _storage_url(path: str) -> str:
    return f"{settings.supabase_url}/storage/v1/object/{_BUCKET}/{path}"


def _upload_to_storage(path: str, content_type: str, data: bytes) -> None:
    """PUT the object using the service-role key."""
    resp = httpx.post(
        _storage_url(path),
        headers={
            "authorization": f"Bearer {settings.supabase_service_role_key}",
            "content-type": content_type,
            "x-upsert": "true",
        },
        content=data,
        timeout=30.0,
    )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Supabase Storage upload failed: {resp.status_code} {resp.text[:200]}",
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    org_id: UUID,
    kind: str = Form(..., pattern=r"^(INVOICE|RECEIPT|DELIVERY_NOTE|GOODS_RECEIPT|BANK_STATEMENT|"
                                  r"PAYMENT_RECEIPT|DONATION_RECEIPT|STOCK_COUNT|DAMAGE_REPORT|"
                                  r"DISPOSAL_RECORD|PHOTO|OTHER)$"),
    file: UploadFile = File(...),
    membership: OrganizationMembership = Depends(get_current_membership),
) -> dict:
    if membership.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Org mismatch")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Empty file")
    content_sha256 = hashlib.sha256(data).hexdigest()
    content_type = file.content_type or "application/octet-stream"

    evidence_id = uuid4()
    storage_path = f"org/{org_id}/evidence/{evidence_id}/{file.filename}"

    # OCR advisory extraction (rulebook §12). Failures do not corrupt the row.
    ocr = build_ocr_provider()
    try:
        extraction = ocr.extract(OcrRequest(
            filename=file.filename or "unknown",
            content_type=content_type,
            data=data,
        ))
        extracted_fields = extraction.fields
    except Exception:                                     # noqa: BLE001
        extracted_fields = {}

    # Upload to storage BEFORE writing the row so a failed upload doesn't
    # leave orphan metadata pointing at nothing.
    _upload_to_storage(storage_path, content_type, data)

    with psycopg.connect(settings.database_url) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        INSERT INTO evidence (
                            id, organization_id, kind, filename, content_type,
                            size_bytes, content_sha256, storage_path, status,
                            extracted_fields, uploaded_by
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, 'EXTRACTED',
                            %s, %s
                        )
                        RETURNING id, organization_id, kind::text, filename,
                                  content_type, size_bytes, content_sha256,
                                  storage_path, status::text, uploaded_at
                        """,
                        (
                            evidence_id, org_id, kind, file.filename,
                            content_type, len(data), content_sha256,
                            storage_path, Jsonb(extracted_fields),
                            membership.user_id,
                        ),
                    )
                    row = cur.fetchone()
                except psycopg.errors.UniqueViolation:
                    raise HTTPException(status_code=409, detail="Duplicate evidence (same sha256 already exists in this org)")

            _record_in_txn(
                conn,
                DomainEventInput(
                    organization_id=org_id,
                    event_type=DomainEventType.EVIDENCE_UPLOADED,
                    aggregate_type="evidence",
                    aggregate_id=evidence_id,
                    performed_by=membership.user_id,
                    payload={
                        "kind": kind,
                        "filename": file.filename,
                        "content_sha256": content_sha256,
                        "size_bytes": len(data),
                    },
                ),
            )

    return {
        "id": row[0],
        "organization_id": row[1],
        "kind": row[2],
        "filename": row[3],
        "content_type": row[4],
        "size_bytes": row[5],
        "content_sha256": row[6],
        "storage_path": row[7],
        "status": row[8],
        "uploaded_at": row[9],
    }


@router.post("/{evidence_id}/link/{event_id}", status_code=200)
def link_evidence(
    org_id: UUID,
    evidence_id: UUID,
    event_id: UUID,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> dict:
    if membership.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Org mismatch")

    with psycopg.connect(settings.database_url) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        INSERT INTO evidence_links (
                            organization_id, evidence_id, domain_event_id
                        ) VALUES (%s, %s, %s)
                        RETURNING id
                        """,
                        (org_id, evidence_id, event_id),
                    )
                    link_id = cur.fetchone()[0]
                except psycopg.errors.UniqueViolation:
                    raise HTTPException(status_code=409, detail="Already linked")
                except psycopg.errors.ForeignKeyViolation as e:
                    raise HTTPException(status_code=404, detail=str(e).splitlines()[0])

            _record_in_txn(
                conn,
                DomainEventInput(
                    organization_id=org_id,
                    event_type=DomainEventType.EVIDENCE_LINKED,
                    aggregate_type="evidence",
                    aggregate_id=evidence_id,
                    performed_by=membership.user_id,
                    payload={"linked_event_id": str(event_id)},
                ),
            )
    return {"link_id": link_id}
