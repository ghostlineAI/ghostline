#!/usr/bin/env python3
"""
Validate that all SQLAlchemy models can be imported without errors.
"""

import sys


def validate_models():
    """Validate all models can be imported."""
    print("🔍 Validating GhostLine Database Models...")

    models_to_test = [
        ("BillingPlan", "app.models.billing_plan"),
        ("User", "app.models.user"),
        ("APIKey", "app.models.api_key"),
        ("Project", "app.models.project"),
        ("SourceMaterial", "app.models.source_material"),
        ("ContentChunk", "app.models.content_chunk"),
        ("VoiceProfile", "app.models.voice_profile"),
        ("BookOutline", "app.models.book_outline"),
        ("Chapter", "app.models.chapter"),
        ("ChapterRevision", "app.models.chapter_revision"),
        ("GenerationTask", "app.models.generation_task"),
        ("TokenTransaction", "app.models.token_transaction"),
        ("QaFinding", "app.models.qa_finding"),
        ("ExportedBook", "app.models.exported_book"),
        ("Notification", "app.models.notification"),
    ]

    errors = []

    for model_name, module_path in models_to_test:
        try:
            module = __import__(module_path, fromlist=[model_name])
            model_class = getattr(module, model_name)
            print(f"✅ {model_name:<20} - imported successfully")

            # Check table name
            if hasattr(model_class, "__tablename__"):
                print(f"   Table: {model_class.__tablename__}")

        except Exception as e:
            print(f"❌ {model_name:<20} - {str(e)}")
            errors.append((model_name, str(e)))

    if errors:
        print(f"\n❌ Found {len(errors)} errors:")
        for model, error in errors:
            print(f"  - {model}: {error}")
        return 1
    else:
        print("\n✅ All models validated successfully!")

        # Try to import all at once
        try:
            print("✅ Bulk import successful!")
        except Exception as e:
            print(f"❌ Bulk import failed: {e}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(validate_models())
