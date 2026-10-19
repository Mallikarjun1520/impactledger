import re
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase" / "migrations"
SEED = MIGRATIONS.parent / "seed.sql"
AUDIT_POLICY_OCCURRENCES = 2


def _migration_text(version: int) -> str:
    matches = list(MIGRATIONS.glob(f"{version:03d}_*.sql"))
    assert len(matches) == 1
    return matches[0].read_text(encoding="utf-8")


def test_migration_versions_are_unique_and_contiguous_through_025():
    versions = sorted(
        int(match.group(1))
        for path in MIGRATIONS.glob("*.sql")
        if (match := re.match(r"^(\d{3})_", path.name))
    )

    assert versions == list(range(1, 26))


def test_domain_event_sequences_support_table_is_rls_protected():
    sql = _migration_text(25)
    assert "ALTER TABLE domain_event_sequences ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE domain_event_sequences FORCE ROW LEVEL SECURITY" in sql
    assert "REVOKE ALL ON domain_event_sequences FROM anon, authenticated" in sql
    assert "CREATE POLICY domain_event_sequences_service_role" in sql



def test_recorded_011_audit_logs_migration_is_preserved():
    audit_migration = MIGRATIONS / "011_create_audit_logs.sql"
    assert audit_migration.is_file()
    assert "CREATE TABLE audit_logs" in audit_migration.read_text(encoding="utf-8")
    assert len(list(MIGRATIONS.glob("011_*.sql"))) == 1


def test_seed_does_not_assign_multiple_initiative_ids_to_a_scalar():
    sql = SEED.read_text(encoding="utf-8")
    assert "RETURNING id INTO v_init_relief" not in sql
    assert "v_init_relief" not in sql


def test_dependent_migrations_follow_required_schema_order():
    assert "CREATE TABLE initiatives" in _migration_text(12)
    assert "CREATE TABLE fund_pools" in _migration_text(13)
    assert "CREATE TABLE commitments" in _migration_text(14)
    assert "ADD COLUMN purchase_order_id" in _migration_text(15)
    assert "CREATE TABLE evidence" in _migration_text(16)
    assert "CREATE TABLE domain_events" in _migration_text(17)
    assert "CREATE TABLE anchor_batches" in _migration_text(18)
    audit_events = _migration_text(19)
    assert "CREATE TABLE audit_events" in audit_events
    assert "FROM audit_logs AS legacy" in audit_events
    assert "'legacy_audit_log_id', legacy.id::text" in audit_events
    assert "legacy.timestamp" in audit_events
    assert "CREATE TRIGGER domain_events_forbid_mutation" in _migration_text(20)
    assert "CREATE OR REPLACE FUNCTION is_org_role" in _migration_text(21)
    assert "CREATE OR REPLACE VIEW public_initiative_summary" in _migration_text(22)
    assert "ALTER COLUMN contribution_id DROP NOT NULL" in _migration_text(23)
    assert "DROP POLICY IF EXISTS audit_events_select_member" in _migration_text(24)


def test_allocation_must_draw_from_exactly_one_source():
    sql = _migration_text(23)

    assert (
        "(contribution_id IS NOT NULL AND fund_pool_id IS NULL)"
        in sql
    )
    assert "(contribution_id IS NULL     AND fund_pool_id IS NOT NULL)" in sql
    assert "contribution_id IS NOT NULL AND fund_pool_id IS NOT NULL" not in sql


def test_audit_rls_limits_reads_and_keeps_service_policy_out_of_scope():
    sql = _migration_text(24)
    base_rls = _migration_text(21)

    assert "ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY" in sql
    assert "FOR ALL TO service_role" in sql
    assert "DROP POLICY IF EXISTS audit_events_select_member ON audit_events" in sql
    assert "FOR SELECT TO authenticated" in sql
    assert "is_org_role(organization_id, ARRAY['ADMIN', 'AUDITOR'])" in sql
    assert "organization_id IS NOT NULL" in sql
    assert "DROP POLICY" not in sql.replace(
        "DROP POLICY IF EXISTS audit_events_select_member ON audit_events", ""
    )
    assert base_rls.count("'audit_events'") >= AUDIT_POLICY_OCCURRENCES
    assert "CREATE POLICY %I_write_service" in base_rls


def test_public_projection_migration_exposes_only_expected_views():
    sql = _migration_text(22)

    for view_name in (
        "public_initiative_summary",
        "public_initiative_resources",
        "public_reconciliation_flags",
        "public_anchor_batches",
    ):
        assert f"VIEW {view_name}" in sql
        assert f"GRANT SELECT ON {view_name}" in sql
    assert "audit_events" not in sql


def test_audit_read_policy_names_both_authorized_roles():
    sql = _migration_text(24)
    assert "ARRAY['ADMIN', 'AUDITOR']" in sql


def test_rls_membership_helpers_bypass_their_own_member_policy_safely():
    sql = _migration_text(21)
    assert sql.count("SECURITY DEFINER") == 2
    assert sql.count("SET search_path = pg_catalog") == 2
    assert sql.count("FROM public.organization_members m") == 2
