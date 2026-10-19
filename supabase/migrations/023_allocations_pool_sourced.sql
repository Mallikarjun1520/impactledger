-- Pool-sourced allocations don't have a single owning contribution
-- (rulebook §6 fungibility). Make contribution_id nullable, and enforce
-- that exactly one of (contribution_id, fund_pool_id) is set.

ALTER TABLE allocations
    ALTER COLUMN contribution_id DROP NOT NULL;

ALTER TABLE allocations
    ADD CONSTRAINT allocations_source_shape
    CHECK (
        (contribution_id IS NOT NULL AND fund_pool_id IS NULL)
     OR (contribution_id IS NULL     AND fund_pool_id IS NOT NULL)
    );
