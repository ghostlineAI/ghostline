"""expand BookGenre enum to include new values

Revision ID: c3b9f49732db
Revises: ff58d1e57171_fixed
Create Date: 2025-06-29 17:16:41.064706

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3b9f49732db'
down_revision: Union[str, None] = 'ff58d1e57171_fixed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add new values to BookGenre enum."""
    # Use a PL/pgSQL block to handle existing values gracefully
    op.execute("""
        DO $$
        BEGIN
            -- Add fiction
            BEGIN
                ALTER TYPE bookgenre ADD VALUE 'fiction';
            EXCEPTION WHEN duplicate_object THEN
                RAISE NOTICE 'Value fiction already exists';
            END;
            
            -- Add non_fiction
            BEGIN
                ALTER TYPE bookgenre ADD VALUE 'non_fiction';
            EXCEPTION WHEN duplicate_object THEN
                RAISE NOTICE 'Value non_fiction already exists';
            END;
            
            -- Add memoir
            BEGIN
                ALTER TYPE bookgenre ADD VALUE 'memoir';
            EXCEPTION WHEN duplicate_object THEN
                RAISE NOTICE 'Value memoir already exists';
            END;
            
            -- Add business
            BEGIN
                ALTER TYPE bookgenre ADD VALUE 'business';
            EXCEPTION WHEN duplicate_object THEN
                RAISE NOTICE 'Value business already exists';
            END;
            
            -- Add self_help
            BEGIN
                ALTER TYPE bookgenre ADD VALUE 'self_help';
            EXCEPTION WHEN duplicate_object THEN
                RAISE NOTICE 'Value self_help already exists';
            END;
            
            -- Add academic
            BEGIN
                ALTER TYPE bookgenre ADD VALUE 'academic';
            EXCEPTION WHEN duplicate_object THEN
                RAISE NOTICE 'Value academic already exists';
            END;
            
            -- Add technical
            BEGIN
                ALTER TYPE bookgenre ADD VALUE 'technical';
            EXCEPTION WHEN duplicate_object THEN
                RAISE NOTICE 'Value technical already exists';
            END;
            
            -- Add other
            BEGIN
                ALTER TYPE bookgenre ADD VALUE 'other';
            EXCEPTION WHEN duplicate_object THEN
                RAISE NOTICE 'Value other already exists';
            END;
        END$$;
    """)
    

def downgrade() -> None:
    """Downgrade schema - Note: PostgreSQL doesn't support removing enum values."""
    # Unfortunately, PostgreSQL doesn't allow removing values from enums
    # The best we can do is document this limitation
    pass  # Cannot remove enum values in PostgreSQL
