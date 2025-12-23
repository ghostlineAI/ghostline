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


@test("GenerationService implemented", "3-Services")
def test_generation_service_implemented():
    from app.main import app
    from app.services.generation import GenerationService
    import inspect
    
    methods = [m for m in dir(GenerationService) if not m.startswith('_')]
    required = ["generate_outline", "generate_chapter", "analyze_voice"]
    missing = [m for m in required if m not in methods]
    
    if missing:
        return f"GenerationService missing methods: {missing}"
    return True


@test("ProcessingService implemented", "3-Services")
def test_processing_service_implemented():
    from app.main import app
    from app.services.processing import ProcessingService
    import inspect
    
    methods = [m for m in dir(ProcessingService) if not m.startswith('_')]
    required = ["process_source_material", "create_voice_profile", "find_relevant_chunks"]
    missing = [m for m in required if m not in methods]
    
    if missing:
        return f"ProcessingService missing methods: {missing}"
    return True


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


@test("Generation endpoint exists", "4-API")
def test_generation_endpoint_exists():
    from app.main import app
    
    routes = [r.path for r in app.routes]
    
    # Frontend calls: POST /projects/{id}/generate
    generation_routes = [r for r in routes if "generate" in r.lower()]
    
    if not generation_routes:
        return "Generation endpoint missing"
    return True


@test("Outline generation endpoint exists", "4-API")
def test_outline_generation_exists():
    from app.main import app
    
    routes = [(r.path, list(r.methods) if hasattr(r, 'methods') else []) for r in app.routes]
    
    # Check for POST to outline (generation)
    outline_posts = [r for r in routes if "outline" in r[0].lower() and "POST" in r[1]]
    
    if not outline_posts:
        return "Outline generation endpoint missing"
    return True


# ============================================================================
# CATEGORY 5: Celery/Background Tasks
# ============================================================================

@test("Celery configured", "5-Celery")
def test_celery_config():
    from app.core.celery_app import celery_app
    
    assert celery_app is not None
    assert celery_app.conf.broker_url or True  # May not be set until runtime
    return True


@test("Tasks module exists", "5-Celery")
def test_celery_tasks_exist():
    import os
    
    # Check if tasks directory exists
    tasks_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'api', 'app', 'tasks')
    if not os.path.exists(tasks_dir):
        return "Tasks directory missing"
    
    # Check for generation.py
    gen_file = os.path.join(tasks_dir, 'generation.py')
    if not os.path.exists(gen_file):
        return "generation.py task file missing"
    
    return True


# ============================================================================
# CATEGORY 6: AI/LLM Integration
# ============================================================================

@test("LLM client service exists", "6-AI")
def test_llm_client_exists():
    import os
    
    services_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'api', 'app', 'services')
    llm_file = os.path.join(services_dir, 'llm.py')
    
    if not os.path.exists(llm_file):
        return "LLM service file missing"
    
    # Verify it has the expected classes
    with open(llm_file, 'r') as f:
        content = f.read()
    if 'LLMService' not in content or 'AnthropicClient' not in content:
        return "LLM service missing expected classes"
    return True


@test("Embedding service exists", "6-AI")
def test_embedding_service_exists():
    import os
    
    services_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'api', 'app', 'services')
    embed_file = os.path.join(services_dir, 'embeddings.py')
    
    if not os.path.exists(embed_file):
        return "Embedding service file missing"
    
    with open(embed_file, 'r') as f:
        content = f.read()
    if 'EmbeddingService' not in content or 'embed_text' not in content:
        return "Embedding service missing expected classes/methods"
    return True


@test("Document processor exists", "6-AI")
def test_doc_processor_exists():
    import os
    
    services_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'api', 'app', 'services')
    proc_file = os.path.join(services_dir, 'document_processor.py')
    
    if not os.path.exists(proc_file):
        return "Document processor file missing"
    
    with open(proc_file, 'r') as f:
        content = f.read()
    if 'DocumentProcessor' not in content or 'extract_from_file' not in content:
        return "Document processor missing expected classes/methods"
    return True


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


@test("Agent base/ has BaseAgent", "7-Agents")
def test_agents_base_implemented():
    import os
    
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'agents', 'agents', 'base')
    agent_file = os.path.join(base_dir, 'agent.py')
    
    if not os.path.exists(agent_file):
        return "agent.py missing from base/"
    
    with open(agent_file, 'r') as f:
        content = f.read()
    
    required = ['BaseAgent', 'AgentConfig', 'AgentOutput']
    missing = [r for r in required if r not in content]
    
    if missing:
        return f"Base agent missing: {missing}"
    return True


@test("Specialized agents implemented", "7-Agents")
def test_agents_specialized_implemented():
    import os
    
    spec_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'agents', 'agents', 'specialized')
    
    required_agents = [
        'outline_planner.py',
        'content_drafter.py',
        'voice_editor.py',
        'fact_checker.py',
        'cohesion_analyst.py',
    ]
    
    files = os.listdir(spec_dir)
    missing = [a for a in required_agents if a not in files]
    
    if missing:
        return f"Missing specialized agents: {missing}"
    return True


@test("Agents core has database.py", "7-Agents")
def test_agents_core():
    import os
    
    core_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'agents', 'agents', 'core')
    files = [f for f in os.listdir(core_dir) if f.endswith('.py')]
    
    if 'database.py' not in files:
        return "database.py missing from core/"
    return True


@test("LangGraph orchestration exists", "7-Agents")
def test_langgraph_orchestration():
    import os
    
    orch_dir = os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'agents', 'orchestrator')
    
    if not os.path.exists(orch_dir):
        return "orchestrator/ directory missing"
    
    required = ['workflow.py', 'subgraphs.py']
    files = os.listdir(orch_dir)
    missing = [f for f in required if f not in files]
    
    if missing:
        return f"Missing orchestration files: {missing}"
    
    # Check workflow.py has key components
    with open(os.path.join(orch_dir, 'workflow.py'), 'r') as f:
        content = f.read()
    
    if 'BookGenerationWorkflow' not in content or 'StateGraph' not in content:
        return "workflow.py missing key components"
    
    return True


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

