-- Fix alembic_version table to support longer revision IDs
-- Run this if alembic_version table already exists with VARCHAR(32)

DO $$
BEGIN
    -- Check if alembic_version table exists and alter if needed
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'alembic_version'
        AND column_name = 'version_num'
    ) THEN
        -- Alter the column type to VARCHAR(128)
        ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128);
        RAISE NOTICE 'alembic_version.version_num altered to VARCHAR(128)';
    END IF;
END $$;
