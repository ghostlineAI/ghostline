"""add missing project columns subtitle target_page_count target_word_count language

Revision ID: eb1f54a9d067
Revises: 235925f86ed6
Create Date: 2025-07-01 21:14:55.726831

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb1f54a9d067'
down_revision: Union[str, None] = '235925f86ed6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing columns to projects table
    op.add_column('projects', sa.Column('subtitle', sa.String(length=500), nullable=True))
    op.add_column('projects', sa.Column('target_page_count', sa.Integer(), nullable=True))
    op.add_column('projects', sa.Column('target_word_count', sa.Integer(), nullable=True))
    op.add_column('projects', sa.Column('language', sa.String(length=10), nullable=True))
    
    # Set default values for existing rows
    op.execute("UPDATE projects SET target_page_count = 80 WHERE target_page_count IS NULL")
    op.execute("UPDATE projects SET target_word_count = 20000 WHERE target_word_count IS NULL")
    op.execute("UPDATE projects SET language = 'en' WHERE language IS NULL")


def downgrade() -> None:
    # Remove the added columns
    op.drop_column('projects', 'language')
    op.drop_column('projects', 'target_word_count')
    op.drop_column('projects', 'target_page_count')
    op.drop_column('projects', 'subtitle')
