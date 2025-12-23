---
Last Updated: 2025-06-28 09:30:52 PDT
---

# GhostLine Comprehensive Database Schema

## Overview

This document describes the complete database schema for GhostLine, designed to support the full user experience of an AI-powered book-writing platform. The schema is built on PostgreSQL with pgvector extension for AI embeddings.

## Database Architecture

The schema is organized into five main domains:

1. **Users & Billing** - User accounts, authentication, and token-based billing
2. **Projects & Source Data** - Book projects and raw materials (uploads, notes, recordings)
3. **Generation & Quality Assurance** - AI generation workflow and quality checks
4. **Export & Notifications** - Final outputs and user communication
5. **Supporting Infrastructure** - API keys, audit trails, and system metadata

## Core Tables

### 1. Users & Billing Domain

#### `users`
Central user account table with authentication and billing information.

**Key Fields:**
- `id` (UUID) - Primary key
- `email` (String) - Unique email address
- `username` (String) - Unique username
- `cognito_sub` (String) - AWS Cognito user ID for SSO
- `billing_plan_id` (UUID) - Current subscription tier
- `token_balance` (Integer) - Available tokens for AI generation
- `stripe_customer_id` (String) - Stripe customer reference

**Relationships:**
- Has many `projects`
- Has many `token_transactions`
- Has many `notifications`
- Belongs to `billing_plan`

#### `billing_plans`
Defines subscription tiers (Basic, Premium, Pro).

**Key Fields:**
- `name` (String) - Internal name (e.g., "basic", "premium")
- `display_name` (String) - User-facing name
- `monthly_token_quota` (Integer) - Tokens included per month
- `price_cents` (Integer) - Monthly price in cents
- `stripe_price_id` (String) - Stripe Price ID for subscriptions

#### `token_transactions`
Ledger of all token credits and debits.

**Key Fields:**
- `user_id` (UUID) - User who owns the transaction
- `transaction_type` (Enum) - CREDIT or DEBIT
- `amount` (Integer) - Number of tokens
- `balance_after` (Integer) - User's balance after transaction
- `description` (Text) - Human-readable description
- `project_id` (UUID) - Optional link to project
- `generation_task_id` (UUID) - Optional link to AI task

### 2. Projects & Source Data Domain

#### `projects`
Container for a book project.

**Key Fields:**
- `title` (String) - Project title
- `owner_id` (UUID) - User who owns the project
- `genre` (Enum) - FICTION, NON_FICTION, BIOGRAPHY, etc.
- `status` (Enum) - CREATED, DATA_COLLECTION, WRITING, etc.
- `forked_from_project_id` (UUID) - For "second edition" functionality

**Relationships:**
- Has many `source_materials`
- Has many `chapters`
- Has one `voice_profile`
- Has many `book_outlines`

#### `source_materials`
Raw materials uploaded or created by users.

**Key Fields:**
- `material_type` (Enum) - PDF, DOCX, AUDIO, IMAGE, NOTE, VOICE_MEMO
- `processing_status` (Enum) - UPLOADING, PROCESSING, READY, FAILED
- `s3_bucket` / `s3_key` - S3 storage location
- `extracted_text` (Text) - Processed text content
- `word_count` (Integer) - For progress tracking

**Relationships:**
- Has many `content_chunks`

#### `content_chunks`
Processed text chunks with embeddings for semantic search.

**Key Fields:**
- `content` (Text) - Chunk text (typically ~1000 tokens)
- `embedding` (Vector) - 1536-dimensional embedding
- `chunk_index` (Integer) - Order within source material

**Indexes:**
- Vector index on `embedding` for similarity search

### 3. Generation & QA Domain

#### `voice_profiles`
Author's writing style fingerprint.

**Key Fields:**
- `sample_text` (Text) - Representative writing samples
- `style_attributes` (JSON) - Analyzed style characteristics
- `embedding` (Vector) - Style embedding for comparison

#### `book_outlines`
Hierarchical book structure.

**Key Fields:**
- `structure` (JSON) - Nested parts/chapters/scenes
- `status` (Enum) - DRAFT, APPROVED, ARCHIVED
- `version` (Integer) - For revision tracking

