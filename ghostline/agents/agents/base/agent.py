"""
Base Agent class for the GhostLine multi-agent system.

All specialized agents inherit from BaseAgent, which provides:
- LLM integration (Claude/GPT)
- State management
- Cost tracking (with database persistence)
- Output formatting
- Conversation logging
"""

import os
import sys
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

# Add API module to path for cost tracking imports
# agents/agents/base/agent.py -> agents/ -> api/
API_PATH = Path(__file__).parent.parent.parent.parent / "api"
if API_PATH.exists() and str(API_PATH) not in sys.path:
    sys.path.insert(0, str(API_PATH))

# Import conversation logger
from agents.core import get_conversation_logger

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Cost tracking context (thread-local style)
# ─────────────────────────────────────────────────────────────────────────────
_cost_context: dict = {}


def set_cost_context(
    project_id: Optional[UUID] = None,
    task_id: Optional[UUID] = None,
    workflow_run_id: Optional[str] = None,
    chapter_number: Optional[int] = None,
    db_session=None,
):
    """
    Set the context for cost tracking.
    Call this before running agent workflows to enable DB persistence.
    """
    global _cost_context
    _cost_context = {
        "project_id": project_id,
        "task_id": task_id,
        "workflow_run_id": workflow_run_id,
        "chapter_number": chapter_number,
        "db_session": db_session,
    }


def get_cost_context() -> dict:
    """Get the current cost tracking context."""
    return _cost_context.copy()


def clear_cost_context():
    """Clear the cost tracking context."""
    global _cost_context
    _cost_context = {}


class AgentRole(str, Enum):
    """Roles that agents can play in the system."""
    ORCHESTRATOR = "orchestrator"
    PLANNER = "planner"
    DRAFTER = "drafter"
    EDITOR = "editor"
    CRITIC = "critic"
    FACT_CHECKER = "fact_checker"
    VOICE_ANALYST = "voice_analyst"
    COHESION = "cohesion_analyst"


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    role: AgentRole
    model: str = "claude-sonnet-4-20250514"  # Latest Claude Sonnet
    provider: LLMProvider = LLMProvider.ANTHROPIC
    temperature: float = 0.7
    max_tokens: int = 4096
    max_retries: int = 3
    timeout: int = 120  # seconds
    
    # Cost control
    max_cost_per_call: float = 1.0  # USD
    budget_remaining: float = 10.0  # USD


@dataclass
class AgentOutput:
    """Standard output from an agent."""
    content: str
    structured_data: Optional[dict] = None
    confidence: float = 1.0
    reasoning: Optional[str] = None
    tokens_used: int = 0
    estimated_cost: float = 0.0
    duration_ms: int = 0
    error: Optional[str] = None
    
    def is_success(self) -> bool:
        """Check if the output represents a successful operation."""
        return self.error is None


# Type for agent state
StateT = TypeVar("StateT", bound=BaseModel)


