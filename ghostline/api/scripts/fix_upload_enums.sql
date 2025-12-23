-- Fix MaterialType enum values for file upload
ALTER TYPE materialtype ADD VALUE IF NOT EXISTS 'TEXT';
ALTER TYPE materialtype ADD VALUE IF NOT EXISTS 'PDF';
ALTER TYPE materialtype ADD VALUE IF NOT EXISTS 'DOCX';
ALTER TYPE materialtype ADD VALUE IF NOT EXISTS 'AUDIO';
ALTER TYPE materialtype ADD VALUE IF NOT EXISTS 'IMAGE';
ALTER TYPE materialtype ADD VALUE IF NOT EXISTS 'VIDEO';
ALTER TYPE materialtype ADD VALUE IF NOT EXISTS 'MARKDOWN';
ALTER TYPE materialtype ADD VALUE IF NOT EXISTS 'HTML';
ALTER TYPE materialtype ADD VALUE IF NOT EXISTS 'NOTE';
ALTER TYPE materialtype ADD VALUE IF NOT EXISTS 'VOICE_MEMO';
ALTER TYPE materialtype ADD VALUE IF NOT EXISTS 'OTHER';

-- Fix ProcessingStatus enum values
ALTER TYPE processingstatus ADD VALUE IF NOT EXISTS 'UPLOADING';
ALTER TYPE processingstatus ADD VALUE IF NOT EXISTS 'PENDING';
ALTER TYPE processingstatus ADD VALUE IF NOT EXISTS 'PROCESSING';
ALTER TYPE processingstatus ADD VALUE IF NOT EXISTS 'COMPLETED';
ALTER TYPE processingstatus ADD VALUE IF NOT EXISTS 'FAILED';
ALTER TYPE processingstatus ADD VALUE IF NOT EXISTS 'READY';

-- Show current values
SELECT 'MaterialType values:' as info;
SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'materialtype') ORDER BY enumsortorder;

SELECT 'ProcessingStatus values:' as info;
SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'processingstatus') ORDER BY enumsortorder; 