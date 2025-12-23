-- Fix projects table schema mismatch
-- The Python model expects different column names than what exists in the database

BEGIN;

-- 1. Rename 'name' to 'title'
ALTER TABLE projects RENAME COLUMN name TO title;

-- 2. Add missing 'subtitle' column
ALTER TABLE projects ADD COLUMN IF NOT EXISTS subtitle VARCHAR(500);

-- 3. Rename 'target_length' to 'target_page_count'
ALTER TABLE projects RENAME COLUMN target_length TO target_page_count;

-- 4. Add missing 'target_word_count' column with default
ALTER TABLE projects ADD COLUMN IF NOT EXISTS target_word_count INTEGER DEFAULT 20000;

-- 5. Add missing 'language' column with default
ALTER TABLE projects ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en';

-- Verify the changes
\d projects

COMMIT;

-- If everything looks good, the changes will be committed
-- If there's an error, everything will be rolled back 