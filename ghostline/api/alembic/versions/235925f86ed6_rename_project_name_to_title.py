"""rename project name to title

Revision ID: 235925f86ed6
Revises: c3b9f49732db
Create Date: 2025-07-01 21:14:27.127116

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '235925f86ed6'
down_revision: Union[str, None] = 'c3b9f49732db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename 'name' column to 'title' in projects table
    op.alter_column('projects', 'name', new_column_name='title')
    
    # Also need to increase the length limit from 255 to 500 to match the model
    op.alter_column('projects', 'title', 
                    type_=sa.String(length=500), 
                    existing_type=sa.String(length=255),
                    existing_nullable=False)


def downgrade() -> None:
    # Revert the column length change
    op.alter_column('projects', 'title', 
                    type_=sa.String(length=255), 
                    existing_type=sa.String(length=500),
                    existing_nullable=False)
    
    # Rename 'title' column back to 'name'
    op.alter_column('projects', 'title', new_column_name='name')
