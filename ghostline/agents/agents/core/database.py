"""
Database integration for agent system.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator


class DatabaseConfig:
    """Database configuration."""
    
    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://ghostline:ghostline@localhost/ghostline"
        )
        
        # Create engine with connection pooling
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session context manager."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Global database configuration
db_config = DatabaseConfig() 