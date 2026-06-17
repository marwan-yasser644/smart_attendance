-- ============================================================================
-- Migration: RBAC support for the Smart Attendance System (Neon / PostgreSQL)
-- ============================================================================
-- Adds the RBAC columns to the existing `lecturers` table (the application's
-- user table) and normalises any legacy role values onto the canonical
-- two-role set: DEAN and TA.
--
-- This migration is SAFE and IDEMPOTENT:
--   * All ADD COLUMN statements use IF NOT EXISTS.
--   * No rows are deleted; existing data is preserved.
--   * Re-running it has no additional effect.
--
-- HOW TO RUN ON NEON:
--   1. Open the Neon Console -> your project -> "SQL Editor".
--   2. Paste this entire file and click "Run".
--   (Or: psql "$DATABASE_URL" -f migrations/001_add_rbac.sql)
-- ============================================================================

BEGIN;

-- 1. New columns (nullable/defaulted so existing rows remain valid) --------------
ALTER TABLE lecturers ADD COLUMN IF NOT EXISTS username VARCHAR(80);
ALTER TABLE lecturers ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE lecturers ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Widen / ensure the role column can hold the canonical values ---------------
ALTER TABLE lecturers ALTER COLUMN role TYPE VARCHAR(20);
ALTER TABLE lecturers ALTER COLUMN role SET DEFAULT 'TA';

-- 3. Normalise legacy / invalid role values ------------------------------------
--    'admin'    -> 'DEAN'
--    everything else that is not already DEAN/TA -> 'TA' (least privilege)
UPDATE lecturers SET role = 'DEAN' WHERE lower(role) IN ('admin', 'dean');
UPDATE lecturers SET role = 'TA'   WHERE role IS NULL OR role NOT IN ('DEAN', 'TA');

-- 4. Backfill usernames for any existing rows that lack one --------------------
--    Derives a username from the local-part of the email; guarantees uniqueness
--    by appending the row id when needed.
UPDATE lecturers
   SET username = split_part(email, '@', 1) || '_' || id
 WHERE username IS NULL OR username = '';

-- 5. Enforce uniqueness on username -------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS ix_lecturers_username ON lecturers (username);

-- 6. Integrity guard: keep the role column constrained to the two roles --------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_lecturers_role'
    ) THEN
        ALTER TABLE lecturers
            ADD CONSTRAINT ck_lecturers_role CHECK (role IN ('DEAN', 'TA'));
    END IF;
END$$;

COMMIT;

-- ============================================================================
-- Verification (optional): run after the migration
--   SELECT id, name, email, username, role, is_active, must_change_password
--   FROM lecturers ORDER BY id;
-- ============================================================================
