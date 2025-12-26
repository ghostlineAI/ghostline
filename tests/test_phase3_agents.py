"""
Phase 3 Tests: Agent Framework with LangGraph

These tests verify the agent framework and LangGraph orchestration
work correctly. Includes LIVE agent calls where API keys are available.
"""

import pytest
import sys
import os

# Add the agents module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'agents'))


class TestBaseAgent:
    """Test base agent classes."""
    
    def test_base_agent_imports(self):
        """Base agent should import without errors."""
        from agents.base.agent import (
            BaseAgent,
            AgentConfig,
            AgentOutput,
            AgentRole,
            LLMProvider,
            ConversationAgent,
        )
        assert BaseAgent is not None
        assert AgentConfig is not None
    
    def test_agent_config_defaults(self):
        """Agent config should have sensible defaults."""
        from agents.base.agent import AgentConfig, AgentRole
        
        config = AgentConfig(role=AgentRole.PLANNER)
        
        assert config.model is not None
        assert config.temperature >= 0 and config.temperature <= 1
        assert config.max_tokens > 0
        assert config.max_retries > 0
    
    def test_agent_output_structure(self):
        """AgentOutput should have required fields."""
        from agents.base.agent import AgentOutput
        
        output = AgentOutput(
            content="Test content",
            tokens_used=100,
            estimated_cost=0.01,
        )
        
        assert output.is_success()
        assert output.content == "Test content"
        
        # Error case
        error_output = AgentOutput(content="", error="Something failed")
        assert not error_output.is_success()
    
    def test_agent_roles_defined(self):
        """All expected agent roles should be defined."""
        from agents.base.agent import AgentRole
        
        expected_roles = [
            'ORCHESTRATOR', 'PLANNER', 'DRAFTER', 'EDITOR',
            'CRITIC', 'FACT_CHECKER', 'VOICE_ANALYST', 'COHESION'
        ]
        
        for role in expected_roles:
            assert hasattr(AgentRole, role), f"Missing role: {role}"


class TestSpecializedAgents:
    """Test specialized agent classes."""
    
    def test_outline_planner_imports(self):
        """Outline planner should import."""
        from agents.specialized.outline_planner import (
            OutlinePlannerAgent,
            OutlineCriticAgent,
            OutlineState,
        )
        assert OutlinePlannerAgent is not None
        assert OutlineCriticAgent is not None
    
    def test_content_drafter_imports(self):
        """Content drafter should import."""
        from agents.specialized.content_drafter import (
            ContentDrafterAgent,
            ChapterState,
        )
        assert ContentDrafterAgent is not None
    
    def test_voice_editor_imports(self):
        """Voice editor should import."""
        from agents.specialized.voice_editor import (
            VoiceEditorAgent,
            VoiceState,
        )
        assert VoiceEditorAgent is not None
    
    def test_fact_checker_imports(self):
        """Fact checker should import."""
        from agents.specialized.fact_checker import (
            FactCheckerAgent,
            FactCheckState,
        )
        assert FactCheckerAgent is not None
    
    def test_cohesion_analyst_imports(self):
        """Cohesion analyst should import."""
        from agents.specialized.cohesion_analyst import (
            CohesionAnalystAgent,
            CohesionState,
        )
        assert CohesionAnalystAgent is not None
    
    def test_all_agents_have_required_methods(self):
        """All specialized agents should have process() and get_system_prompt()."""
        from agents.specialized.outline_planner import OutlinePlannerAgent
        from agents.specialized.content_drafter import ContentDrafterAgent
        from agents.specialized.voice_editor import VoiceEditorAgent
        from agents.specialized.fact_checker import FactCheckerAgent
        from agents.specialized.cohesion_analyst import CohesionAnalystAgent
        
        agents = [
            OutlinePlannerAgent,
            ContentDrafterAgent,
            VoiceEditorAgent,
            FactCheckerAgent,
            CohesionAnalystAgent,
        ]
        
        for agent_class in agents:
            # Create instance without calling __init__ fully
            assert hasattr(agent_class, 'process')
            assert hasattr(agent_class, 'get_system_prompt')
            assert hasattr(agent_class, '_default_config')
    
    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set"
    )
    @pytest.mark.slow
    def test_outline_planner_live(self):
        """LIVE TEST: OutlinePlannerAgent generates outline."""
        from agents.specialized.outline_planner import OutlinePlannerAgent, OutlineState
        
        agent = OutlinePlannerAgent()
        
        state = OutlineState(
            project_title="The Future of AI",
            project_description="A book about artificial intelligence and its impact on society",
            source_summaries=[
                "AI has made remarkable progress in recent years, particularly in language models.",
                "Concerns about AI safety and ethics are growing among researchers and policymakers.",
                "The economic impact of AI could be transformative, affecting millions of jobs.",
            ],
            target_chapters=5,
        )
        
        output = agent.process(state)
        
        assert output.is_success(), f"Failed: {output.error}"
        assert output.structured_data is not None
        
        # Check outline structure
        outline = output.structured_data
        assert 'chapters' in outline or 'title' in outline
        
        print(f"  [LIVE] Outline generated: {len(str(outline))} chars")
        print(f"  [LIVE] Tokens: {output.tokens_used}, Cost: ${output.estimated_cost:.4f}")


