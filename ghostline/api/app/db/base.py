"""
Database base configuration and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Import all models here to ensure they are registered with SQLAlchemy
from app.models.user import User  # noqa
from app.models.billing_plan import BillingPlan  # noqa
from app.models.api_key import APIKey  # noqa
from app.models.project import Project  # noqa
from app.models.source_material import SourceMaterial  # noqa
from app.models.content_chunk import ContentChunk  # noqa
from app.models.voice_profile import VoiceProfile  # noqa
from app.models.book_outline import BookOutline  # noqa
from app.models.chapter import Chapter  # noqa
from app.models.chapter_revision import ChapterRevision  # noqa
from app.models.generation_task import GenerationTask  # noqa
from app.models.token_transaction import TokenTransaction  # noqa
from app.models.qa_finding import QaFinding  # noqa
from app.models.exported_book import ExportedBook  # noqa
from app.models.notification import Notification  # noqa


# Dependency to get DB session
def get_db():
    """
    Get database session.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
