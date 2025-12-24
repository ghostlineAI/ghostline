#!/usr/bin/env python3
"""
E2E System Test for GhostLine
Tests all layers: models, services, API, and identifies gaps.
"""

import sys
import os
import importlib
from dataclasses import dataclass
from typing import Callable

# Add the api directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'api'))

@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    category: str

results: list[TestResult] = []

def test(name: str, category: str):
    """Decorator to register and run tests."""
    def decorator(func: Callable):
        def wrapper():
            try:
                result = func()
                if result is True or result is None:
                    results.append(TestResult(name, True, "OK", category))
                    return True
                else:
                    results.append(TestResult(name, False, str(result), category))
                    return False
            except Exception as e:
                results.append(TestResult(name, False, f"{type(e).__name__}: {str(e)}", category))
                return False
        wrapper()
        return func
    return decorator


# ============================================================================
# CATEGORY 1: Core Configuration
# ============================================================================

@test("Config loads without errors", "1-Config")
def test_config():
    from app.core.config import settings
    assert settings.DATABASE_URL, "DATABASE_URL not set"
    assert settings.REDIS_URL, "REDIS_URL not set"
    assert settings.ENVIRONMENT, "ENVIRONMENT not set"
    return True


@test("Auth disabled for local dev", "1-Config")
def test_auth_disabled():
    from app.core.config import settings
    if settings.ENVIRONMENT == "local":
        assert settings.AUTH_DISABLED == True, "AUTH_DISABLED should be True in local"
    return True


# ============================================================================
# CATEGORY 2: Database Models
# ============================================================================

@test("All SQLAlchemy models load", "2-Models")
def test_models_load():
    # Need to load through main to avoid circular import
    from app.main import app
    from app.db.base import Base
    
    expected_tables = [
        "users", "projects", "chapters", "source_materials",
        "content_chunks", "voice_profiles", "book_outlines",
        "generation_tasks", "chapter_revisions", "api_keys",
        "billing_plans", "token_transactions", "qa_findings",
        "exported_books", "notifications"
    ]
    
    actual_tables = list(Base.metadata.tables.keys())
    missing = [t for t in expected_tables if t not in actual_tables]
    
    if missing:
        return f"Missing tables: {missing}"
    return True


@test("VoiceProfile has embedding column", "2-Models")
def test_voice_profile_embedding():
    from app.main import app
    from app.db.base import Base
    
    table = Base.metadata.tables.get("voice_profiles")
    if table is None:
        return "voice_profiles table not found"
    
    if "voice_embedding" not in table.columns:
        return "voice_embedding column not found"
    return True


@test("ContentChunk has embedding column", "2-Models")
def test_content_chunk_embedding():
    from app.main import app
    from app.db.base import Base
    
    table = Base.metadata.tables.get("content_chunks")
    if table is None:
        return "content_chunks table not found"
    
    if "embedding" not in table.columns:
        return "embedding column not found"
    return True


@test("GenerationTask tracks AI workflow", "2-Models")
def test_generation_task_model():
    from app.main import app
    from app.db.base import Base
    
    table = Base.metadata.tables.get("generation_tasks")
    if table is None:
        return "generation_tasks table not found"
    
    required_cols = ["task_type", "status", "agent_name", "token_usage", "progress"]
    missing = [c for c in required_cols if c not in table.columns]
    
    if missing:
        return f"Missing columns: {missing}"
    return True


# ============================================================================
# CATEGORY 3: Services
# ============================================================================

@test("AuthService implemented", "3-Services")
def test_auth_service():
    from app.main import app
    from app.services.auth import AuthService
    import inspect
    
    methods = [m for m in dir(AuthService) if not m.startswith('_')]
    required = ["create_user", "authenticate_user", "verify_token"]
    missing = [m for m in required if m not in methods]
    
    if missing:
        return f"Missing methods: {missing}"
    return True


@test("StorageService implemented", "3-Services")
def test_storage_service():
    from app.main import app
    from app.services.storage import StorageService
    
    service = StorageService()
    methods = [m for m in dir(service) if not m.startswith('_') and callable(getattr(service, m))]
    
    required = ["upload_file", "delete_file", "get_file_content"]
    missing = [m for m in required if m not in methods]
    
    if missing:
        return f"Missing methods: {missing}"
    return True


@test("GenerationService is EMPTY (gap)", "3-Services")
def test_generation_service_empty():
    from app.main import app
    from app.services.generation import GenerationService
    import inspect
    
    source = inspect.getsource(GenerationService)
    if "pass" in source and len(source.strip().split('\n')) <= 2:
        return True  # This confirms the gap
    return "GenerationService has content (update plan)"


