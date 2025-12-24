"""Phase 7: Schema reconciliation - align Alembic with ORM models

Revision ID: phase7_schema_fix
Revises: ff58d1e57171_fixed
Create Date: 2025-12-23

This migration reconciles schema differences between ORM models and database.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "phase7_schema_fix"
down_revision: str = "a5539dbb4d4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Reconcile schema with ORM models.
    
    Fixes:
    1. content_chunks: add missing columns, make token_count nullable
    2. voice_profiles: add stylometry columns for numeric voice metrics
    3. generation_tasks: add missing enum values and columns
    4. source_materials: ensure local_path column exists
    """
    
    # =========================================================================
    # 1. FIX content_chunks TABLE
    # =========================================================================
    
    # Add project_id column (nullable for existing rows, then we can populate)
    op.add_column(
        "content_chunks",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    # Add token_count column (nullable - ORM says NOT NULL but we need migration to work)
    op.add_column(
        "content_chunks",
        sa.Column("token_count", sa.Integer(), nullable=True, default=0)
    )
    
    # Add word_count column
    op.add_column(
        "content_chunks",
        sa.Column("word_count", sa.Integer(), nullable=True)
    )
    
    # Add position tracking columns
    op.add_column(
        "content_chunks",
        sa.Column("start_page", sa.Integer(), nullable=True)
    )
    op.add_column(
        "content_chunks",
        sa.Column("end_page", sa.Integer(), nullable=True)
    )
    op.add_column(
        "content_chunks",
        sa.Column("start_char", sa.Integer(), nullable=True)
    )
    op.add_column(
        "content_chunks",
        sa.Column("end_char", sa.Integer(), nullable=True)
    )
    
    # Add embedding_model column
    op.add_column(
        "content_chunks",
        sa.Column("embedding_model", sa.String(100), nullable=True, server_default="text-embedding-3-small")
    )
    
    # Add source_reference for citation tracking
    op.add_column(
        "content_chunks",
        sa.Column("source_reference", sa.String(500), nullable=True)
    )
    
    # Add FK constraint for project_id
    op.create_foreign_key(
        "fk_content_chunks_project",
        "content_chunks",
        "projects",
        ["project_id"],
        ["id"],
    )
    
    # =========================================================================
    # 2. FIX voice_profiles TABLE - add stylometry columns
    # =========================================================================
    
    # Add tone column
    op.add_column(
        "voice_profiles",
        sa.Column("tone", sa.String(100), nullable=True)
    )
    
    # Add style column
    op.add_column(
        "voice_profiles",
        sa.Column("style", sa.String(100), nullable=True)
    )
    
    # Add numeric metrics for stylometry
    op.add_column(
        "voice_profiles",
        sa.Column("avg_sentence_length", sa.Float(), nullable=True)
    )
    op.add_column(
        "voice_profiles",
        sa.Column("vocabulary_complexity", sa.Float(), nullable=True)
    )
    op.add_column(
        "voice_profiles",
        sa.Column("avg_word_length", sa.Float(), nullable=True)
    )
    op.add_column(
        "voice_profiles",
        sa.Column("punctuation_density", sa.Float(), nullable=True)
    )
    
    # Add array columns for patterns (PostgreSQL ARRAY)
    op.add_column(
        "voice_profiles",
        sa.Column("common_phrases", postgresql.ARRAY(sa.String()), nullable=True)
    )
    op.add_column(
        "voice_profiles",
        sa.Column("sentence_starters", postgresql.ARRAY(sa.String()), nullable=True)
    )
    op.add_column(
        "voice_profiles",
        sa.Column("transition_words", postgresql.ARRAY(sa.String()), nullable=True)
    )
    
    # Add stylistic_elements JSON
    op.add_column(
        "voice_profiles",
        sa.Column("stylistic_elements", sa.JSON(), nullable=True)
    )
    
    # Add similarity_threshold for voice matching
    op.add_column(
        "voice_profiles",
        sa.Column("similarity_threshold", sa.Float(), nullable=True, server_default="0.85")
    )
    
    # =========================================================================
    # 3. FIX generation_tasks TABLE - add missing columns and enum values
    # =========================================================================
    
    # Add new enum values to taskstatus
    # PostgreSQL requires explicit ALTER TYPE for adding enum values
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'QUEUED'")
    op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'PAUSED'")
    
    # Add new enum values to tasktype
    op.execute("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'CONSISTENCY_CHECK'")
    op.execute("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'SAFETY_CHECK'")
    op.execute("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'FINAL_COMPILATION'")
    
    # Add estimated_cost column
    op.add_column(
        "generation_tasks",
        sa.Column("estimated_cost", sa.Float(), nullable=True, server_default="0.0")
    )
    
    # Add execution_time column
    op.add_column(
        "generation_tasks",
        sa.Column("execution_time", sa.Integer(), nullable=True)
    )
    
    # Add progress column
    op.add_column(
        "generation_tasks",
        sa.Column("progress", sa.Integer(), nullable=True, server_default="0")
    )
    
    # Add current_step column
    op.add_column(
        "generation_tasks",
        sa.Column("current_step", sa.String(500), nullable=True)
    )
    
    # Add retry columns
    op.add_column(
        "generation_tasks",
        sa.Column("retry_count", sa.Integer(), nullable=True, server_default="0")
    )
    op.add_column(
        "generation_tasks",
        sa.Column("max_retries", sa.Integer(), nullable=True, server_default="3")
    )
    
    # Add celery_task_id column
    op.add_column(
        "generation_tasks",
        sa.Column("celery_task_id", sa.String(255), nullable=True)
    )
    
    # Add workflow_state for LangGraph checkpoint storage
    op.add_column(
        "generation_tasks",
        sa.Column("workflow_state", sa.JSON(), nullable=True)
    )
    
    # =========================================================================
    # 4. FIX source_materials TABLE - add local_path
    # =========================================================================
    
    op.add_column(
        "source_materials",
        sa.Column("local_path", sa.String(1000), nullable=True)
    )
    
    # Add extracted_content column (alias for extracted_text in some code paths)
    op.add_column(
        "source_materials",
        sa.Column("extracted_content", sa.Text(), nullable=True)
    )
    
    # =========================================================================
    # 5. CREATE workflow_checkpoints TABLE for durable LangGraph state
    # =========================================================================
    
    op.create_table(
        "workflow_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", sa.String(255), nullable=False),
        sa.Column("checkpoint_id", sa.String(255), nullable=False),
        sa.Column("parent_checkpoint_id", sa.String(255), nullable=True),
        sa.Column("checkpoint_data", sa.LargeBinary(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["task_id"], ["generation_tasks.id"]),
    )
    
    # Index for fast checkpoint lookups
    op.create_index(
        "idx_workflow_checkpoints_thread",
        "workflow_checkpoints",
        ["thread_id", "checkpoint_id"],
        unique=True,
    )


def downgrade() -> None:
    """Revert schema changes."""
    
    # Drop workflow_checkpoints table
    op.drop_index("idx_workflow_checkpoints_thread", table_name="workflow_checkpoints")
    op.drop_table("workflow_checkpoints")
    
    # Remove source_materials columns
    op.drop_column("source_materials", "extracted_content")
    op.drop_column("source_materials", "local_path")
    
    # Remove generation_tasks columns
    op.drop_column("generation_tasks", "workflow_state")
    op.drop_column("generation_tasks", "celery_task_id")
    op.drop_column("generation_tasks", "max_retries")
    op.drop_column("generation_tasks", "retry_count")
    op.drop_column("generation_tasks", "current_step")
    op.drop_column("generation_tasks", "progress")
    op.drop_column("generation_tasks", "execution_time")
    op.drop_column("generation_tasks", "estimated_cost")
    
    # Remove voice_profiles columns
    op.drop_column("voice_profiles", "similarity_threshold")
    op.drop_column("voice_profiles", "stylistic_elements")
    op.drop_column("voice_profiles", "transition_words")
    op.drop_column("voice_profiles", "sentence_starters")
    op.drop_column("voice_profiles", "common_phrases")
    op.drop_column("voice_profiles", "punctuation_density")
    op.drop_column("voice_profiles", "avg_word_length")
    op.drop_column("voice_profiles", "vocabulary_complexity")
    op.drop_column("voice_profiles", "avg_sentence_length")
    op.drop_column("voice_profiles", "style")
    op.drop_column("voice_profiles", "tone")
    
    # Remove content_chunks columns
    op.drop_constraint("fk_content_chunks_project", "content_chunks", type_="foreignkey")
    op.drop_column("content_chunks", "source_reference")
    op.drop_column("content_chunks", "embedding_model")
    op.drop_column("content_chunks", "end_char")
    op.drop_column("content_chunks", "start_char")
    op.drop_column("content_chunks", "end_page")
    op.drop_column("content_chunks", "start_page")
    op.drop_column("content_chunks", "word_count")
    op.drop_column("content_chunks", "token_count")
    op.drop_column("content_chunks", "project_id")
    
    # Note: Cannot easily remove enum values in PostgreSQL
    # The new enum values will remain but be unused


