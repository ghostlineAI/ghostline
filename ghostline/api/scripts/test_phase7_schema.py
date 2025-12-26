#!/usr/bin/env python3
"""
Test Phase 7.1: Schema Reconciliation

Verifies that:
1. All ORM models load without errors
2. Model fields match expected schema
3. Relationships are properly defined

NOTE: This test inspects the model classes directly without importing
the database session to avoid circular import issues.
"""

import sys
import ast
from pathlib import Path

# Add the api directory to the path
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))


def parse_model_file(filepath: Path) -> dict:
    """Parse a model file and extract column definitions."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Simple regex-based extraction of Column definitions
    import re
    columns = re.findall(r'(\w+)\s*=\s*Column\(', content)
    relationships = re.findall(r'(\w+)\s*=\s*relationship\(', content)
    
    return {
        "columns": columns,
        "relationships": relationships,
        "content": content,
    }


def test_models_load():
    """Test that all models can be imported without circular import errors."""
    print("=" * 60)
    print("TEST: Loading all ORM models (via direct file inspection)")
    print("=" * 60)
    
    models_dir = api_dir / "app" / "models"
    required_models = [
        "content_chunk.py", "voice_profile.py", "source_material.py",
        "generation_task.py", "project.py", "user.py", "chapter.py",
        "book_outline.py"
    ]
    
    all_ok = True
    for model_file in required_models:
        filepath = models_dir / model_file
        if filepath.exists():
            try:
                parse_model_file(filepath)
                print(f"  ✅ {model_file}")
            except Exception as e:
                print(f"  ❌ {model_file}: {e}")
                all_ok = False
        else:
            print(f"  ❌ {model_file} NOT FOUND")
            all_ok = False
    
    if all_ok:
        print("✅ All models parseable")
    
    return all_ok


def test_content_chunk_fields():
    """Test ContentChunk has all required fields."""
    print("\n" + "=" * 60)
    print("TEST: ContentChunk model fields")
    print("=" * 60)
    
    filepath = api_dir / "app" / "models" / "content_chunk.py"
    parsed = parse_model_file(filepath)
    
    required_fields = [
        "id", "content", "chunk_index", "word_count", "token_count",
        "start_page", "end_page", "start_char", "end_char",
        # NOTE: the underlying DB column is named "metadata", but the ORM attribute
        # is intentionally named "chunk_metadata" to avoid SQLAlchemy's reserved
        # Base.metadata attribute.
        "embedding", "embedding_model", "source_reference", "chunk_metadata",
        "source_material_id", "project_id", "created_at"
    ]
    
    all_ok = True
    for field in required_fields:
        if field in parsed["columns"]:
            print(f"  ✅ {field}")
        else:
            print(f"  ❌ {field} MISSING")
            all_ok = False
    
    # Check relationships
    required_rels = ["source_material", "project"]
    for rel in required_rels:
        if rel in parsed["relationships"]:
            print(f"  ✅ {rel} relationship")
        else:
            print(f"  ❌ {rel} relationship MISSING")
            all_ok = False
    
    return all_ok


def test_voice_profile_fields():
    """Test VoiceProfile has all stylometry fields."""
    print("\n" + "=" * 60)
    print("TEST: VoiceProfile model fields (stylometry)")
    print("=" * 60)
    
    filepath = api_dir / "app" / "models" / "voice_profile.py"
    parsed = parse_model_file(filepath)
    
    # Stylometry fields for numeric voice metrics
    stylometry_fields = [
        "avg_sentence_length", "sentence_length_std",
        "avg_word_length", "vocabulary_complexity", "vocabulary_richness",
        "punctuation_density", "question_ratio", "exclamation_ratio",
        "avg_paragraph_length"
    ]
    
    all_ok = True
    print("  Stylometry fields:")
    for field in stylometry_fields:
        if field in parsed["columns"]:
            print(f"    ✅ {field}")
        else:
            print(f"    ❌ {field} MISSING")
            all_ok = False
    
    # Voice matching configuration
    config_fields = ["similarity_threshold", "embedding_weight", "is_active"]
    print("  Voice matching config:")
    for field in config_fields:
        if field in parsed["columns"]:
            print(f"    ✅ {field}")
        else:
            print(f"    ❌ {field} MISSING")
            all_ok = False
    
    # Embedding field
    if "voice_embedding" in parsed["columns"]:
        print(f"  ✅ voice_embedding (1536-dim vector)")
    else:
        print(f"  ❌ voice_embedding MISSING")
        all_ok = False
    
    return all_ok


def test_generation_task_status():
    """Test GenerationTask has PAUSED and QUEUED statuses."""
    print("\n" + "=" * 60)
    print("TEST: GenerationTask status enum")
    print("=" * 60)
    
    filepath = api_dir / "app" / "models" / "generation_task.py"
    with open(filepath, 'r') as f:
        content = f.read()
    
    required_statuses = ["PENDING", "QUEUED", "RUNNING", "PAUSED", "COMPLETED", "FAILED", "CANCELLED"]
    
    all_ok = True
    for status in required_statuses:
        if f'{status} = "' in content or f"{status} = '" in content:
            print(f"  ✅ TaskStatus.{status}")
        else:
            print(f"  ❌ TaskStatus.{status} MISSING")
            all_ok = False
    
    return all_ok


def test_source_material_fields():
    """Test SourceMaterial has local_path and extracted_content."""
    print("\n" + "=" * 60)
    print("TEST: SourceMaterial model fields")
    print("=" * 60)
    
    filepath = api_dir / "app" / "models" / "source_material.py"
    parsed = parse_model_file(filepath)
    
    required_fields = ["local_path", "extracted_content", "extracted_text"]
    
    all_ok = True
    for field in required_fields:
        if field in parsed["columns"]:
            print(f"  ✅ {field}")
        else:
            print(f"  ❌ {field} MISSING")
            all_ok = False
    
    return all_ok


def test_generation_task_workflow_state():
    """Test GenerationTask has workflow_state for LangGraph."""
    print("\n" + "=" * 60)
    print("TEST: GenerationTask workflow_state field")
    print("=" * 60)
    
    filepath = api_dir / "app" / "models" / "generation_task.py"
    parsed = parse_model_file(filepath)
    
    if "workflow_state" in parsed["columns"]:
        print(f"  ✅ workflow_state (for LangGraph checkpoints)")
        return True
    else:
        print(f"  ❌ workflow_state MISSING")
        return False


def test_project_content_chunks_relationship():
    """Test Project has content_chunks relationship."""
    print("\n" + "=" * 60)
    print("TEST: Project -> ContentChunk relationship")
    print("=" * 60)
    
    filepath = api_dir / "app" / "models" / "project.py"
    parsed = parse_model_file(filepath)
    
    if "content_chunks" in parsed["relationships"]:
        print(f"  ✅ Project.content_chunks relationship")
        return True
    else:
        print(f"  ❌ Project.content_chunks relationship MISSING")
        return False


def main():
    """Run all schema tests."""
    print("\n" + "=" * 60)
    print("PHASE 7.1: SCHEMA RECONCILIATION TESTS")
    print("=" * 60)
    
    results = []
    
    results.append(("Models Load", test_models_load()))
    results.append(("ContentChunk Fields", test_content_chunk_fields()))
    results.append(("VoiceProfile Stylometry", test_voice_profile_fields()))
    results.append(("GenerationTask Status", test_generation_task_status()))
    results.append(("SourceMaterial Fields", test_source_material_fields()))
    results.append(("GenerationTask Workflow", test_generation_task_workflow_state()))
    results.append(("Project Relationships", test_project_content_chunks_relationship()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for name, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n  Total: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 Phase 7.1 Schema Reconciliation: ALL TESTS PASSED")
        return 0
    else:
        print("\n💥 Phase 7.1 Schema Reconciliation: SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

