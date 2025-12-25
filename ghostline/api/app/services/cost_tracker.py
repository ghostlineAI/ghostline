"""
Cost Tracker Service for GhostLine.

Records and analyzes LLM API costs at the most granular level (per call),
enabling aggregation at any level: agent, chapter, project, model, provider.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.llm_usage_log import LLMUsageLog, LLMProvider, CallType

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Pricing tables (per 1K tokens)
# ─────────────────────────────────────────────────────────────────────────────

# Anthropic Claude pricing (as of 2024-12)
ANTHROPIC_PRICING = {
    # Claude 4 Sonnet
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    # Claude 3.5 Sonnet
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-5-sonnet-latest": {"input": 0.003, "output": 0.015},
    # Claude 3 Opus
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    # Claude 3 Haiku
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
}

# OpenAI pricing (as of 2024-12)
OPENAI_PRICING = {
    # GPT-4o
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-2024-11-20": {"input": 0.0025, "output": 0.01},
    # GPT-4o mini
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    # GPT-4 Turbo
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    # GPT-4
    "gpt-4": {"input": 0.03, "output": 0.06},
    # GPT-3.5 Turbo
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}

# OpenAI embedding pricing
EMBEDDING_PRICING = {
    "text-embedding-3-small": 0.00002,  # per 1K tokens
    "text-embedding-3-large": 0.00013,
    "text-embedding-ada-002": 0.0001,
}


def get_pricing(provider: str, model: str) -> tuple[float, float]:
    """
    Get input/output pricing per 1K tokens for a model.
    
    Returns:
        Tuple of (input_price, output_price)
    """
    if provider == "anthropic":
        pricing = ANTHROPIC_PRICING.get(model, {"input": 0.003, "output": 0.015})
        return pricing["input"], pricing["output"]
    elif provider == "openai":
        if "embedding" in model.lower():
            price = EMBEDDING_PRICING.get(model, 0.0001)
            return price, 0.0  # Embeddings only have input cost
        pricing = OPENAI_PRICING.get(model, {"input": 0.0025, "output": 0.01})
        return pricing["input"], pricing["output"]
    else:
        # Default fallback
        return 0.01, 0.01


@dataclass
class CostRecord:
    """Record for a single LLM call."""
    agent_name: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    duration_ms: int
    success: bool
    call_type: str = "chat"
    project_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    workflow_run_id: Optional[str] = None
    chapter_number: Optional[int] = None
    agent_role: Optional[str] = None
    is_fallback: bool = False
    fallback_reason: Optional[str] = None
    prompt_preview: Optional[str] = None
    response_preview: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class CostSummary:
    """Aggregated cost summary."""
    total_calls: int
    total_tokens: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost: float
    total_input_cost: float
    total_output_cost: float
    avg_cost_per_call: float
    avg_tokens_per_call: float
    avg_duration_ms: float
    success_rate: float
    by_model: dict  # model -> {calls, tokens, cost}
    by_agent: dict  # agent_name -> {calls, tokens, cost}
    by_chapter: dict  # chapter_number -> {calls, tokens, cost}
    by_provider: dict  # provider -> {calls, tokens, cost}


class CostTracker:
    """
    Service for recording and analyzing LLM costs.
    
    Usage:
        tracker = CostTracker(db)
        
        # Record a call
        tracker.record(
            agent_name="ContentDrafterAgent",
            model="claude-sonnet-4-20250514",
            provider="anthropic",
            input_tokens=1000,
            output_tokens=500,
            duration_ms=2500,
            project_id=project_id,
            task_id=task_id,
            chapter_number=1,
        )
        
        # Get summary for a project
        summary = tracker.get_project_summary(project_id)
        print(f"Total cost: ${summary.total_cost:.4f}")
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def record(
        self,
        agent_name: str,
        model: str,
        provider: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        duration_ms: int = 0,
        success: bool = True,
        call_type: str = "chat",
        project_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        workflow_run_id: Optional[str] = None,
        chapter_number: Optional[int] = None,
        agent_role: Optional[str] = None,
        is_fallback: bool = False,
        fallback_reason: Optional[str] = None,
        prompt_preview: Optional[str] = None,
        response_preview: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> LLMUsageLog:
        """
        Record an LLM API call.
        
        Returns:
            The created LLMUsageLog record.
        """
        # Calculate costs
        input_price, output_price = get_pricing(provider, model)
        input_cost = (input_tokens / 1000) * input_price
        output_cost = (output_tokens / 1000) * output_price
        total_cost = input_cost + output_cost
        total_tokens = input_tokens + output_tokens
        
        # Create log entry
        log = LLMUsageLog(
            agent_name=agent_name,
            agent_role=agent_role,
            model=model,
            provider=provider,
            call_type=call_type or "chat",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            input_price_per_1k=input_price,
            output_price_per_1k=output_price,
            duration_ms=duration_ms,
            success=success,
            project_id=project_id,
            task_id=task_id,
            workflow_run_id=workflow_run_id,
            chapter_number=chapter_number,
            is_fallback=is_fallback,
            fallback_reason=fallback_reason,
            prompt_preview=prompt_preview[:500] if prompt_preview else None,
            response_preview=response_preview[:500] if response_preview else None,
            error_message=error_message,
            extra_data=metadata or {},
        )
        
        self.db.add(log)
        self.db.commit()
        
        logger.info(
            f"📊 [CostTracker] Recorded: {agent_name} | {model} | "
            f"{total_tokens} tokens | ${total_cost:.4f}"
        )
        
        return log
    
    def get_task_summary(self, task_id: UUID) -> CostSummary:
        """Get cost summary for a specific generation task."""
        return self._get_summary(task_id=task_id)
    
    def get_project_summary(self, project_id: UUID) -> CostSummary:
        """Get cost summary for a project."""
        return self._get_summary(project_id=project_id)
    
    def get_workflow_run_summary(self, workflow_run_id: str) -> CostSummary:
        """Get cost summary for a specific workflow run."""
        return self._get_summary(workflow_run_id=workflow_run_id)
    
    def get_all_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> CostSummary:
        """Get overall cost summary, optionally filtered by date range."""
        return self._get_summary(start_date=start_date, end_date=end_date)
    
    def _get_summary(
        self,
        task_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        workflow_run_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> CostSummary:
        """Internal method to build cost summary with filters."""
        
        # Build base query
        query = self.db.query(LLMUsageLog)
        
        if task_id:
            query = query.filter(LLMUsageLog.task_id == task_id)
        if project_id:
            query = query.filter(LLMUsageLog.project_id == project_id)
        if workflow_run_id:
            query = query.filter(LLMUsageLog.workflow_run_id == workflow_run_id)
        if start_date:
            query = query.filter(LLMUsageLog.created_at >= start_date)
        if end_date:
            query = query.filter(LLMUsageLog.created_at <= end_date)
        
        logs = query.all()
        
        if not logs:
            return CostSummary(
                total_calls=0,
                total_tokens=0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_cost=0.0,
                total_input_cost=0.0,
                total_output_cost=0.0,
                avg_cost_per_call=0.0,
                avg_tokens_per_call=0.0,
                avg_duration_ms=0.0,
                success_rate=0.0,
                by_model={},
                by_agent={},
                by_chapter={},
                by_provider={},
            )
        
        # Aggregate
        total_calls = len(logs)
        total_tokens = sum(l.total_tokens for l in logs)
        total_input_tokens = sum(l.input_tokens for l in logs)
        total_output_tokens = sum(l.output_tokens for l in logs)
        total_cost = sum(l.total_cost for l in logs)
        total_input_cost = sum(l.input_cost for l in logs)
        total_output_cost = sum(l.output_cost for l in logs)
        total_duration = sum(l.duration_ms for l in logs)
        successful = sum(1 for l in logs if l.success)
        
        # By model
        by_model = {}
        for log in logs:
            if log.model not in by_model:
                by_model[log.model] = {"calls": 0, "tokens": 0, "cost": 0.0, "input_tokens": 0, "output_tokens": 0}
            by_model[log.model]["calls"] += 1
            by_model[log.model]["tokens"] += log.total_tokens
            by_model[log.model]["cost"] += log.total_cost
            by_model[log.model]["input_tokens"] += log.input_tokens
            by_model[log.model]["output_tokens"] += log.output_tokens
        
        # By agent
        by_agent = {}
        for log in logs:
            if log.agent_name not in by_agent:
                by_agent[log.agent_name] = {"calls": 0, "tokens": 0, "cost": 0.0}
            by_agent[log.agent_name]["calls"] += 1
            by_agent[log.agent_name]["tokens"] += log.total_tokens
            by_agent[log.agent_name]["cost"] += log.total_cost
        
        # By chapter
        by_chapter = {}
        for log in logs:
            if log.chapter_number is not None:
                ch = log.chapter_number
                if ch not in by_chapter:
                    by_chapter[ch] = {"calls": 0, "tokens": 0, "cost": 0.0}
                by_chapter[ch]["calls"] += 1
                by_chapter[ch]["tokens"] += log.total_tokens
                by_chapter[ch]["cost"] += log.total_cost
        
        # By provider
        by_provider = {}
        for log in logs:
            prov = log.provider or "unknown"
            if prov not in by_provider:
                by_provider[prov] = {"calls": 0, "tokens": 0, "cost": 0.0}
            by_provider[prov]["calls"] += 1
            by_provider[prov]["tokens"] += log.total_tokens
            by_provider[prov]["cost"] += log.total_cost
        
        return CostSummary(
            total_calls=total_calls,
            total_tokens=total_tokens,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_cost=total_cost,
            total_input_cost=total_input_cost,
            total_output_cost=total_output_cost,
            avg_cost_per_call=total_cost / total_calls if total_calls else 0.0,
            avg_tokens_per_call=total_tokens / total_calls if total_calls else 0.0,
            avg_duration_ms=total_duration / total_calls if total_calls else 0.0,
            success_rate=successful / total_calls if total_calls else 0.0,
            by_model=by_model,
            by_agent=by_agent,
            by_chapter=by_chapter,
            by_provider=by_provider,
        )
    
    def get_detailed_logs(
        self,
        task_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        workflow_run_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[LLMUsageLog]:
        """Get detailed log entries for a task/project/run."""
        query = self.db.query(LLMUsageLog)
        
        if task_id:
            query = query.filter(LLMUsageLog.task_id == task_id)
        if project_id:
            query = query.filter(LLMUsageLog.project_id == project_id)
        if workflow_run_id:
            query = query.filter(LLMUsageLog.workflow_run_id == workflow_run_id)
        
        return query.order_by(LLMUsageLog.created_at.desc()).limit(limit).all()
    
    def export_to_dict(self, summary: CostSummary) -> dict:
        """Export a CostSummary to a dictionary for JSON serialization."""
        return {
            "total_calls": summary.total_calls,
            "total_tokens": summary.total_tokens,
            "total_input_tokens": summary.total_input_tokens,
            "total_output_tokens": summary.total_output_tokens,
            "total_cost_usd": round(summary.total_cost, 6),
            "total_input_cost_usd": round(summary.total_input_cost, 6),
            "total_output_cost_usd": round(summary.total_output_cost, 6),
            "avg_cost_per_call_usd": round(summary.avg_cost_per_call, 6),
            "avg_tokens_per_call": round(summary.avg_tokens_per_call, 2),
            "avg_duration_ms": round(summary.avg_duration_ms, 2),
            "success_rate": round(summary.success_rate, 4),
            "by_model": {
                model: {
                    "calls": data["calls"],
                    "tokens": data["tokens"],
                    "input_tokens": data.get("input_tokens", 0),
                    "output_tokens": data.get("output_tokens", 0),
                    "cost_usd": round(data["cost"], 6),
                }
                for model, data in summary.by_model.items()
            },
            "by_agent": {
                agent: {
                    "calls": data["calls"],
                    "tokens": data["tokens"],
                    "cost_usd": round(data["cost"], 6),
                }
                for agent, data in summary.by_agent.items()
            },
            "by_chapter": {
                str(ch): {
                    "calls": data["calls"],
                    "tokens": data["tokens"],
                    "cost_usd": round(data["cost"], 6),
                }
                for ch, data in sorted(summary.by_chapter.items())
            },
            "by_provider": {
                prov: {
                    "calls": data["calls"],
                    "tokens": data["tokens"],
                    "cost_usd": round(data["cost"], 6),
                }
                for prov, data in summary.by_provider.items()
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Convenience function for use in agents
# ─────────────────────────────────────────────────────────────────────────────

_cost_tracker_context: dict = {}


def set_cost_tracker_context(
    project_id: Optional[UUID] = None,
    task_id: Optional[UUID] = None,
    workflow_run_id: Optional[str] = None,
    chapter_number: Optional[int] = None,
):
    """Set the context for cost tracking (call before agent invocations)."""
    global _cost_tracker_context
    _cost_tracker_context = {
        "project_id": project_id,
        "task_id": task_id,
        "workflow_run_id": workflow_run_id,
        "chapter_number": chapter_number,
    }


def get_cost_tracker_context() -> dict:
    """Get the current cost tracking context."""
    return _cost_tracker_context.copy()


def clear_cost_tracker_context():
    """Clear the cost tracking context."""
    global _cost_tracker_context
    _cost_tracker_context = {}