class BaseAgent(ABC, Generic[StateT]):
    """
    Abstract base class for all GhostLine agents.
    
    Provides common functionality:
    - LLM client management
    - State handling
    - Cost tracking
    - Structured output parsing
    
    Subclasses must implement:
    - process(state) -> AgentOutput
    - get_system_prompt() -> str
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or self._default_config()
        self._llm = None
        self._total_cost = 0.0
        self._total_tokens = 0
        self._call_count = 0
    
    @abstractmethod
    def _default_config(self) -> AgentConfig:
        """Return the default configuration for this agent."""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass
    
    @abstractmethod
    def process(self, state: StateT) -> AgentOutput:
        """
        Process the current state and produce output.
        
        Args:
            state: The current workflow state
            
        Returns:
            AgentOutput with the agent's response
        """
        pass
    
    @property
    def llm(self):
        """Get the LLM client, initializing if needed."""
        if self._llm is None:
            self._llm = self._create_llm()
        return self._llm
    
    def _create_llm(self):
        """Create the LLM client based on configuration."""
        if self.config.provider == LLMProvider.ANTHROPIC:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            
            return ChatAnthropic(
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                api_key=api_key,
            )
        
        elif self.config.provider == LLMProvider.OPENAI:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            
            return ChatOpenAI(
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                api_key=api_key,
            )
        
        else:
            raise ValueError(f"Unknown provider: {self.config.provider}")
    
    def invoke(self, prompt: str, context: Optional[str] = None) -> AgentOutput:
        """
        Invoke the LLM with a prompt.
        
        Args:
            prompt: The user prompt
            context: Optional additional context
            
        Returns:
            AgentOutput with the response
        """
        import time
        start = time.time()
        
        # Get conversation logger
        conv_logger = get_conversation_logger()
        agent_name = self.__class__.__name__
        
        # Track fallback state
        is_fallback = False
        fallback_reason = None
        used_model = self.config.model
        used_provider = self.config.provider.value
        
        try:
            messages = [
                SystemMessage(content=self.get_system_prompt()),
            ]
            
            if context:
                messages.append(HumanMessage(content=f"Context:\n{context}"))
            
            messages.append(HumanMessage(content=prompt))
            
            # Log the prompt being sent
            conv_logger.log_prompt(
                agent_name=agent_name,
                prompt=prompt,
                model=self.config.model,
                context=context or "",
            )

            def _should_fallback_to_openai(err: Exception) -> bool:
                """Return True if we should automatically fall back from Anthropic to OpenAI."""
                msg = str(err or "").lower()
                # Anthropic quota/credit exhaustion message
                if "credit balance is too low" in msg:
                    return True
                if "plans & billing" in msg and "anthropic" in msg:
                    return True
                # Some clients surface this as quota/insufficient balance
                if "insufficient" in msg and "anthropic" in msg:
                    return True
                return False

            try:
                response = self.llm.invoke(messages)
            except Exception as e:
                # If Anthropic is unavailable (credits/quota), transparently fall back to OpenAI
                # so the product can still run end-to-end in dev.
                strict_mode = os.getenv("GHOSTLINE_STRICT_MODE", "").strip().lower() in ("1", "true", "yes", "on")
                allow_fallback = os.getenv("GHOSTLINE_ALLOW_LLM_FALLBACK", "1").strip().lower() in ("1", "true", "yes", "on")
                if strict_mode:
                    allow_fallback = False

                if allow_fallback and self.config.provider == LLMProvider.ANTHROPIC and _should_fallback_to_openai(e):
                    openai_key = os.getenv("OPENAI_API_KEY")
                    if openai_key:
                        fallback_model = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4o")
                        conv_logger.log_system(
                            agent_name=agent_name,
                            message=(
                                "Anthropic call failed (likely insufficient credits). "
                                f"Falling back to OpenAI model={fallback_model}."
                            ),
                        )
                        fallback_llm = ChatOpenAI(
                            model=fallback_model,
                            temperature=self.config.temperature,
                            max_tokens=self.config.max_tokens,
                            api_key=openai_key,
                        )
                        response = fallback_llm.invoke(messages)
                        # Track fallback
                        is_fallback = True
                        fallback_reason = str(e)
                        used_model = fallback_model
                        used_provider = "openai"
                        # Persist fallback for subsequent calls in this agent instance
                        self.config.provider = LLMProvider.OPENAI
                        self.config.model = fallback_model
                        self._llm = fallback_llm
                    else:
                        raise e
                else:
                    raise e
            
            duration = int((time.time() - start) * 1000)
            
            # Extract usage info - get input/output tokens separately
            input_tokens = 0
            output_tokens = 0
            total_tokens = 0
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                input_tokens = response.usage_metadata.get('input_tokens', 0)
                output_tokens = response.usage_metadata.get('output_tokens', 0)
                total_tokens = response.usage_metadata.get('total_tokens', input_tokens + output_tokens)
            
            cost = self._estimate_cost_detailed(input_tokens, output_tokens, used_model, used_provider)
            
            self._total_tokens += total_tokens
            self._total_cost += cost
            self._call_count += 1
            
            response_content = response.content if isinstance(response.content, str) else str(response.content)
            
            # Log the response received
            conv_logger.log_response(
                agent_name=agent_name,
                response=response_content,
                tokens_used=total_tokens,
                cost=cost,
                duration_ms=duration,
                model=used_model,
            )
            
            # Record to database if context is set
            self._record_to_db(
                agent_name=agent_name,
                model=used_model,
                provider=used_provider,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration,
                success=True,
                is_fallback=is_fallback,
                fallback_reason=fallback_reason,
                prompt_preview=prompt,
                response_preview=response_content,
            )
            
            return AgentOutput(
                content=response_content,
                tokens_used=total_tokens,
                estimated_cost=cost,
                duration_ms=duration,
            )
            
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            
            # Log the error
            conv_logger.log_system(
                agent_name=agent_name,
                message=f"ERROR: {str(e)}"
            )
            
            # Record failed call to database
            self._record_to_db(
                agent_name=agent_name,
                model=used_model,
                provider=used_provider,
                input_tokens=0,
                output_tokens=0,
                duration_ms=duration,
                success=False,
                error_message=str(e),
                prompt_preview=prompt,
            )
            
            return AgentOutput(
                content="",
                error=str(e),
                duration_ms=duration,
            )
    
    def _record_to_db(
        self,
        agent_name: str,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: int,
        success: bool,
        is_fallback: bool = False,
        fallback_reason: Optional[str] = None,
        prompt_preview: Optional[str] = None,
        response_preview: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """Record this LLM call to the database if context is set."""
        ctx = get_cost_context()
        db = ctx.get("db_session")
        
        if not db:
            # No DB session set, skip recording
            return
        
        try:
            from app.services.cost_tracker import CostTracker
            
            tracker = CostTracker(db)
            tracker.record(
                agent_name=agent_name,
                model=model,
                provider=provider,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                success=success,
                call_type="chat",
                project_id=ctx.get("project_id"),
                task_id=ctx.get("task_id"),
                workflow_run_id=ctx.get("workflow_run_id"),
                chapter_number=ctx.get("chapter_number"),
                agent_role=self.config.role.value if self.config.role else None,
                is_fallback=is_fallback,
                fallback_reason=fallback_reason,
                prompt_preview=prompt_preview,
                response_preview=response_preview,
                error_message=error_message,
                metadata={
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                },
            )
        except Exception as e:
            # Don't fail the agent call if cost tracking fails
            logger.warning(f"Failed to record cost to database: {e}")
    
    def _estimate_cost_detailed(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
        provider: str,
    ) -> float:
        """Estimate cost based on input/output tokens and model."""
        # Pricing per 1K tokens (input, output)
        pricing = {
            # Anthropic
            "claude-sonnet-4-20250514": (0.003, 0.015),
            "claude-3-5-sonnet-20241022": (0.003, 0.015),
            "claude-3-5-sonnet-latest": (0.003, 0.015),
            "claude-3-opus-20240229": (0.015, 0.075),
            "claude-3-haiku-20240307": (0.00025, 0.00125),
            # OpenAI
            "gpt-4o": (0.0025, 0.01),
            "gpt-4o-2024-11-20": (0.0025, 0.01),
            "gpt-4o-mini": (0.00015, 0.0006),
            "gpt-4-turbo": (0.01, 0.03),
            "gpt-4": (0.03, 0.06),
            "gpt-3.5-turbo": (0.0005, 0.0015),
        }
        
        input_rate, output_rate = pricing.get(model, (0.003, 0.015))
        return (input_tokens / 1000) * input_rate + (output_tokens / 1000) * output_rate
    
    def _estimate_cost(self, tokens: int) -> float:
        """Estimate cost based on total tokens (legacy method, assumes 50/50 split)."""
        # Assume roughly 50% input, 50% output for backward compatibility
        half = tokens // 2
        return self._estimate_cost_detailed(half, tokens - half, self.config.model, self.config.provider.value)
    
    def get_stats(self) -> dict:
        """Get statistics for this agent."""
        return {
            "role": self.config.role.value,
            "model": self.config.model,
            "total_calls": self._call_count,
            "total_tokens": self._total_tokens,
            "total_cost": round(self._total_cost, 4),
        }


class ConversationAgent(BaseAgent):
    """
    Agent that can participate in multi-agent conversations.
    
    Used for bounded subgraph discussions (e.g., outline creation,
    chapter revision loops).
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        max_turns: int = 5,
    ):
        super().__init__(config)
        self.max_turns = max_turns
        self.conversation_history: list[tuple[str, str]] = []
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history."""
        self.conversation_history.append((role, content))
    
    def respond(self, message: str) -> AgentOutput:
        """Respond to a message in the conversation."""
        # Build context from history
        context = "\n".join(
            f"[{role}]: {content}"
            for role, content in self.conversation_history[-10:]
        )
        
        output = self.invoke(message, context=context if context else None)
        
        if output.is_success():
            self.add_message("assistant", output.content)
        
        return output
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

