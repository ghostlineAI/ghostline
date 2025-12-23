#!/usr/bin/env python3
"""
Test all database models and their relationships.
"""

import sys
from datetime import UTC, datetime
from decimal import Decimal

# Test imports
try:
    from app.models import (
        APIKey,
        BillingPlan,
        BookOutline,
        Chapter,
        ChapterRevision,
        ContentChunk,
        ExportedBook,
        GenerationTask,
        Notification,
        Project,
        QaFinding,
        SourceMaterial,
        TokenTransaction,
        User,
        VoiceProfile,
    )
    from app.models.book_outline import OutlineStatus
    from app.models.chapter import BookGenre
    from app.models.exported_book import ExportFormat
    from app.models.generation_task import TaskStatus, TaskType
    from app.models.notification import NotificationChannel, NotificationType
    from app.models.project import ProjectStatus
    from app.models.qa_finding import FindingStatus, FindingType
    from app.models.source_material import MaterialType, ProcessingStatus
    from app.models.token_transaction import TransactionType

    print("✅ All model imports successful!")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


# Test model instantiation
def test_models():
    """Test creating instances of all models."""
    print("\n🧪 Testing model instantiation...")

    try:
        # 1. BillingPlan
        BillingPlan(
            name="Premium",
            monthly_tokens=500000,
            price_per_month=Decimal("99.99"),
            features={"max_projects": 10, "priority_support": True},
        )
        print("✅ BillingPlan")

        # 2. User
        user = User(
            email="test@example.com",
            full_name="Test User",
            cognito_sub="12345-67890",
            billing_plan_id=1,
            token_balance=100000,
        )
        print("✅ User")

        # 3. APIKey
        APIKey(
            user_id=1,
            name="Test API Key",
            key_hash="hashed_key_here",
            last_used_at=datetime.now(UTC),
        )
        print("✅ APIKey")

        # 4. Project
        project = Project(
            owner_id=1,
            title="My Book",
            description="A test book",
            genre=BookGenre.NON_FICTION,
            target_audience="Business professionals",
            target_word_count=50000,
            status=ProjectStatus.ACTIVE,
        )
        print("✅ Project")

        # 5. SourceMaterial
        source = SourceMaterial(
            project_id=1,
            material_type=MaterialType.PDF,
            file_name="research.pdf",
            s3_key="projects/1/materials/research.pdf",
            file_size=1024000,
            processing_status=ProcessingStatus.COMPLETED,
        )
        print("✅ SourceMaterial")

        # 6. ContentChunk
        chunk = ContentChunk(
            source_material_id=1,
            content="This is a test chunk of content.",
            chunk_index=0,
            start_page=1,
            embedding=[0.1] * 1536,  # 1536-dimensional vector
        )
        print("✅ ContentChunk")

        # 7. VoiceProfile
        VoiceProfile(
            project_id=1,
            analysis_version="1.0",
            vocabulary_patterns={"common_words": ["test", "example"]},
            sentence_structures={"avg_length": 15.5},
            tone_markers={"formal": 0.8},
            voice_embedding=[0.2] * 1536,
        )
        print("✅ VoiceProfile")

        # 8. BookOutline
        BookOutline(
            project_id=1,
            parent_id=None,
            item_type="part",
            order_index=0,
            title="Part I: Introduction",
            description="Opening section",
            target_word_count=15000,
            status=OutlineStatus.APPROVED,
        )
        print("✅ BookOutline")

        # 9. Chapter
        chapter = Chapter(
            project_id=1,
            book_outline_id=1,
            chapter_number=1,
            title="Getting Started",
            target_word_count=5000,
            status="draft",
        )
        print("✅ Chapter")

        # 10. ChapterRevision
        revision = ChapterRevision(
            chapter_id=1,
            revision_number=1,
            content="Chapter content here...",
            word_count=4500,
            similarity_score=0.92,
            tokens_used=1500,
            feedback="Great start!",
        )
        print("✅ ChapterRevision")

        # 11. GenerationTask
        GenerationTask(
            project_id=1,
            task_type=TaskType.CHAPTER_GENERATION,
            status=TaskStatus.COMPLETED,
            agent_name="ChapterAgent",
            input_data={"chapter_id": 1},
            output_data={"revision_id": 1},
            tokens_used=1500,
        )
        print("✅ GenerationTask")

        # 12. TokenTransaction
        TokenTransaction(
            user_id=1,
            transaction_type=TransactionType.DEBIT,
            amount=1500,
            balance_after=98500,
            description="Chapter generation",
            project_id=1,
            task_id=1,
        )
        print("✅ TokenTransaction")

        # 13. QaFinding
        QaFinding(
            project_id=1,
            chapter_id=1,
            finding_type=FindingType.TIMELINE_ERROR,
            severity="high",
            description="Date inconsistency found",
            location={"page": 5, "paragraph": 3},
            suggested_fix="Change 2023 to 2024",
            status=FindingStatus.RESOLVED,
        )
        print("✅ QaFinding")

        # 14. ExportedBook
        ExportedBook(
            project_id=1,
            format=ExportFormat.PDF,
            version=1,
            file_name="my_book.pdf",
            s3_key="exports/1/book.pdf",
            file_size_bytes=2048000,
            title="My Book",
            author_name="Test Author",
        )
        print("✅ ExportedBook")

        # 15. Notification
        Notification(
            user_id=1,
            notification_type=NotificationType.CHAPTER_READY,
            channel=NotificationChannel.IN_APP,
            title="Chapter Ready for Review",
            message="Chapter 1 has been generated",
            data={"chapter_id": 1, "project_id": 1},
            read_at=None,
        )
        print("✅ Notification")

        print("\n✅ All models instantiated successfully!")

        # Test relationships
        print("\n🔗 Testing model relationships...")

        # User -> Projects
        user.projects = [project]
        print("✅ User -> Projects")

        # Project -> SourceMaterials
        project.source_materials = [source]
        print("✅ Project -> SourceMaterials")

        # SourceMaterial -> ContentChunks
        source.chunks = [chunk]
        print("✅ SourceMaterial -> ContentChunks")

        # Project -> Chapters
        project.chapters = [chapter]
        print("✅ Project -> Chapters")

        # Chapter -> Revisions
        chapter.revisions = [revision]
        print("✅ Chapter -> Revisions")

        print("\n✅ All relationships tested successfully!")

    except Exception as e:
        print(f"\n❌ Error testing models: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(test_models())
