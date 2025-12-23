"""
Specialized agents for ghostwriting tasks.

Each agent has a specific role in the book generation pipeline.
"""

from agents.specialized.outline_planner import OutlinePlannerAgent
from agents.specialized.content_drafter import ContentDrafterAgent
from agents.specialized.voice_editor import VoiceEditorAgent
from agents.specialized.fact_checker import FactCheckerAgent
from agents.specialized.cohesion_analyst import CohesionAnalystAgent

__all__ = [
    "OutlinePlannerAgent",
    "ContentDrafterAgent",
    "VoiceEditorAgent",
    "FactCheckerAgent",
    "CohesionAnalystAgent",
]

