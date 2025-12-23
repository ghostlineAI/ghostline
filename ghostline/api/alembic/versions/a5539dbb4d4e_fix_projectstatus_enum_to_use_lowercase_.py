"""fix projectstatus enum to use lowercase values

Revision ID: a5539dbb4d4e
Revises: eb1f54a9d067
Create Date: 2025-07-01 21:24:34.654592

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5539dbb4d4e'
down_revision: Union[str, None] = 'eb1f54a9d067'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Since there's no data in the projects table, we can safely recreate the enum
    # First, alter the column to use text temporarily
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE text")
    
    # Drop the old enum type
    op.execute("DROP TYPE IF EXISTS projectstatus")
    
    # Create new enum with lowercase values
    op.execute("""
        CREATE TYPE projectstatus AS ENUM (
            'draft',
            'processing', 
            'ready',
            'published',
            'archived'
        )
    """)
    
    # Alter the column back to use the new enum
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE projectstatus USING status::projectstatus")
    
    # Set default value
    op.execute("ALTER TABLE projects ALTER COLUMN status SET DEFAULT 'draft'::projectstatus")


def downgrade() -> None:
    # Revert to uppercase values
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE text")
    op.execute("DROP TYPE IF EXISTS projectstatus")
    op.execute("""
        CREATE TYPE projectstatus AS ENUM (
            'CREATED',
            'DATA_COLLECTION',
            'OUTLINE_GENERATION',
            'WRITING', 
            'REVIEW',
            'COMPLETED',
            'ARCHIVED'
        )
    """)
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE projectstatus USING 'CREATED'::projectstatus")
    op.execute("ALTER TABLE projects ALTER COLUMN status DROP DEFAULT")