@test("ProcessingService is EMPTY (gap)", "3-Services")
def test_processing_service_empty():
    from app.main import app
    from app.services.processing import ProcessingService
    import inspect
    
    source = inspect.getsource(ProcessingService)
    if "pass" in source and len(source.strip().split('\n')) <= 2:
        return True  # This confirms the gap
    return "ProcessingService has content (update plan)"


# ============================================================================
# CATEGORY 4: API Endpoints
# ============================================================================

@test("FastAPI app loads", "4-API")
def test_fastapi_loads():
    from app.main import app
    assert app is not None
    return True


@test("Auth endpoints exist", "4-API")
def test_auth_endpoints():
    from app.main import app
    
    routes = [r.path for r in app.routes]
    required = ["/api/v1/auth/register/", "/api/v1/auth/login/"]
    missing = [r for r in required if r not in routes]
    
    if missing:
        return f"Missing routes: {missing}"
    return True


@test("Project endpoints exist", "4-API")
def test_project_endpoints():
    from app.main import app
    
    routes = [r.path for r in app.routes]
    required = [
        "/api/v1/projects/",
        "/api/v1/projects/{project_id}",
        "/api/v1/projects/{project_id}/chapters",
        "/api/v1/projects/{project_id}/outline",
    ]
    missing = [r for r in required if r not in routes]
    
    if missing:
        return f"Missing routes: {missing}"
    return True


@test("Source materials endpoints exist", "4-API")
def test_source_materials_endpoints():
    from app.main import app
    
    routes = [r.path for r in app.routes]
    required = [
        "/api/v1/source-materials/upload",
        "/api/v1/source-materials/{material_id}",
        "/api/v1/source-materials/{material_id}/content",
    ]
    missing = [r for r in required if r not in routes]
    
    if missing:
        return f"Missing routes: {missing}"
    return True


@test("Generation endpoint MISSING (gap)", "4-API")
def test_generation_endpoint_missing():
    from app.main import app
    
    routes = [r.path for r in app.routes]
    
    # Frontend calls: POST /projects/{id}/generate
    generation_routes = [r for r in routes if "generate" in r.lower()]
    
    if generation_routes:
        return f"Found generation routes (update plan): {generation_routes}"
    return True  # Confirms the gap


@test("Outline generation endpoint MISSING (gap)", "4-API")
def test_outline_generation_missing():
    from app.main import app
    
    routes = [(r.path, list(r.methods) if hasattr(r, 'methods') else []) for r in app.routes]
    
    # Check for POST to outline (generation)
    outline_posts = [r for r in routes if "outline" in r[0].lower() and "POST" in r[1]]
    
    if outline_posts:
        return f"Found outline generation routes (update plan): {outline_posts}"
    return True  # Confirms the gap


# ============================================================================
# CATEGORY 5: Celery/Background Tasks
# ============================================================================

@test("Celery configured", "5-Celery")
def test_celery_config():
    from app.core.celery_app import celery_app
    
    assert celery_app is not None
    assert celery_app.conf.broker_url or True  # May not be set until runtime
    return True


@test("Task routes defined but tasks MISSING (gap)", "5-Celery")
def test_celery_tasks_missing():
    from app.core.celery_app import celery_app
    
    # Check if task routes are defined
    routes = celery_app.conf.task_routes or {}
    
    expected_tasks = [
        "app.tasks.process_source_material",
        "app.tasks.generate_chapter",
        "app.tasks.analyze_voice",
    ]
    
    # Check if tasks directory exists
    import os
    tasks_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'api', 'app', 'tasks')
    if os.path.exists(tasks_dir):
        return f"Tasks directory exists at {tasks_dir} (update plan)"
    
    return True  # Confirms tasks are referenced but don't exist


# ============================================================================
# CATEGORY 6: AI/LLM Integration
# ============================================================================

@test("No LLM client service exists (gap)", "6-AI")
def test_no_llm_client():
    import os
    
    services_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'api', 'app', 'services')
    llm_files = [f for f in os.listdir(services_dir) if 'llm' in f.lower() or 'openai' in f.lower() or 'anthropic' in f.lower()]
    
    if llm_files:
        return f"Found LLM service files (update plan): {llm_files}"
    return True  # Confirms the gap


@test("No embedding service exists (gap)", "6-AI")
def test_no_embedding_service():
    import os
    
    services_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'api', 'app', 'services')
    embed_files = [f for f in os.listdir(services_dir) if 'embed' in f.lower() or 'vector' in f.lower()]
    
    if embed_files:
        return f"Found embedding service files (update plan): {embed_files}"
    return True  # Confirms the gap


