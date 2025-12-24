"""
Phase 0 Tests: Generation Endpoints

These tests verify the generation endpoints are properly wired
and respond correctly. Uses FastAPI TestClient for live testing.
"""

import pytest
import sys
import os

# Add the API app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'api'))

from fastapi.testclient import TestClient


class TestPhase0Endpoints:
    """Test generation endpoint wiring and responses."""
    
    def test_app_loads(self):
        """Verify FastAPI app loads without errors."""
        from app.main import app
        assert app is not None
        assert app.title is not None
    
    def test_routes_registered(self):
        """Verify generation routes are registered."""
        from app.main import app
        
        routes = [r.path for r in app.routes]
        
        # Check generation endpoints exist
        assert "/api/v1/projects/{project_id}/generate" in routes
        assert "/api/v1/projects/{project_id}/outline" in routes
        assert "/api/v1/projects/{project_id}/tasks" in routes
        assert "/api/v1/projects/tasks/{task_id}" in routes
    
    def test_generation_router_imported(self):
        """Verify generation router is in the API router."""
        from app.api.v1.router import api_router
        
        # Check generation router is included
        route_paths = [r.path for r in api_router.routes]
        assert any("generate" in p for p in route_paths)
        assert any("tasks" in p for p in route_paths)
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires running database
        reason="Requires running database"
    )
    def test_endpoint_responses_with_db(self):
        """Test actual endpoint responses (requires DB)."""
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/health")
        assert response.status_code == 200


class TestPhase0CeleryTasks:
    """Test Celery task module loads correctly."""
    
    def test_celery_app_loads(self):
        """Celery app should load without errors."""
        from app.core.celery_app import celery_app
        assert celery_app is not None
    
    def test_generation_tasks_import(self):
        """Generation tasks should import without errors."""
        from app.tasks.generation import (
            generate_book_task,
            generate_outline_task,
            generate_chapter_task,
            analyze_voice_task,
        )
        assert callable(generate_book_task)
        assert callable(generate_outline_task)
        assert callable(generate_chapter_task)
        assert callable(analyze_voice_task)
    
    def test_task_names_registered(self):
        """Tasks should have proper Celery names."""
        from app.tasks.generation import generate_book_task
        assert generate_book_task.name == "app.tasks.generate_book"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

