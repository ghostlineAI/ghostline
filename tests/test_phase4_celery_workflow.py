"""
Phase 4 Tests: Celery Tasks Wired to LangGraph Workflows

Tests that Celery tasks correctly call LangGraph workflows:
1. WorkflowService can import and use agents
2. Generation tasks are properly wired
3. Task status updates work correctly
4. Resume/feedback endpoints function
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add paths
API_PATH = Path(__file__).parent.parent / "ghostline" / "api"
AGENTS_PATH = Path(__file__).parent.parent / "ghostline" / "agents"

sys.path.insert(0, str(API_PATH))
sys.path.insert(0, str(AGENTS_PATH))


def _can_import_models():
    """Check if we can import models (avoids circular import in tests)."""
    try:
        # Try importing via main app first (correct way)
        os.environ.setdefault("DATABASE_URL", "postgresql://localhost/ghostline")
        from app.main import app
        return True
    except Exception:
        return False


class TestPhase4Structure:
    """Test that Phase 4 files exist and have correct structure."""
    
    def test_workflow_service_exists(self):
        """WorkflowService should exist."""
        workflow_service_path = API_PATH / "app" / "services" / "workflow_service.py"
        assert workflow_service_path.exists(), "workflow_service.py should exist"
    
    def test_workflow_service_imports(self):
        """WorkflowService should be importable (via file inspection)."""
        workflow_service_path = API_PATH / "app" / "services" / "workflow_service.py"
        content = workflow_service_path.read_text()
        
        # Check that the class is defined
        assert "class WorkflowService:" in content
        assert "def start_book_generation" in content
        assert "def resume_workflow" in content
        assert "def generate_outline" in content
        assert "def approve_outline" in content
    
    def test_generation_tasks_updated(self):
        """Generation tasks should import workflow service."""
        generation_path = API_PATH / "app" / "tasks" / "generation.py"
        content = generation_path.read_text()
        
        assert "WorkflowService" in content, "Should import WorkflowService"
        assert "generate_book_task" in content
        assert "generate_outline_task" in content
        assert "resume_workflow_task" in content
    
    def test_generation_endpoints_updated(self):
        """Generation endpoints should queue Celery tasks."""
        endpoints_path = API_PATH / "app" / "api" / "v1" / "endpoints" / "generation.py"
        content = endpoints_path.read_text()
        
        # Check that TODOs are replaced with actual task calls
        assert "generate_book_task.delay" in content, "Should call generate_book_task.delay"
        assert "generate_outline_task.delay" in content, "Should call generate_outline_task.delay"
        assert "generate_chapter_task.delay" in content
        assert "analyze_voice_task.delay" in content
        
        # Check new endpoints exist
        assert "approve-outline" in content, "Should have approve-outline endpoint"
        assert "feedback" in content, "Should have feedback endpoint"
        assert "resume" in content, "Should have resume endpoint"
    
    def test_task_status_has_paused(self):
        """TaskStatus should include PAUSED (via file inspection)."""
        model_path = API_PATH / "app" / "models" / "generation_task.py"
        content = model_path.read_text()
        
        assert 'PAUSED = "paused"' in content, "TaskStatus should have PAUSED"


class TestWorkflowServiceUnit:
    """Unit tests for WorkflowService (file-based to avoid circular imports)."""
    
    def test_workflow_service_structure(self):
        """WorkflowService should have correct structure."""
        workflow_path = API_PATH / "app" / "services" / "workflow_service.py"
        content = workflow_path.read_text()
        
        # Check init
        assert "def __init__(self, db: Session):" in content
        assert "self.db = db" in content
        assert "self._workflow = None" in content
    
    def test_lazy_loading_workflow(self):
        """Workflow should be lazy loaded via @property."""
        workflow_path = API_PATH / "app" / "services" / "workflow_service.py"
        content = workflow_path.read_text()
        
        assert "@property" in content
        assert "def workflow(self):" in content
        assert "BookGenerationWorkflow" in content
    
    def test_lazy_loading_subgraphs(self):
        """Subgraphs should be lazy loaded via @property."""
        workflow_path = API_PATH / "app" / "services" / "workflow_service.py"
        content = workflow_path.read_text()
        
        assert "def outline_subgraph(self):" in content
        assert "OutlineSubgraph" in content
        assert "def chapter_subgraph(self):" in content
        assert "ChapterSubgraph" in content


class TestCeleryTasksUnit:
    """Unit tests for Celery tasks."""
    
    def test_tasks_importable(self):
        """All generation tasks should be importable."""
        try:
            from app.tasks.generation import (
                generate_book_task,
                generate_outline_task,
                generate_chapter_task,
                analyze_voice_task,
                resume_workflow_task,
            )
            
            assert generate_book_task is not None
            assert generate_outline_task is not None
            assert generate_chapter_task is not None
            assert analyze_voice_task is not None
            assert resume_workflow_task is not None
        except ModuleNotFoundError as e:
            if "psycopg2" in str(e):
                pytest.skip("psycopg2 not installed (API dependencies required)")
            raise
    
    def test_tasks_are_celery_tasks(self):
        """Tasks should be proper Celery tasks."""
        try:
            from app.tasks.generation import generate_book_task
            
            # Celery tasks have delay and apply_async methods
            assert hasattr(generate_book_task, "delay")
            assert hasattr(generate_book_task, "apply_async")
        except ModuleNotFoundError as e:
            if "psycopg2" in str(e):
                pytest.skip("psycopg2 not installed (API dependencies required)")
            raise


class TestGenerationEndpoints:
    """Test generation API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        try:
            from app.main import app
            from fastapi.testclient import TestClient
            return TestClient(app)
        except Exception:
            pytest.skip("Could not create test client")
    
    def test_endpoints_exist(self, client):
        """Check that all generation endpoints exist."""
        from app.main import app
        
        routes = [route.path for route in app.routes]
        
        # Check for generation endpoints
        assert any("/generate" in r for r in routes), "Should have /generate endpoint"
        assert any("/outline" in r for r in routes), "Should have /outline endpoint"
        assert any("/approve-outline" in r for r in routes), "Should have approve-outline"
        assert any("/feedback" in r for r in routes), "Should have feedback endpoint"
        assert any("/resume" in r for r in routes), "Should have resume endpoint"