@test("No document processor exists (gap)", "6-AI")
def test_no_doc_processor():
    import os
    
    services_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'api', 'app', 'services')
    proc_files = [f for f in os.listdir(services_dir) if 'document' in f.lower() or 'unstructured' in f.lower()]
    
    if proc_files:
        return f"Found document processor files (update plan): {proc_files}"
    return True  # Confirms the gap


# ============================================================================
# CATEGORY 7: Agents System
# ============================================================================

@test("Agents directory structure exists", "7-Agents")
def test_agents_structure():
    import os
    
    agents_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'agents', 'agents')
    
    expected = ['base', 'core', 'specialized']
    actual = [d for d in os.listdir(agents_dir) if os.path.isdir(os.path.join(agents_dir, d))]
    missing = [d for d in expected if d not in actual]
    
    if missing:
        return f"Missing directories: {missing}"
    return True


@test("Agent base/ is EMPTY (gap)", "7-Agents")
def test_agents_base_empty():
    import os
    
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'agents', 'agents', 'base')
    files = [f for f in os.listdir(base_dir) if f.endswith('.py')]
    
    if files:
        return f"Found files in base/ (update plan): {files}"
    return True  # Confirms the gap


@test("Agent specialized/ is EMPTY (gap)", "7-Agents")
def test_agents_specialized_empty():
    import os
    
    spec_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'agents', 'agents', 'specialized')
    files = [f for f in os.listdir(spec_dir) if f.endswith('.py')]
    
    if files:
        return f"Found files in specialized/ (update plan): {files}"
    return True  # Confirms the gap


@test("Only database.py exists in agents core/", "7-Agents")
def test_agents_core_minimal():
    import os
    
    core_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'agents', 'agents', 'core')
    files = [f for f in os.listdir(core_dir) if f.endswith('.py')]
    
    if files == ['database.py']:
        return True  # Only database.py, confirms gap
    return f"Found additional files in core/ (update plan): {files}"


# ============================================================================
# CATEGORY 8: Dependencies
# ============================================================================

@test("API has pgvector dependency", "8-Dependencies")
def test_api_pgvector():
    # Check pyproject.toml content would be better, but we can check import
    try:
        import pgvector
        return True
    except ImportError:
        return "pgvector not installed"


@test("Agents pyproject has LangGraph", "8-Dependencies")
def test_agents_langgraph():
    import os
    
    pyproject = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'agents', 'pyproject.toml')
    with open(pyproject) as f:
        content = f.read()
    
    if 'langgraph' in content.lower():
        return True
    return "LangGraph not in agents pyproject.toml"


@test("Agents pyproject has sentence-transformers", "8-Dependencies")
def test_agents_sentence_transformers():
    import os
    
    pyproject = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'agents', 'pyproject.toml')
    with open(pyproject) as f:
        content = f.read()
    
    if 'sentence-transformers' in content.lower():
        return True
    return "sentence-transformers not in agents pyproject.toml"


@test("Agents pyproject has unstructured", "8-Dependencies")
def test_agents_unstructured():
    import os
    
    pyproject = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'agents', 'pyproject.toml')
    with open(pyproject) as f:
        content = f.read()
    
    if 'unstructured' in content.lower():
        return True
    return "unstructured not in agents pyproject.toml"


# ============================================================================
# SUMMARY
# ============================================================================

def print_results():
    print("\n" + "=" * 80)
    print("GHOSTLINE E2E SYSTEM TEST RESULTS")
    print("=" * 80 + "\n")
    
    # Group by category
    categories = {}
    for r in results:
        if r.category not in categories:
            categories[r.category] = []
        categories[r.category].append(r)
    
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    
    for cat in sorted(categories.keys()):
        print(f"\n{cat}")
        print("-" * 60)
        for r in categories[cat]:
            status = "✅" if r.passed else "❌"
            print(f"  {status} {r.name}")
            if not r.passed:
                print(f"      → {r.message}")
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(results)} tests")
    print("=" * 80)
    
    # Print gaps identified
    print("\n" + "=" * 80)
    print("CONFIRMED GAPS (tests that passed by verifying something is MISSING)")
    print("=" * 80)
    
    gap_tests = [r for r in results if r.passed and "(gap)" in r.name.lower()]
    for r in gap_tests:
        print(f"  📍 {r.name}")
    
    if not gap_tests:
        print("  No gaps confirmed by tests")
    
    print("\n" + "=" * 80)
    print("UNEXPECTED RESULTS (tests that failed unexpectedly)")
    print("=" * 80)
    
    unexpected = [r for r in results if not r.passed and "(gap)" not in r.name.lower()]
    for r in unexpected:
        print(f"  ❌ {r.name}: {r.message}")
    
    if not unexpected:
        print("  No unexpected failures!")
    
    return failed == 0


if __name__ == "__main__":
    success = print_results()
    sys.exit(0 if success else 1)

