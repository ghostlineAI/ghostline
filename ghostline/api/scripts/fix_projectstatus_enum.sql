-- Fix projectstatus enum by adding missing values
-- Python model expects: draft, processing, ready, published, archived
-- Database has: CREATED, DATA_COLLECTION, OUTLINE_GENERATION, WRITING, REVIEW, COMPLETED, ARCHIVED

-- Add missing enum values
ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'draft';
ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'processing';
ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'ready';
ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'published';
ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'archived';

-- Also add uppercase versions since the code sends uppercase
ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'DRAFT';
ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'PROCESSING';
ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'READY';
ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'PUBLISHED';

-- Verify the values
SELECT unnest(enum_range(NULL::projectstatus)) ORDER BY 1; 