class TestLangGraphOrchestration:
    """Test LangGraph workflow and subgraphs."""
    
    def test_workflow_imports(self):
        """Workflow should import without errors."""
        from orchestrator.workflow import (
            BookGenerationWorkflow,
            WorkflowState,
            WorkflowPhase,
            create_initial_state,
        )
        assert BookGenerationWorkflow is not None
    
    def test_subgraphs_imports(self):
        """Subgraphs should import without errors."""
        from orchestrator.subgraphs import (
            OutlineSubgraph,
            ChapterSubgraph,
            SubgraphConfig,
        )
        assert OutlineSubgraph is not None
        assert ChapterSubgraph is not None
    
    def test_initial_state_creation(self):
        """Initial workflow state should be valid."""
        from orchestrator.workflow import create_initial_state, WorkflowPhase
        
        state = create_initial_state(
            project_id="test-project-id",
            user_id="test-user-id",
            source_material_ids=["mat-1", "mat-2"],
        )
        
        assert state["project_id"] == "test-project-id"
        assert state["user_id"] == "test-user-id"
        assert state["phase"] == WorkflowPhase.INITIALIZED.value
        assert state["progress"] == 0
        assert len(state["source_material_ids"]) == 2
    
    def test_subgraph_config_defaults(self):
        """Subgraph config should have bounded limits."""
        from orchestrator.subgraphs import SubgraphConfig
        
        config = SubgraphConfig()
        
        assert config.max_turns > 0
        assert config.max_tokens > 0
        assert config.max_cost > 0
        assert config.timeout_seconds > 0
    
    def test_outline_subgraph_runs(self):
        """OutlineSubgraph should execute its graph."""
        from orchestrator.subgraphs import OutlineSubgraph
        
        subgraph = OutlineSubgraph()
        
        result = subgraph.run(
            source_summaries=["Test summary about AI"],
            project_title="Test Book",
            target_chapters=3,
        )
        
        assert "outline" in result
        assert "iterations" in result
        assert result["outline"] is not None
        
        print(f"  Outline subgraph: {result['iterations']} iterations")
    
    def test_chapter_subgraph_runs(self):
        """ChapterSubgraph should execute its graph."""
        from orchestrator.subgraphs import ChapterSubgraph
        
        subgraph = ChapterSubgraph()
        
        result = subgraph.run(
            chapter_outline={"number": 1, "title": "Introduction", "summary": "An intro"},
            source_chunks=["Relevant source content for the chapter."],
            target_words=1000,
        )
        
        assert "content" in result
        assert "voice_score" in result
        assert "fact_score" in result
        assert "cohesion_score" in result
        
        print(f"  Chapter subgraph: voice={result['voice_score']:.2f}, fact={result['fact_score']:.2f}")
    
    def test_workflow_graph_compiles(self):
        """BookGenerationWorkflow graph should compile."""
        from orchestrator.workflow import BookGenerationWorkflow
        
        workflow = BookGenerationWorkflow()
        
        assert workflow.graph is not None
        assert workflow.checkpointer is not None


class TestAgentIntegration:
    """Test agent system integration."""
    
    def test_agents_share_llm_config(self):
        """Multiple agents should be able to share configuration."""
        from agents.base.agent import AgentConfig, AgentRole, LLMProvider
        from agents.specialized.outline_planner import OutlinePlannerAgent
        from agents.specialized.content_drafter import ContentDrafterAgent
        
        # Create shared config
        shared_config = AgentConfig(
            role=AgentRole.PLANNER,
            model="claude-3-haiku-20240307",
            provider=LLMProvider.ANTHROPIC,
            temperature=0.5,
        )
        
        # Both agents can use it (they'll override role internally)
        planner = OutlinePlannerAgent()  # Uses default
        drafter = ContentDrafterAgent()  # Uses default
        
        # They should both have configs
        assert planner.config is not None
        assert drafter.config is not None
    
    def test_full_pipeline_structure(self):
        """Verify the full pipeline can be constructed."""
        from orchestrator.workflow import BookGenerationWorkflow, create_initial_state
        from orchestrator.subgraphs import OutlineSubgraph, ChapterSubgraph
        
        # Create all components
        workflow = BookGenerationWorkflow()
        outline_subgraph = OutlineSubgraph()
        chapter_subgraph = ChapterSubgraph()
        
        # Create initial state
        state = create_initial_state(
            project_id="integration-test",
            user_id="test-user",
            source_material_ids=["source-1"],
        )
        
        # All components should be ready
        assert workflow.graph is not None
        assert outline_subgraph.graph is not None
        assert chapter_subgraph.graph is not None
        assert state["phase"] == "initialized"
        
        print("  Full pipeline structure verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])



