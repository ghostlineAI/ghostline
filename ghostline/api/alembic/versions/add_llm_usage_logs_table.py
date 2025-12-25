"""Add llm_usage_logs table for granular cost tracking

Revision ID: add_llm_usage_logs
Revises: phase7_schema_reconciliation
Create Date: 2024-12-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_llm_usage_logs'
down_revision = 'phase7_schema_fix'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'llm_usage_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Context columns
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('workflow_run_id', sa.String(255), nullable=True),
        sa.Column('chapter_number', sa.Integer(), nullable=True),
        
        # Agent info
        sa.Column('agent_name', sa.String(100), nullable=False),
        sa.Column('agent_role', sa.String(50), nullable=True),
        
        # Model info (using strings instead of enums for simplicity)
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('call_type', sa.String(50), nullable=True, default='chat'),
        sa.Column('is_fallback', sa.Boolean(), default=False),
        sa.Column('fallback_reason', sa.String(255), nullable=True),
        
        # Token usage
        sa.Column('input_tokens', sa.Integer(), default=0),
        sa.Column('output_tokens', sa.Integer(), default=0),
        sa.Column('total_tokens', sa.Integer(), default=0),
        sa.Column('embedding_dimensions', sa.Integer(), nullable=True),
        
        # Cost (USD)
        sa.Column('input_cost', sa.Float(), default=0.0),
        sa.Column('output_cost', sa.Float(), default=0.0),
        sa.Column('total_cost', sa.Float(), default=0.0),
        sa.Column('input_price_per_1k', sa.Float(), nullable=True),
        sa.Column('output_price_per_1k', sa.Float(), nullable=True),
        
        # Performance
        sa.Column('duration_ms', sa.Integer(), default=0),
        
        # Request/Response metadata
        sa.Column('prompt_preview', sa.Text(), nullable=True),
        sa.Column('response_preview', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('extra_data', postgresql.JSONB(), default=dict),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['generation_tasks.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for common query patterns
    op.create_index('ix_llm_usage_logs_project_id', 'llm_usage_logs', ['project_id'])
    op.create_index('ix_llm_usage_logs_task_id', 'llm_usage_logs', ['task_id'])
    op.create_index('ix_llm_usage_logs_workflow_run_id', 'llm_usage_logs', ['workflow_run_id'])
    op.create_index('ix_llm_usage_logs_agent_name', 'llm_usage_logs', ['agent_name'])
    op.create_index('ix_llm_usage_logs_model', 'llm_usage_logs', ['model'])
    op.create_index('ix_llm_usage_logs_provider', 'llm_usage_logs', ['provider'])
    op.create_index('ix_llm_usage_logs_call_type', 'llm_usage_logs', ['call_type'])
    op.create_index('ix_llm_usage_logs_created_at', 'llm_usage_logs', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_llm_usage_logs_created_at', table_name='llm_usage_logs')
    op.drop_index('ix_llm_usage_logs_call_type', table_name='llm_usage_logs')
    op.drop_index('ix_llm_usage_logs_provider', table_name='llm_usage_logs')
    op.drop_index('ix_llm_usage_logs_model', table_name='llm_usage_logs')
    op.drop_index('ix_llm_usage_logs_agent_name', table_name='llm_usage_logs')
    op.drop_index('ix_llm_usage_logs_workflow_run_id', table_name='llm_usage_logs')
    op.drop_index('ix_llm_usage_logs_task_id', table_name='llm_usage_logs')
    op.drop_index('ix_llm_usage_logs_project_id', table_name='llm_usage_logs')
    
    # Drop table
    op.drop_table('llm_usage_logs')

