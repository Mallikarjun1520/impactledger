# ADR-007 — Evidence stored off-chain

Status: Accepted
Date: 2026-09-24

## Context

Evidence contains PII (bank account numbers, donor addresses, beneficiary
identity documents), operational secrets (vendor pricing), and material that
we cannot legally or ethically publish. It is also large (PDFs, images).

## Decision

- Evidence bytes live in Supabase Storage (private bucket `evidence`, RLS
  applied via signed URLs from the backend only).
- The DB row `evidence` carries only metadata: `content_sha256`,
  `content_type`, `filename`, `size`, `uploaded_by`, `status`, and OCR
  extraction candidates.
- Only the SHA-256 of an evidence file may participate in the Merkle root
  (rulebook Rule 05), never the file itself.

## Reason

- Compliance (GDPR-like norms, donor privacy).
- On-chain size / cost.
- Rulebook Rule 05.

## Consequences

- Easier: privacy-preserving public transparency.
- Harder: verifying evidence integrity requires the platform to serve the
  bytes over a signed URL alongside the sha. A malicious platform *could*
  serve different bytes than were originally uploaded, but the sha and
  Merkle proof make this detectable.

## Revisit conditions

None.
