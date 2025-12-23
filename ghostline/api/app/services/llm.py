"""
LLM Client Service for AI-powered text generation.

Provides a unified interface for calling Claude (Anthropic) and GPT (OpenAI) models.
Supports streaming, token counting, and cost estimation.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import AsyncGenerator, Optional

import tiktoken
from anthropic import Anthropic
from openai import OpenAI

from app.core.config import settings


class ModelProvider(str, Enum):
    """Supported model providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class LLMResponse:
    """Response from an LLM call."""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    stop_reason: Optional[str] = None


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    provider: ModelProvider
    model_id: str
    max_tokens: int
    input_cost_per_1k: float  # USD per 1000 input tokens
    output_cost_per_1k: float  # USD per 1000 output tokens


# Model configurations with pricing (as of Dec 2024)
MODELS = {
    # Anthropic models
    "claude-3-5-sonnet-20241022": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-3-5-sonnet-20241022",
        max_tokens=8192,
        input_cost_per_1k=0.003,
        output_cost_per_1k=0.015,
    ),
    "claude-3-haiku-20240307": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-3-haiku-20240307",
        max_tokens=4096,
        input_cost_per_1k=0.00025,
        output_cost_per_1k=0.00125,
    ),
    # OpenAI models
    "gpt-4o": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_id="gpt-4o",
        max_tokens=4096,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
    ),
    "gpt-4o-mini": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_id="gpt-4o-mini",
        max_tokens=4096,
        input_cost_per_1k=0.00015,
        output_cost_per_1k=0.0006,
    ),
}


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate text from a prompt."""
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Generate text with streaming output."""
        pass


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client."""
    
    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.config = MODELS.get(model)
        if not self.config:
            raise ValueError(f"Unknown model: {model}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate text using Claude."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "You are a helpful AI assistant.",
            messages=[{"role": "user", "content": prompt}],
        )
        
        content = message.content[0].text if message.content else ""
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        
        cost = self._calculate_cost(input_tokens, output_tokens)
        
        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost=cost,
            stop_reason=message.stop_reason,
        )
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Generate text with streaming using Claude."""
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "You are a helpful AI assistant.",
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost for the request."""
        input_cost = (input_tokens / 1000) * self.config.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.config.output_cost_per_1k
        return input_cost + output_cost


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT client."""
    
    def __init__(self, model: str = "gpt-4o"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.config = MODELS.get(model)
        if not self.config:
            raise ValueError(f"Unknown model: {model}")
        
        # Token counter for OpenAI
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate text using GPT."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        content = response.choices[0].message.content or ""
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0
        
        cost = self._calculate_cost(input_tokens, output_tokens)
        
        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost=cost,
            stop_reason=response.choices[0].finish_reason,
        )
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Generate text with streaming using GPT."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost for the request."""
        input_cost = (input_tokens / 1000) * self.config.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.config.output_cost_per_1k
        return input_cost + output_cost


class LLMService:
    """
    High-level LLM service that manages multiple clients.
    
    Provides model routing based on task requirements:
    - High-quality tasks: Claude Sonnet or GPT-4o
    - Fast/cheap tasks: Claude Haiku or GPT-4o-mini
    """
    
    def __init__(self):
        self._clients: dict[str, BaseLLMClient] = {}
        
        # Default models
        self.default_model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self.fast_model = "claude-3-haiku-20240307"
    
    def get_client(self, model: Optional[str] = None) -> BaseLLMClient:
        """Get or create a client for the specified model."""
        model = model or self.default_model
        
        if model not in self._clients:
            config = MODELS.get(model)
            if not config:
                raise ValueError(f"Unknown model: {model}")
            
            if config.provider == ModelProvider.ANTHROPIC:
                self._clients[model] = AnthropicClient(model)
            elif config.provider == ModelProvider.OPENAI:
                self._clients[model] = OpenAIClient(model)
            else:
                raise ValueError(f"Unknown provider: {config.provider}")
        
        return self._clients[model]
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate text using the specified or default model."""
        client = self.get_client(model)
        return client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    
    def generate_fast(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate text using a fast/cheap model (for simple tasks)."""
        return self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=self.fast_model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    
    def generate_quality(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate text using a high-quality model (for important tasks)."""
        return self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=self.default_model,
            max_tokens=max_tokens,
            temperature=temperature,
        )


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

