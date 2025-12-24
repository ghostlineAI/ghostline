"""
Live E2E Tests for Phases 4 & 5

These tests require:
1. Docker running (PostgreSQL + Redis)
2. API keys set (ANTHROPIC_API_KEY or OPENAI_API_KEY)
3. Celery worker running (or we test synchronously)

Run with: pytest tests/test_live_e2e_phases_4_5.py -v -s
"""

import os
import sys
import time
import pytest
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add paths
API_PATH = Path(__file__).parent.parent / "ghostline" / "api"
AGENTS_PATH = Path(__file__).parent.parent / "ghostline" / "agents"
sys.path.insert(0, str(API_PATH))
sys.path.insert(0, str(AGENTS_PATH))


def has_api_keys():
    """Check if API keys are available."""
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def db_available():
    """Check if database is running."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", 5432),
            user=os.getenv("DB_USER", "ghostline"),
            password=os.getenv("DB_PASSWORD", "ghostline"),  # Default from docker-compose
            database=os.getenv("DB_NAME", "ghostline"),
        )
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"Database not available: {e}")
        return False


# ============================================================================
# PHASE 4 LIVE TESTS: Celery → LangGraph Integration
# ============================================================================

class TestPhase4LiveWorkflow:
    """Live tests for Phase 4: Workflow execution without Celery."""
    
    @pytest.mark.skipif(not has_api_keys(), reason="API keys required")
    def test_workflow_start_with_real_agents(self):
        """Test BookGenerationWorkflow.start() with real agents."""
        logger.info("=" * 60)
        logger.info("TEST: Workflow start with real agents")
        logger.info("=" * 60)
        
        from orchestrator.workflow import BookGenerationWorkflow
        
        workflow = BookGenerationWorkflow()
        
        start_time = time.time()
        result = workflow.start(
            project_id="test-project-001",
            user_id="test-user-001",
            source_material_ids=["source-1"],
        )
        elapsed = time.time() - start_time
        
        logger.info(f"Workflow started in {elapsed:.2f}s")
        logger.info(f"Workflow ID: {result['workflow_id']}")
        logger.info(f"Phase: {result['state'].get('phase')}")
        logger.info(f"Progress: {result['state'].get('progress')}%")
        logger.info(f"Pending action: {result['state'].get('pending_user_action')}")
        
        assert result["workflow_id"] is not None
        assert result["state"]["phase"] == "outline_review"
        assert result["state"]["pending_user_action"] == "approve_outline"
        assert result["state"]["outline"] is not None
        
        logger.info("✅ Workflow paused at outline review as expected")
    
    @pytest.mark.skipif(not has_api_keys(), reason="API keys required")  
    def test_workflow_resume_after_approval(self):
        """Test workflow resumes and completes after outline approval."""
        logger.info("=" * 60)
        logger.info("TEST: Workflow resume after approval")
        logger.info("=" * 60)
        
        from orchestrator.workflow import BookGenerationWorkflow
        
        workflow = BookGenerationWorkflow()
        
        # Start workflow
        logger.info("Starting workflow...")
        result = workflow.start(
            project_id="test-project-002",
            user_id="test-user-001",
            source_material_ids=["source-1"],
        )
        workflow_id = result["workflow_id"]
        logger.info(f"Workflow {workflow_id} paused at: {result['state']['phase']}")
        
        # Modify outline to have just 1 chapter (to avoid long test)
        config = {"configurable": {"thread_id": workflow_id}}
        state = workflow.graph.get_state(config)
        state_values = dict(state.values)
        state_values["outline"] = {
            "title": "Quick Test Book",
            "chapters": [{"number": 1, "title": "Chapter 1", "summary": "Test chapter"}]
        }
        workflow.graph.update_state(config, state_values)
        logger.info("Updated outline to 1 chapter for fast test")
        
        # Approve and resume
        logger.info("Approving outline and resuming...")
        start_time = time.time()
        result = workflow.resume(
            workflow_id=workflow_id,
            user_input={"approve_outline": True},
        )
        elapsed = time.time() - start_time
        
        logger.info(f"Resumed in {elapsed:.2f}s")
        logger.info(f"Final phase: {result['state'].get('phase')}")
        logger.info(f"Progress: {result['state'].get('progress')}%")
        logger.info(f"Chapters processed: {result['state'].get('current_chapter')}")
        
        # Should have completed
        assert result["state"]["outline_approved"] == True
        assert result["state"]["phase"] in ["completed", "finalizing"]
        
        logger.info("✅ Workflow completed after approval")
    
    @pytest.mark.skipif(not has_api_keys(), reason="API keys required")
    def test_outline_subgraph_live(self):
        """Test OutlineSubgraph with real Planner↔Critic conversation."""
        logger.info("=" * 60)
        logger.info("TEST: OutlineSubgraph live with Planner↔Critic")
        logger.info("=" * 60)
        
        from orchestrator.subgraphs import OutlineSubgraph, SubgraphConfig
        
        # Limit iterations and cost
        config = SubgraphConfig(max_turns=2, max_cost=0.20)
        subgraph = OutlineSubgraph(config=config)
        
        start_time = time.time()
        result = subgraph.run(
            source_summaries=[
                "This book is about machine learning fundamentals.",
                "Topics include neural networks, training, and deployment."
            ],
            project_title="ML Fundamentals",
            project_description="A beginner's guide to machine learning",
            target_chapters=3,
        )
        elapsed = time.time() - start_time
        
        logger.info(f"Outline generated in {elapsed:.2f}s")
        logger.info(f"Iterations: {result['iterations']}")
        logger.info(f"Tokens used: {result['tokens_used']}")
        logger.info(f"Cost: ${result['cost']:.4f}")
        logger.info(f"Chapters: {len(result['outline'].get('chapters', []))}")
        logger.info(f"Approved: {result['approved']}")
        
        assert result["outline"] is not None
        assert len(result["outline"].get("chapters", [])) >= 1
        assert result["tokens_used"] > 0
        
        logger.info("✅ OutlineSubgraph completed with real agents")
    
    @pytest.mark.skipif(not has_api_keys(), reason="API keys required")
    def test_chapter_subgraph_live(self):
        """Test ChapterSubgraph with real Drafter→Voice→Fact→Cohesion chain."""
        logger.info("=" * 60)
        logger.info("TEST: ChapterSubgraph live with full agent chain")
        logger.info("=" * 60)
        
        from orchestrator.subgraphs import ChapterSubgraph, SubgraphConfig
        
        # Limit iterations
        config = SubgraphConfig(max_turns=2, max_cost=0.30)
        subgraph = ChapterSubgraph(config=config)
        
        start_time = time.time()
        result = subgraph.run(
            chapter_outline={
                "number": 1,
                "title": "Introduction to Neural Networks",
                "summary": "This chapter introduces the basic concepts of neural networks.",
                "key_points": [
                    "What is a neuron",
                    "How neurons connect",
                    "Activation functions"
                ],
            },
            source_chunks=[
                "A neural network is a computational model inspired by biological neurons.",
                "Neurons are connected by weights that are learned during training."
            ],
            target_words=500,  # Short chapter for testing
        )
        elapsed = time.time() - start_time
        
        logger.info(f"Chapter generated in {elapsed:.2f}s")
        logger.info(f"Word count: {result['word_count']}")
        logger.info(f"Voice score: {result['voice_score']:.2f}")
        logger.info(f"Fact score: {result['fact_score']:.2f}")
        logger.info(f"Cohesion score: {result['cohesion_score']:.2f}")
        logger.info(f"Iterations: {result['iterations']}")
        logger.info(f"Tokens used: {result['tokens_used']}")
        logger.info(f"Cost: ${result['cost']:.4f}")
        
        assert result["content"] is not None
        assert len(result["content"]) > 100
        
        logger.info("✅ ChapterSubgraph completed with real agents")


# ============================================================================
# PHASE 5 LIVE TESTS: User Feedback Loop
# ============================================================================

class TestPhase5LiveFeedback:
    """Live tests for Phase 5: Feedback and resume functionality."""
    
    @pytest.mark.skipif(not has_api_keys(), reason="API keys required")
    def test_workflow_pause_state_persists(self):
        """Test that paused workflow state can be retrieved."""
        logger.info("=" * 60)
        logger.info("TEST: Workflow pause state persistence")
        logger.info("=" * 60)
        
        from orchestrator.workflow import BookGenerationWorkflow
        
        workflow = BookGenerationWorkflow()
        
        # Start
        result = workflow.start(
            project_id="test-persist-001",
            user_id="test-user-001",
            source_material_ids=["source-1"],
        )
        workflow_id = result["workflow_id"]
        original_outline = result["state"].get("outline")
        
        logger.info(f"Started workflow: {workflow_id}")
        
        # Retrieve state
        retrieved_state = workflow.get_state(workflow_id)
        
        logger.info(f"Retrieved phase: {retrieved_state.get('phase')}")
        logger.info(f"Retrieved outline chapters: {len(retrieved_state.get('outline', {}).get('chapters', []))}")
        
        assert retrieved_state["workflow_id"] == workflow_id
        assert retrieved_state["phase"] == "outline_review"
        assert retrieved_state.get("outline") == original_outline
        
        logger.info("✅ Paused state correctly retrieved")
    
    @pytest.mark.skipif(not has_api_keys(), reason="API keys required")
    def test_feedback_applied_to_workflow(self):
        """Test that user feedback is applied to workflow state."""
        logger.info("=" * 60)
        logger.info("TEST: Feedback applied to workflow")
        logger.info("=" * 60)
        
        from orchestrator.workflow import BookGenerationWorkflow
        
        workflow = BookGenerationWorkflow()
        
        # Start
        result = workflow.start(
            project_id="test-feedback-001",
            user_id="test-user-001",
            source_material_ids=["source-1"],
        )
        workflow_id = result["workflow_id"]
        
        # Update state with minimal outline first
        config = {"configurable": {"thread_id": workflow_id}}
        state = workflow.graph.get_state(config)
        state_values = dict(state.values)
        state_values["outline"] = {"title": "Test", "chapters": [{"number": 1, "title": "Ch1"}]}
        workflow.graph.update_state(config, state_values)
        
        # Resume with feedback
        result = workflow.resume(
            workflow_id=workflow_id,
            user_input={
                "approve_outline": True,
                "feedback": {"text": "Please make it more engaging", "target": "outline"}
            },
        )
        
        # Check feedback was recorded
        state = workflow.get_state(workflow_id)
        
        logger.info(f"Feedback recorded: {state.get('user_feedback')}")
        logger.info(f"Outline approved: {state.get('outline_approved')}")
        
        assert state.get("outline_approved") == True
        assert len(state.get("user_feedback", [])) > 0
        
        logger.info("✅ Feedback correctly applied")


# ============================================================================
# INTEGRATION TESTS: Full Pipeline
# ============================================================================

@pytest.mark.skip(reason="Requires DB migrations to be up-to-date - run alembic upgrade head first")
class TestFullPipelineIntegration:
    """Full pipeline integration tests requiring DB and API keys."""
    
    def test_api_to_workflow_integration(self):
        """Test the full API → WorkflowService → LangGraph flow."""
        logger.info("=" * 60)
        logger.info("TEST: API to Workflow Integration (requires DB)")
        logger.info("=" * 60)
        
        from app.db.base import SessionLocal
        from app.services.workflow_service import WorkflowService
        from app.models.project import Project
        from app.models.generation_task import GenerationTask, TaskStatus, TaskType
        from app.models.user import User
        import uuid
        
        db = SessionLocal()
        created_user = None
        created_project = None
        
        try:
            # Get or create a test user
            user = db.query(User).first()
            if not user:
                logger.info("Creating test user...")
                from passlib.context import CryptContext
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                user = User(
                    id=uuid.uuid4(),
                    email="test@ghostline.ai",
                    username="testuser",
                    hashed_password=pwd_context.hash("testpassword123"),
                    full_name="Test User",
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                created_user = user
                logger.info(f"Created test user: {user.email}")
            
            # Get or create a test project
            project = db.query(Project).filter(Project.owner_id == user.id).first()
            if not project:
                logger.info("Creating test project...")
                project = Project(
                    id=uuid.uuid4(),
                    name="Test Book Project",
                    description="A test project for E2E testing",
                    owner_id=user.id,
                )
                db.add(project)
                db.commit()
                db.refresh(project)
                created_project = project
                logger.info(f"Created test project: {project.name}")
            
            logger.info(f"Using project: {project.name} (ID: {project.id})")
            
            # Create a generation task
            task = GenerationTask(
                id=uuid.uuid4(),
                project_id=project.id,
                task_type=TaskType.OUTLINE_GENERATION,
                status=TaskStatus.PENDING,
                agent_name="test_orchestrator",
                progress=0,
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            
            logger.info(f"Created task: {task.id}")
            
            # Initialize workflow service
            workflow_service = WorkflowService(db)
            
            # Test outline generation
            start_time = time.time()
            result = workflow_service.generate_outline(task=task, project=project)
            elapsed = time.time() - start_time
            
            logger.info(f"Outline generated in {elapsed:.2f}s")
            logger.info(f"Task status: {task.status.value}")
            logger.info(f"Task progress: {task.progress}%")
            logger.info(f"Tokens used: {task.token_usage}")
            logger.info(f"Cost: ${task.estimated_cost:.4f}")
            
            # Verify task was updated
            assert task.status == TaskStatus.COMPLETED
            assert task.progress == 100
            assert task.output_data is not None
            assert "outline" in task.output_data
            
            logger.info("✅ Full API to Workflow integration successful")
            
        finally:
            # Cleanup
            if 'task' in locals():
                db.delete(task)
            if created_project:
                db.delete(created_project)
            if created_user:
                db.delete(created_user)
            db.commit()
            db.close()


# ============================================================================
# SUMMARY REPORT
# ============================================================================

def test_summary_report():
    """Print a summary of what can be tested."""
    logger.info("=" * 60)
    logger.info("E2E TEST CAPABILITY SUMMARY")
    logger.info("=" * 60)
    
    api_keys = has_api_keys()
    db = db_available()
    
    logger.info(f"API Keys available: {'✅' if api_keys else '❌'}")
    logger.info(f"Database available: {'✅' if db else '❌'}")
    
    if api_keys:
        logger.info("\nCan run:")
        logger.info("  - Workflow start/resume tests")
        logger.info("  - OutlineSubgraph live tests")
        logger.info("  - ChapterSubgraph live tests")
        logger.info("  - Feedback/approval tests")
    
    if api_keys and db:
        logger.info("  - Full API integration tests")
        logger.info("  - WorkflowService with real DB")
    
    if not api_keys:
        logger.info("\n⚠️  Set ANTHROPIC_API_KEY or OPENAI_API_KEY for live agent tests")
    
    if not db:
        logger.info("\n⚠️  Start Docker (PostgreSQL) for full integration tests")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