Example structure:
```json
{
  "parts": [
    {
      "title": "Part I: The Beginning",
      "chapters": [
        {
          "title": "Chapter 1: Origins",
          "scenes": ["Opening", "Conflict", "Resolution"]
        }
      ]
    }
  ]
}
```

#### `chapters`
Individual book chapters.

**Key Fields:**
- `order` (Integer) - Chapter sequence
- `status` (String) - draft, reviewing, approved
- `book_outline_id` (UUID) - Links to outline

**Relationships:**
- Has many `chapter_revisions`

#### `chapter_revisions`
Versioned chapter content with feedback.

**Key Fields:**
- `content` (Text) - Markdown-formatted chapter text
- `similarity_score` (Float) - Style match to voice profile (0-1)
- `token_cost` (Integer) - AI tokens used
- `user_feedback` (Text) - User's revision requests
- `ai_feedback` (Text) - AI's analysis

#### `generation_tasks`
Background AI agent workflows.

**Key Fields:**
- `task_type` (Enum) - OUTLINE_GENERATION, CHAPTER_GENERATION, etc.
- `agent_name` (String) - Which AI agent handled it
- `output_entity_type` / `output_entity_id` - What was created

#### `qa_findings`
Issues found by automated QA.

**Key Fields:**
- `finding_type` (Enum) - NAME_INCONSISTENCY, TIMELINE_ERROR, etc.
- `severity` (String) - low, medium, high, critical
- `is_blocking` (Boolean) - Must fix before export?
- `status` (Enum) - OPEN, RESOLVED, WAIVED

### 4. Export & Notifications Domain

#### `exported_books`
Generated manuscripts in various formats.

**Key Fields:**
- `format` (Enum) - PDF, DOCX, EPUB, MARKDOWN, HTML
- `version` (Integer) - Export version number
- `s3_key` (String) - S3 location of file
- `signed_url` (Text) - Temporary download URL

#### `notifications`
User alerts and updates.

**Key Fields:**
- `notification_type` (Enum) - UPLOAD_COMPLETE, CHAPTER_READY, etc.
- `channel` (Enum) - IN_APP, EMAIL, WEBSOCKET
- `is_read` (Boolean) - Has user seen it?
- `link_url` (String) - Deep link to relevant content

## Key Design Decisions

### 1. Token-Based Billing
- Transparent usage tracking via `token_transactions`
- Pre-purchase and subscription models supported
- Every AI operation records token cost

### 2. Iterative Generation
- Multiple `chapter_revisions` per chapter
- User feedback incorporated into next revision
- Full history maintained for learning

### 3. Style Consistency
- `voice_profiles` capture author's style
- Every revision gets `similarity_score`
- Embeddings enable style matching

### 4. Quality Assurance
- Automated checks create `qa_findings`
- Users can resolve or waive issues
- Blocking issues prevent export

### 5. Forking & Versioning
- Projects can be forked for "second editions"
- All content maintains version history
- Exports are versioned and stored

## Indexes & Performance

### Primary Indexes
- All UUID primary keys
- Unique constraints on emails, usernames
- Foreign key indexes for relationships

### Vector Indexes
- IVFFlat index on `content_chunks.embedding`
- Cosine similarity for semantic search
- Optimized for 1536-dimensional vectors

### Query Patterns
- Project-scoped queries (most common)
- User token balance checks
- Similarity searches on content
- Status-based task queries

## Migration Strategy

The schema is deployed via Alembic migrations:

1. Create pgvector extension
2. Create all tables in dependency order
3. Create indexes and constraints
4. Seed initial billing plans

## Security Considerations

- Row-level security via application logic
- User can only access own projects
- API keys have scoped permissions
- Sensitive data (passwords) are hashed
- S3 URLs are pre-signed with expiration

## Future Considerations

### Potential Additions
- Collaboration features (project sharing)
- Version control branching
- Real-time collaboration cursors
- Advanced analytics tables
- Social features (comments, reviews)

### Scalability
- Partition large tables by project_id
- Archive completed projects
- Separate read replicas for analytics
- Consider time-series DB for metrics

This schema provides a solid foundation for the full GhostLine user experience while maintaining flexibility for future enhancements. 