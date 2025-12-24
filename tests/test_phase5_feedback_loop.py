"""
Phase 5 Tests: User Feedback Loop (Pause/Resume)

Tests the user feedback and approval workflow:
1. Workflow pauses at outline approval
2. Approval endpoint resumes workflow
3. Feedback can be provided
4. Subgraphs use real agents when API keys are available
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


def has_api_keys():
    """Check if API keys are available."""
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))


class TestPhase5Structure:
    """Test that Phase 5 files exist and have correct structure."""
    
    def test_subgraphs_use_real_agents(self):
        """Subgraphs should have agent loading logic."""
        subgraph_path = AGENTS_PATH / "orchestrator" / "subgraphs.py"
        content = subgraph_path.read_text()
        
        # Check for lazy loading
        assert "@property" in content
        assert "def planner(self):" in content
        assert "def critic(self):" in content
        assert "def drafter(self):" in content
        assert "def voice_editor(self):" in content
        assert "def fact_checker(self):" in content
        assert "def cohesion_analyst(self):" in content
    
    def test_subgraphs_import_agents(self):
        """Subgraphs should import specialized agents."""
        subgraph_path = AGENTS_PATH / "orchestrator" / "subgraphs.py"
        content = subgraph_path.read_text()
        
        assert "from agents.specialized.outline_planner import OutlinePlannerAgent" in content
        assert "from agents.specialized.outline_planner import OutlineCriticAgent" in content
        assert "from agents.specialized.content_drafter import ContentDrafterAgent" in content
        assert "from agents.specialized.voice_editor import VoiceEditorAgent" in content
        assert "from agents.specialized.fact_checker import FactCheckerAgent" in content
        assert "from agents.specialized.cohesion_analyst import CohesionAnalystAgent" in content
    
    def test_api_endpoints_exist(self):
        """Feedback endpoints should exist."""
        endpoints_path = API_PATH / "app" / "api" / "v1" / "endpoints" / "generation.py"
        content = endpoints_path.read_text()
        
        assert "approve-outline" in content
        assert "OutlineApprovalRequest" in content
        assert "FeedbackRequest" in content
        assert "/feedback" in content
        assert "/resume" in content


class TestWorkflowPauseResume:
    """Test workflow pause and resume functionality."""
    
    def test_workflow_pauses_at_outline_review(self):
        """Workflow should pause and wait for outline approval."""
        try:
            from orchestrator.workflow import BookGenerationWorkflow
            
            workflow = BookGenerationWorkflow()
            result = workflow.start(
                project_id="test-123",
                user_id="user-456",
                source_material_ids=["source-1"],
            )
            
            state = result["state"]
            assert state.get("phase") == "outline_review", "Should pause at outline_review"
            assert state.get("pending_user_action") == "approve_outline"
            assert state.get("progress") == 30
        except ImportError as e:
            pytest.skip(f"Could not import workflow: {e}")
    
    def test_workflow_resumes_on_approval(self):
        """Workflow should continue when outline is approved."""
        try:
            from orchestrator.workflow import BookGenerationWorkflow, WorkflowState, create_initial_state
            
            workflow = BookGenerationWorkflow()
            
            # Start workflow
            result = workflow.start(
                project_id="test-123",
                user_id="user-456",
                source_material_ids=["source-1"],
            )
            workflow_id = result["workflow_id"]
            
            # Before resuming, update the outline to have fewer chapters (to avoid recursion limit)
            config = {"configurable": {"thread_id": workflow_id}}
            state = workflow.graph.get_state(config)
            state_values = dict(state.values)
            state_values["outline"] = {
                "title": "Test Book",
                "chapters": [
                    {"number": 1, "title": "Chapter 1", "summary": "Test"}
                ]
            }
            workflow.graph.update_state(config, state_values)
            
            # Approve outline
            result = workflow.resume(
                workflow_id=workflow_id,
                user_input={"approve_outline": True},
            )
            
            state = result["state"]
            assert state.get("outline_approved") == True
            # Should have moved past outline_review (or completed)
            assert state.get("phase") in ["drafting", "editing", "reviewing", "finalizing", "completed"]
        except ImportError as e:
            pytest.skip(f"Could not import workflow: {e}")
    
    def test_workflow_state_persistence(self):
        """Workflow state should be retrievable."""
        try:
            from orchestrator.workflow import BookGenerationWorkflow
            
            workflow = BookGenerationWorkflow()
            
            # Start workflow
            result = workflow.start(
                project_id="test-123",
                user_id="user-456",
                source_material_ids=["source-1"],
            )
            workflow_id = result["workflow_id"]
            
            # Get state
            state = workflow.get_state(workflow_id)
            
            assert state.get("workflow_id") == workflow_id
            assert state.get("project_id") == "test-123"
        except ImportError as e:
            pytest.skip(f"Could not import workflow: {e}")


class TestOutlineSubgraph:
    """Test outline generation subgraph."""
    
    def test_outline_subgraph_runs(self):
        """OutlineSubgraph should run without errors."""
        try:
            from orchestrator.subgraphs import OutlineSubgraph
            
            subgraph = OutlineSubgraph()
            result = subgraph.run(
                source_summaries=["This is a book about technology."],
                project_title="My Test Book",
                project_description="A test book for testing",
                target_chapters=5,
            )
            
            assert "outline" in result
            assert "iterations" in result
            assert result["outline"] is not None
            assert "chapters" in result["outline"]
        except ImportError as e:
            pytest.skip(f"Could not import subgraph: {e}")
    
    def test_outline_subgraph_bounded(self):
        """OutlineSubgraph should respect bounds."""
        try:
            from orchestrator.subgraphs import OutlineSubgraph, SubgraphConfig
            
            config = SubgraphConfig(max_turns=2)
            subgraph = OutlineSubgraph(config=config)
            
            result = subgraph.run(
                source_summaries=["Test source"],
                project_title="Bounded Test",
            )
            
            # Should complete within bounds
            assert result["iterations"] <= 2
        except ImportError as e:
            pytest.skip(f"Could not import subgraph: {e}")


class TestChapterSubgraph:
    """Test chapter generation subgraph."""
    
    def test_chapter_subgraph_runs(self):
        """ChapterSubgraph should run without errors."""
        try:
            from orchestrator.subgraphs import ChapterSubgraph
            
            subgraph = ChapterSubgraph()
            result = subgraph.run(
                chapter_outline={
                    "number": 1,
                    "title": "Introduction",
                    "summary": "This chapter introduces the topic.",
                    "key_points": ["Point 1", "Point 2"],
                },
                source_chunks=["Relevant source material here."],
                target_words=1000,
            )
            
            assert "content" in result
            assert "voice_score" in result
            assert "fact_score" in result
            assert "cohesion_score" in result
            assert result["content"] is not None
        except ImportError as e:
            pytest.skip(f"Could not import subgraph: {e}")
    
    def test_chapter_subgraph_quality_scores(self):
        """ChapterSubgraph should produce quality scores."""
        try:
            from orchestrator.subgraphs import ChapterSubgraph
            
            subgraph = ChapterSubgraph()
            result = subgraph.run(
                chapter_outline={"number": 1, "title": "Test"},
                source_chunks=[],
            )
            
            # Scores should be in valid range
            assert 0 <= result["voice_score"] <= 1
            assert 0 <= result["fact_score"] <= 1
            assert 0 <= result["cohesion_score"] <= 1
        except ImportError as e:
            pytest.skip(f"Could not import subgraph: {e}")


@pytest.mark.skipif(not has_api_keys(), reason="API keys not available")
class TestLiveAgentIntegration:
    """Live tests with real agents (requires API keys)."""
    
    def test_outline_with_real_agent(self):
        """OutlineSubgraph should use real OutlinePlannerAgent."""
        from orchestrator.subgraphs import OutlineSubgraph
        
        subgraph = OutlineSubgraph()
        
        # Should have loaded the planner
        assert subgraph.planner is not None, "Planner agent should be loaded"
        
        result = subgraph.run(
            source_summaries=["A book about the history of computing."],
            project_title="The Digital Age",
            target_chapters=3,
        )
        
        # With real agent, should have used tokens
        assert result["tokens_used"] > 0, "Should have used tokens with real agent"
        assert result["cost"] > 0, "Should have incurred cost"
        
        # Outline should be more detailed
        outline = result["outline"]
        assert outline is not None
        assert "chapters" in outline
        assert len(outline["chapters"]) == 3
    
    def test_chapter_with_real_agents(self):
        """ChapterSubgraph should use real agents for all steps."""
        from orchestrator.subgraphs import ChapterSubgraph
        
        subgraph = ChapterSubgraph()
        
        # Should have loaded agents
        assert subgraph.drafter is not None, "Drafter should be loaded"
        
        result = subgraph.run(
            chapter_outline={
                "number": 1,
                "title": "The Dawn of Computers",
                "summary": "How the first computers came to be.",
                "key_points": ["ENIAC", "Turing", "Von Neumann"],
            },
            source_chunks=["The ENIAC was completed in 1945."],
            target_words=500,
        )
        
        assert result["tokens_used"] > 0, "Should have used tokens"
        assert len(result["content"]) > 100, "Should have substantial content"


class TestFeedbackAPIIntegration:
    """Test API endpoints for feedback."""
    
    def test_approval_endpoint_structure(self):
        """Approval endpoint should accept correct request body."""
        endpoints_path = API_PATH / "app" / "api" / "v1" / "endpoints" / "generation.py"
        content = endpoints_path.read_text()
        
        # Check request model
        assert "class OutlineApprovalRequest" in content
        assert "approve: bool" in content
        assert "feedback: Optional[str]" in content
    
    def test_feedback_endpoint_structure(self):
        """Feedback endpoint should accept correct request body."""
        endpoints_path = API_PATH / "app" / "api" / "v1" / "endpoints" / "generation.py"
        content = endpoints_path.read_text()
        
        # Check request model
        assert "class FeedbackRequest" in content
        assert "feedback: str" in content
        assert "target: str" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

