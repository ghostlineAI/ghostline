"""
Conversation Logger for the GhostLine agent system.

Captures the entire agentic conversation flow:
- Every prompt sent to LLMs
- Every response received
- Agent-to-agent interactions
- Token usage and costs
- Timing information

Can dump to file for debugging and analysis.
"""

import json
import os
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class MessageRole(str, Enum):
    """Role of the message sender."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    AGENT = "agent"


@dataclass
class ConversationMessage:
    """A single message in the conversation."""
    timestamp: str
    role: str
    agent_name: str
    content: str
    
    # Optional metadata
    tokens_used: int = 0
    cost: float = 0.0
    duration_ms: int = 0
    model: str = ""
    
    # For agent-to-agent communication
    source_agent: Optional[str] = None
    target_agent: Optional[str] = None
    
    # For structured outputs
    structured_data: Optional[dict] = None
    
    def to_dict(self) -> dict:
        result = {
            "timestamp": self.timestamp,
            "role": self.role,
            "agent": self.agent_name,
            "content": self.content[:500] + "..." if len(self.content) > 500 else self.content,  # Truncate for readability
            "full_content_length": len(self.content),
        }
        if self.tokens_used:
            result["tokens"] = self.tokens_used
        if self.cost:
            result["cost"] = f"${self.cost:.6f}"
        if self.duration_ms:
            result["duration_ms"] = self.duration_ms
        if self.model:
            result["model"] = self.model
        if self.source_agent:
            result["from"] = self.source_agent
        if self.target_agent:
            result["to"] = self.target_agent
        if self.structured_data:
            result["structured"] = self.structured_data
        return result


@dataclass
class ConversationSession:
    """A complete conversation session (one workflow run)."""
    session_id: str
    workflow_type: str  # e.g., "book_generation", "outline", "chapter"
    started_at: str
    ended_at: Optional[str] = None
    
    # Messages in order
    messages: list = field(default_factory=list)
    
    # Aggregated stats
    total_tokens: int = 0
    total_cost: float = 0.0
    total_duration_ms: int = 0
    agent_call_counts: dict = field(default_factory=dict)
    
    # Status
    status: str = "running"  # running, completed, failed
    error: Optional[str] = None
    
    def add_message(self, msg: ConversationMessage):
        """Add a message to the session."""
        self.messages.append(msg)
        self.total_tokens += msg.tokens_used
        self.total_cost += msg.cost
        self.total_duration_ms += msg.duration_ms
        
        # Track agent calls
        if msg.agent_name not in self.agent_call_counts:
            self.agent_call_counts[msg.agent_name] = 0
        self.agent_call_counts[msg.agent_name] += 1
    
    def complete(self, status: str = "completed", error: Optional[str] = None):
        """Mark the session as complete."""
        self.ended_at = datetime.utcnow().isoformat()
        self.status = status
        self.error = error
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "workflow_type": self.workflow_type,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status,
            "error": self.error,
            "stats": {
                "total_tokens": self.total_tokens,
                "total_cost": f"${self.total_cost:.4f}",
                "total_duration_ms": self.total_duration_ms,
                "total_duration_sec": round(self.total_duration_ms / 1000, 2),
                "message_count": len(self.messages),
                "agent_calls": self.agent_call_counts,
            },
            "messages": [m.to_dict() for m in self.messages],
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


class ConversationLogger:
    """
    Singleton logger for capturing agent conversations.
    
    Usage:
        logger = ConversationLogger.get_instance()
        session = logger.start_session("book_generation", "workflow-123")
        
        # In agents:
        logger.log_prompt("OutlinePlanner", "Create an outline...", model="claude-3")
        logger.log_response("OutlinePlanner", "Here's the outline...", tokens=500, cost=0.01)
        
        # When done:
        logger.end_session()
        logger.dump_to_file("conversation.json")
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._current_session: Optional[ConversationSession] = None
        self._sessions: list[ConversationSession] = []
        self._log_dir = Path("logs/conversations")
        self._log_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_instance(cls) -> "ConversationLogger":
        """Get the singleton instance."""
        return cls()
    
    def start_session(
        self,
        workflow_type: str,
        session_id: str,
    ) -> ConversationSession:
        """Start a new conversation session."""
        if self._current_session and self._current_session.status == "running":
            # Auto-complete previous session
            self._current_session.complete(status="interrupted")
        
        self._current_session = ConversationSession(
            session_id=session_id,
            workflow_type=workflow_type,
            started_at=datetime.utcnow().isoformat(),
        )
        
        logger.info(f"📝 Started conversation session: {session_id} ({workflow_type})")
        return self._current_session
    
    def get_current_session(self) -> Optional[ConversationSession]:
        """Get the current session."""
        return self._current_session
    
    def log_prompt(
        self,
        agent_name: str,
        prompt: str,
        model: str = "",
        context: str = "",
        target_agent: Optional[str] = None,
    ):
        """Log a prompt being sent to an LLM."""
        if not self._current_session:
            self.start_session("unknown", f"auto-{datetime.utcnow().timestamp()}")
        
        content = prompt
        if context:
            content = f"[Context]: {context[:200]}...\n\n[Prompt]: {prompt}"
        
        msg = ConversationMessage(
            timestamp=datetime.utcnow().isoformat(),
            role=MessageRole.USER.value,
            agent_name=agent_name,
            content=content,
            model=model,
            target_agent=target_agent,
        )
        
        self._current_session.add_message(msg)
        logger.info(f"📤 [{agent_name}] Prompt sent ({len(prompt)} chars)")
    
    def log_response(
        self,
        agent_name: str,
        response: str,
        tokens_used: int = 0,
        cost: float = 0.0,
        duration_ms: int = 0,
        model: str = "",
        structured_data: Optional[dict] = None,
        source_agent: Optional[str] = None,
    ):
        """Log a response received from an LLM."""
        if not self._current_session:
            self.start_session("unknown", f"auto-{datetime.utcnow().timestamp()}")
        
        msg = ConversationMessage(
            timestamp=datetime.utcnow().isoformat(),
            role=MessageRole.ASSISTANT.value,
            agent_name=agent_name,
            content=response,
            tokens_used=tokens_used,
            cost=cost,
            duration_ms=duration_ms,
            model=model,
            structured_data=structured_data,
            source_agent=source_agent,
        )
        
        self._current_session.add_message(msg)
        logger.info(f"📥 [{agent_name}] Response received ({tokens_used} tokens, ${cost:.4f})")
    
    def log_agent_handoff(
        self,
        from_agent: str,
        to_agent: str,
        message: str = "",
    ):
        """Log when one agent hands off to another."""
        if not self._current_session:
            return
        
        msg = ConversationMessage(
            timestamp=datetime.utcnow().isoformat(),
            role=MessageRole.AGENT.value,
            agent_name=f"{from_agent}→{to_agent}",
            content=message or f"Handoff from {from_agent} to {to_agent}",
            source_agent=from_agent,
            target_agent=to_agent,
        )
        
        self._current_session.add_message(msg)
        logger.info(f"🔄 [{from_agent}] → [{to_agent}] {message[:50] if message else 'handoff'}")
    
    def log_system(self, agent_name: str, message: str):
        """Log a system message (not an LLM call)."""
        if not self._current_session:
            return
        
        msg = ConversationMessage(
            timestamp=datetime.utcnow().isoformat(),
            role=MessageRole.SYSTEM.value,
            agent_name=agent_name,
            content=message,
        )
        
        self._current_session.add_message(msg)
        logger.info(f"⚙️ [{agent_name}] {message}")
    
    def end_session(
        self,
        status: str = "completed",
        error: Optional[str] = None,
    ) -> Optional[ConversationSession]:
        """End the current session."""
        if not self._current_session:
            return None
        
        self._current_session.complete(status, error)
        self._sessions.append(self._current_session)
        
        session = self._current_session
        
        logger.info(f"📝 Session ended: {session.session_id}")
        logger.info(f"   Status: {status}")
        logger.info(f"   Total tokens: {session.total_tokens}")
        logger.info(f"   Total cost: ${session.total_cost:.4f}")
        logger.info(f"   Duration: {session.total_duration_ms/1000:.2f}s")
        logger.info(f"   Messages: {len(session.messages)}")
        
        self._current_session = None
        return session
    
    def dump_to_file(
        self,
        filename: Optional[str] = None,
        session: Optional[ConversationSession] = None,
    ) -> Path:
        """Dump a session to a JSON file."""
        session = session or self._current_session or (self._sessions[-1] if self._sessions else None)
        
        if not session:
            raise ValueError("No session to dump")
        
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{session.workflow_type}_{session.session_id}_{timestamp}.json"
        
        filepath = self._log_dir / filename
        
        with open(filepath, "w") as f:
            f.write(session.to_json(indent=2))
        
        logger.info(f"💾 Conversation saved to: {filepath}")
        return filepath
    
    def dump_all_sessions(self, filename: str = "all_sessions.json") -> Path:
        """Dump all sessions to a single file."""
        filepath = self._log_dir / filename
        
        data = {
            "sessions": [s.to_dict() for s in self._sessions],
            "total_sessions": len(self._sessions),
            "total_tokens": sum(s.total_tokens for s in self._sessions),
            "total_cost": sum(s.total_cost for s in self._sessions),
        }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"💾 All sessions saved to: {filepath}")
        return filepath
    
    def get_summary(self) -> dict:
        """Get a summary of all sessions."""
        return {
            "current_session": self._current_session.session_id if self._current_session else None,
            "total_sessions": len(self._sessions),
            "total_tokens": sum(s.total_tokens for s in self._sessions),
            "total_cost": sum(s.total_cost for s in self._sessions),
        }
    
    def print_current_session(self):
        """Print the current session to console."""
        if not self._current_session:
            print("No active session")
            return
        
        print("\n" + "=" * 60)
        print(f"Session: {self._current_session.session_id}")
        print(f"Type: {self._current_session.workflow_type}")
        print(f"Status: {self._current_session.status}")
        print("=" * 60)
        
        for msg in self._current_session.messages:
            print(f"\n[{msg.timestamp}] {msg.role.upper()} - {msg.agent_name}")
            if msg.tokens_used:
                print(f"   Tokens: {msg.tokens_used}, Cost: ${msg.cost:.4f}")
            print(f"   {msg.content[:200]}...")
        
        print("\n" + "=" * 60)
        print(f"Total: {self._current_session.total_tokens} tokens, ${self._current_session.total_cost:.4f}")
        print("=" * 60 + "\n")


# Global convenience function
def get_conversation_logger() -> ConversationLogger:
    """Get the global conversation logger instance."""
    return ConversationLogger.get_instance()