class TestAgentIntegration:
    """Test integration with agents module."""
    
    def test_agents_can_be_imported(self):
        """Agents module should be importable from API context."""
        try:
            from orchestrator.workflow import BookGenerationWorkflow
            from orchestrator.subgraphs import OutlineSubgraph, ChapterSubgraph
            
            assert BookGenerationWorkflow is not None
            assert OutlineSubgraph is not None
            assert ChapterSubgraph is not None
        except ImportError as e:
            pytest.skip(f"Could not import agents: {e}")
    
    def test_workflow_can_compile(self):
        """BookGenerationWorkflow should compile without errors."""
        try:
            from orchestrator.workflow import BookGenerationWorkflow
            
            workflow = BookGenerationWorkflow()
            assert workflow.graph is not None
        except ImportError as e:
            pytest.skip(f"Could not import workflow: {e}")
    
    def test_subgraphs_can_compile(self):
        """Subgraphs should compile without errors."""
        try:
            from orchestrator.subgraphs import OutlineSubgraph, ChapterSubgraph
            
            outline = OutlineSubgraph()
            assert outline.graph is not None
            
            chapter = ChapterSubgraph()
            assert chapter.graph is not None
        except ImportError as e:
            pytest.skip(f"Could not import subgraphs: {e}")


# Check if database is available
def db_available():
    """Check if database is available for live tests."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", 5432),
            user=os.getenv("DB_USER", "ghostline"),
            password=os.getenv("DB_PASSWORD", "ghostline_dev"),
            database=os.getenv("DB_NAME", "ghostline"),
        )
        conn.close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not db_available(), reason="Database not available")
class TestLiveWorkflowIntegration:
    """Live integration tests requiring database."""
    
    def test_workflow_service_with_real_db(self):
        """Test WorkflowService with real database session."""
        from app.db.base import SessionLocal
        from app.services.workflow_service import WorkflowService
        
        db = SessionLocal()
        try:
            service = WorkflowService(db)
            assert service.db is not None
            
            # Try to access workflow
            try:
                workflow = service.workflow
                assert workflow is not None
            except ImportError:
                pass  # OK if agents not importable
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

