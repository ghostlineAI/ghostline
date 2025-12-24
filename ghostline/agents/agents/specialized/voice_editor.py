"""
Voice Editor Agent for ensuring style consistency.

This agent analyzes and adjusts content to match the author's
voice profile and writing style.
"""

import json
import re
from typing import Optional

from pydantic import BaseModel, Field

from agents.base.agent import (
    AgentConfig,
    AgentOutput,
    AgentRole,
    BaseAgent,
    ConversationAgent,
    LLMProvider,
)


class VoiceState(BaseModel):
    """State for voice editing."""
    content: str
    voice_profile: Optional[dict] = None
    writing_samples: list[str] = Field(default_factory=list)
    
    # Analysis results
    voice_score: Optional[float] = None
    issues_found: list[str] = Field(default_factory=list)
    edited_content: Optional[str] = None


class VoiceEditorAgent(BaseAgent[VoiceState]):
    """
    Agent that ensures content matches the author's voice.
    
    Specializes in:
    - Analyzing writing style characteristics
    - Identifying voice inconsistencies
    - Rewriting content to match voice profile
    - Preserving meaning while changing style
    """
    
    def _default_config(self) -> AgentConfig:
        return AgentConfig(
            role=AgentRole.EDITOR,
            model="claude-sonnet-4-20250514",
            provider=LLMProvider.ANTHROPIC,
            temperature=0.5,  # Lower for consistent editing
            max_tokens=8192,
        )
    
    def get_system_prompt(self) -> str:
        return """You are an expert voice editor and literary chameleon. You can:

1. Analyze writing samples to identify distinctive voice characteristics
2. Detect when content doesn't match an established voice
3. Rewrite content to match a specific voice while preserving meaning
4. Identify specific elements that break voice consistency

When analyzing voice, consider:
- Sentence length and structure
- Vocabulary level and word choices
- Tone and register
- Use of metaphors and figurative language
- Paragraph structure and pacing
- Common phrases or linguistic patterns

Your edits should be invisible - the result should read as if the original author wrote it."""
    
    def process(self, state: VoiceState) -> AgentOutput:
        """Analyze and edit content for voice consistency."""
        if not state.voice_profile and not state.writing_samples:
            return AgentOutput(
                content="No voice profile or writing samples provided.",
                error="Missing voice reference",
            )
        
        # First analyze, then edit if needed
        analysis = self.analyze_voice_match(state)
        
        if analysis.structured_data and analysis.structured_data.get("score", 1.0) >= 0.85:
            # Voice is already good
            return analysis
        
        # Needs editing
        return self.edit_for_voice(state)
    
    def analyze_voice_match(self, state: VoiceState) -> AgentOutput:
        """Analyze how well content matches the target voice."""
        voice_ref = ""
        if state.voice_profile:
            voice_ref = f"VOICE PROFILE:\n{json.dumps(state.voice_profile, indent=2)}"
        elif state.writing_samples:
            voice_ref = "WRITING SAMPLES:\n" + "\n---\n".join(state.writing_samples[:3])
        
        prompt = f"""Analyze how well this content matches the target voice.

{voice_ref}

CONTENT TO ANALYZE:
{state.content[:4000]}

Provide your analysis as JSON:
{{
    "score": 0.0-1.0 (1.0 = perfect match),
    "strengths": ["what matches well"],
    "issues": ["specific mismatches"],
    "recommendations": ["specific changes needed"]
}}

Be precise about specific words, phrases, or patterns that don't match."""

        output = self.invoke(prompt)
        
        if output.is_success():
            analysis = self._parse_json(output.content)
            output.structured_data = analysis
            output.confidence = analysis.get("score", 0.5)
        
        return output
    
    def edit_for_voice(self, state: VoiceState) -> AgentOutput:
        """Edit content to match the target voice."""
        voice_ref = ""
        if state.voice_profile:
            voice_ref = f"VOICE PROFILE:\n{json.dumps(state.voice_profile, indent=2)}"
        elif state.writing_samples:
            voice_ref = "WRITING SAMPLES (match this style):\n" + "\n---\n".join(state.writing_samples[:2])
        
        prompt = f"""Rewrite this content to match the target voice while preserving all meaning.

{voice_ref}

CONTENT TO REWRITE:
{state.content}

Output only the rewritten content. No explanations or preamble."""

        output = self.invoke(prompt)
        
        if output.is_success():
            output.structured_data = {
                "original_length": len(state.content.split()),
                "edited_length": len(output.content.split()),
            }
        
        return output
    
    def create_voice_profile(self, writing_samples: list[str]) -> AgentOutput:
        """Create a voice profile from writing samples."""
        samples = "\n\n---\n\n".join(writing_samples[:5])
        
        prompt = f"""Analyze these writing samples and create a detailed voice profile.

WRITING SAMPLES:
{samples}

Create a voice profile as JSON:
{{
    "style_description": "2-3 paragraphs describing the distinctive voice",
    "sentence_patterns": {{
        "avg_length": "short/medium/long",
        "structure": "simple/compound/complex/varied",
        "rhythm": "description of sentence rhythm"
    }},
    "vocabulary": {{
        "level": "simple/moderate/sophisticated",
        "distinctive_words": ["list", "of", "characteristic", "words"],
        "avoidances": ["words/patterns", "the", "author", "avoids"]
    }},
    "tone": {{
        "primary": "main tone",
        "secondary": ["other", "tonal", "elements"]
    }},
    "distinctive_features": ["unique", "stylistic", "markers"],
    "examples": ["characteristic phrases from samples"]
}}"""

        output = self.invoke(prompt)
        
        if output.is_success():
            profile = self._parse_json(output.content)
            output.structured_data = profile
        
        return output
    
    def _parse_json(self, content: str) -> dict:
        """Parse JSON from response."""
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r'^```\w*\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {}

