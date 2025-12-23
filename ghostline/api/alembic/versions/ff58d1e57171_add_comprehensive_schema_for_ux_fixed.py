"""Add comprehensive schema for UX requirements - Fixed for pgvector

Revision ID: ff58d1e57171_fixed
Revises:
Create Date: 2025-06-27 06:07:45.385526

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ff58d1e57171_fixed"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create billing_plans table
    op.create_table(
        "billing_plans",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
        ),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("monthly_token_quota", sa.Integer(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=True),
        sa.Column("features", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create users table
    op.create_table(
        "users",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("cognito_sub", sa.String(length=255), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("billing_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("token_balance", sa.Integer(), nullable=True, default=0),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=True, default=False),
        sa.Column("is_verified", sa.Boolean(), nullable=True, default=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["billing_plan_id"],
            ["billing_plans.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_cognito_sub"), "users", ["cognito_sub"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(
        op.f("ix_users_stripe_customer_id"),
        "users",
        ["stripe_customer_id"],
        unique=True,
    )

    # Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("prefix", sa.String(length=10), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_keys_key_hash"), "api_keys", ["key_hash"], unique=True)
    op.create_index(op.f("ix_api_keys_prefix"), "api_keys", ["prefix"], unique=False)

    # Create projects table
    op.create_table(
        "projects",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "genre",
            sa.Enum(
                "FICTION",
                "NON_FICTION",
                "BIOGRAPHY",
                "AUTOBIOGRAPHY",
                "SELF_HELP",
                "BUSINESS",
                "TECHNICAL",
                "ACADEMIC",
                "OTHER",
                name="bookgenre",
            ),
            nullable=False,
        ),
        sa.Column("target_audience", sa.String(length=255), nullable=True),
        sa.Column("target_length", sa.Integer(), nullable=True),
        sa.Column("writing_style", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "CREATED",
                "DATA_COLLECTION",
                "OUTLINE_GENERATION",
                "WRITING",
                "REVIEW",
                "COMPLETED",
                "ARCHIVED",
                name="projectstatus",
            ),
            nullable=True,
        ),
        sa.Column("settings", sa.JSON(), nullable=True),
        sa.Column(
            "forked_from_project_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["forked_from_project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create source_materials table
    op.create_table(
        "source_materials",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
        ),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column(
            "material_type",
            sa.Enum(
                "TEXT",
                "PDF",
                "DOCX",
                "AUDIO",
                "IMAGE",
                "VIDEO",
                "MARKDOWN",
                "HTML",
                "NOTE",
                "VOICE_MEMO",
                "OTHER",
                name="materialtype",
            ),
            nullable=False,
        ),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("s3_bucket", sa.String(length=255), nullable=False),
        sa.Column("s3_key", sa.String(length=500), nullable=False),
        sa.Column("s3_url", sa.String(length=1000), nullable=True),
        sa.Column(
            "processing_status",
            sa.Enum(
                "UPLOADING",
                "PENDING",
                "PROCESSING",
                "COMPLETED",
                "FAILED",
                "READY",
                name="processingstatus",
            ),
            nullable=True,
        ),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("file_metadata", sa.JSON(), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create content_chunks table
    op.create_table(
        "content_chunks",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
        ),
        sa.Column("source_material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["source_material_id"],
            ["source_materials.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_content_chunks_embedding",
        "content_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="ivfflat",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    # Create voice_profiles table
    op.create_table(
        "voice_profiles",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sample_text", sa.Text(), nullable=True),
        sa.Column("style_attributes", sa.JSON(), nullable=True),
        sa.Column("voice_embedding", Vector(1536), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create book_outlines table
    op.create_table(
        "book_outlines",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("subtitle", sa.String(length=500), nullable=True),
        sa.Column("structure", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "APPROVED", "ARCHIVED", name="outlinestatus"),
            nullable=True,
        ),
        sa.Column("version", sa.Integer(), nullable=True, default=1),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("token_cost", sa.Integer(), nullable=True, default=0),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create chapters table
    op.create_table(
        "chapters",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True, default=0),
        sa.Column("outline", sa.Text(), nullable=True),
        sa.Column("key_points", sa.JSON(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True, default=1),
        sa.Column("is_final", sa.Boolean(), nullable=True, default=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("book_outline_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True, default="draft"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["book_outline_id"],
            ["book_outlines.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create chapter_revisions table
    op.create_table(
        "chapter_revisions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
        ),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True, default=0),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("ai_feedback", sa.Text(), nullable=True),
        sa.Column("user_feedback", sa.Text(), nullable=True),
        sa.Column("is_approved", sa.Boolean(), nullable=True, default=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("token_cost", sa.Integer(), nullable=True, default=0),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create generation_tasks table
    op.create_table(
        "generation_tasks",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "task_type",
            sa.Enum(
                "OUTLINE_GENERATION",
                "CHAPTER_GENERATION",
                "CHAPTER_REVISION",
                "VOICE_ANALYSIS",
                "CONTENT_REVIEW",
                "EXPORT_GENERATION",
                name="tasktype",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "RUNNING",
                "COMPLETED",
                "FAILED",
                "CANCELLED",
                name="taskstatus",
            ),
            nullable=True,
        ),
        sa.Column("agent_name", sa.String(length=100), nullable=True),
        sa.Column("input_data", sa.JSON(), nullable=True),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("token_usage", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("output_entity_type", sa.String(length=50), nullable=True),
        sa.Column("output_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create token_transactions table
    op.create_table(
        "token_transactions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generation_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "transaction_type",
            sa.Enum("CREDIT", "DEBIT", name="transactiontype"),
            nullable=False,
        ),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("transaction_metadata", sa.Text(), nullable=True),
        sa.Column("stripe_charge_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["generation_task_id"],
            ["generation_tasks.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create qa_findings table
    op.create_table(
        "qa_findings",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
        ),
        sa.Column("chapter_revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "finding_type",
            sa.Enum(
                "NAME_INCONSISTENCY",
                "TIMELINE_ERROR",
                "TONE_DRIFT",
                "FACTUAL_ERROR",
                "HALLUCINATION",
                "STYLE_DEVIATION",
                "CONTINUITY_ERROR",
                name="findingtype",
            ),
            nullable=False,
        ),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("start_position", sa.Integer(), nullable=True),
        sa.Column("end_position", sa.Integer(), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("suggested_fix", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("OPEN", "ACKNOWLEDGED", "RESOLVED", "WAIVED", name="findingstatus"),
            nullable=True,
        ),
        sa.Column("is_blocking", sa.Boolean(), nullable=True, default=False),
        sa.Column("user_comment", sa.Text(), nullable=True),
        sa.Column(
            "resolved_by_revision_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["chapter_revision_id"],
            ["chapter_revisions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_revision_id"],
            ["chapter_revisions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create exported_books table
    op.create_table(
        "exported_books",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "format",
            sa.Enum("PDF", "DOCX", "EPUB", "MARKDOWN", "HTML", name="exportformat"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("s3_key", sa.String(length=1000), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("subtitle", sa.String(length=500), nullable=True),
        sa.Column("author_name", sa.String(length=255), nullable=True),
        sa.Column("signed_url", sa.Text(), nullable=True),
        sa.Column("signed_url_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_cost", sa.Integer(), nullable=True, default=0),
        sa.Column("export_options", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create notifications table
    op.create_table(
        "notifications",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "notification_type",
            sa.Enum(
                "CHAPTER_READY",
                "GENERATION_COMPLETE",
                "EXPORT_READY",
                "QUALITY_ISSUE",
                "TOKEN_LOW",
                "TOKEN_DEPLETED",
                "BILLING_REMINDER",
                "SYSTEM_UPDATE",
                name="notificationtype",
            ),
            nullable=False,
        ),
        sa.Column(
            "channel",
            sa.Enum("IN_APP", "EMAIL", "SMS", "WEBHOOK", name="notificationchannel"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("action_url", sa.String(length=500), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_sent", sa.Boolean(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("notification_metadata", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order
    op.drop_table("notifications")
    op.drop_table("exported_books")
    op.drop_table("qa_findings")
    op.drop_table("token_transactions")
    op.drop_table("generation_tasks")
    op.drop_table("chapter_revisions")
    op.drop_table("chapters")
    op.drop_table("book_outlines")
    op.drop_table("voice_profiles")
    op.drop_index("idx_content_chunks_embedding", table_name="content_chunks")
    op.drop_table("content_chunks")
    op.drop_table("source_materials")
    op.drop_table("projects")
    op.drop_index(op.f("ix_api_keys_prefix"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_key_hash"), table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_index(op.f("ix_users_stripe_customer_id"), table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_cognito_sub"), table_name="users")
    op.drop_table("users")
    op.drop_table("billing_plans")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS notificationchannel")
    op.execute("DROP TYPE IF EXISTS notificationtype")
    op.execute("DROP TYPE IF EXISTS exportformat")
    op.execute("DROP TYPE IF EXISTS findingstatus")
    op.execute("DROP TYPE IF EXISTS findingtype")
    op.execute("DROP TYPE IF EXISTS transactiontype")
    op.execute("DROP TYPE IF EXISTS taskstatus")
    op.execute("DROP TYPE IF EXISTS tasktype")
    op.execute("DROP TYPE IF EXISTS outlinestatus")
    op.execute("DROP TYPE IF EXISTS processingstatus")
    op.execute("DROP TYPE IF EXISTS materialtype")
    op.execute("DROP TYPE IF EXISTS projectstatus")
    op.execute("DROP TYPE IF EXISTS bookgenre")
