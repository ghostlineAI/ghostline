"""
Base Agent class for the GhostLine multi-agent system.

All specialized agents inherit from BaseAgent, which provides:
- LLM integration (Claude/GPT)
- State management
- Cost tracking
- Output formatting
- Conversation logging
"""

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

# Import conversation logger
from agents.core import get_conversation_logger

logger = logging.getLogger(__name__)


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
            
            response = self.llm.invoke(messages)
            
            duration = int((time.time() - start) * 1000)
            
            # Extract usage info
            tokens = 0
            cost = 0.0
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                tokens = response.usage_metadata.get('total_tokens', 0)
                cost = self._estimate_cost(tokens)
            
            self._total_tokens += tokens
            self._total_cost += cost
            self._call_count += 1
            
            response_content = response.content if isinstance(response.content, str) else str(response.content)
            
            # Log the response received
            conv_logger.log_response(
                agent_name=agent_name,
                response=response_content,
                tokens_used=tokens,
                cost=cost,
                duration_ms=duration,
                model=self.config.model,
            )
            
            return AgentOutput(
                content=response_content,
                tokens_used=tokens,
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
            
            return AgentOutput(
                content="",
                error=str(e),
                duration_ms=duration,
            )
    
    def _estimate_cost(self, tokens: int) -> float:
        """Estimate cost based on tokens and model."""
        # Rough pricing per 1K tokens
        pricing = {
            "claude-sonnet-4-20250514": 0.009,  # Average of input/output
            "claude-3-5-sonnet-20241022": 0.009,
            "claude-3-haiku-20240307": 0.001,
            "gpt-4o": 0.01,
            "gpt-4o-mini": 0.0004,
        }
        rate = pricing.get(self.config.model, 0.01)
        return (tokens / 1000) * rate
    
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

