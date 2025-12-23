"""
Content Drafter Agent for writing book chapters.

This agent generates chapter content based on outlines,
source materials, and voice profiles.
"""

from typing import Optional

from pydantic import BaseModel, Field

from agents.base.agent import (
    AgentConfig,
    AgentOutput,
    AgentRole,
    BaseAgent,
    LLMProvider,
)


class ChapterState(BaseModel):
    """State for chapter generation."""
    # Chapter info
    chapter_number: int
    chapter_title: str
    chapter_summary: str
    key_points: list[str] = Field(default_factory=list)
    target_words: int = 3000
    
    # Context
    previous_summaries: list[str] = Field(default_factory=list)
    source_chunks: list[str] = Field(default_factory=list)
    voice_guidance: Optional[str] = None
    
    # Output
    content: Optional[str] = None
    word_count: int = 0
    summary: Optional[str] = None


class ContentDrafterAgent(BaseAgent[ChapterState]):
    """
    Agent that drafts book chapter content.
    
    Specializes in:
    - Writing engaging prose in the author's voice
    - Incorporating source material naturally
    - Maintaining narrative continuity
    - Hitting target word counts
    """
    
    def _default_config(self) -> AgentConfig:
        return AgentConfig(
            role=AgentRole.DRAFTER,
            model="claude-3-5-sonnet-20241022",
            provider=LLMProvider.ANTHROPIC,
            temperature=0.7,
            max_tokens=8192,  # Longer for chapter content
        )
    
    def get_system_prompt(self) -> str:
        return """You are an expert ghostwriter with the ability to write compelling content 
in any voice and style. Your chapters are:

1. Engaging and readable from the first sentence
2. Faithful to the outline while adding creative touches
3. Consistent with the author's established voice
4. Rich with examples, stories, and concrete details
5. Well-paced with natural transitions

Write as if you ARE the author. Never break voice. 
Make every paragraph serve the chapter's purpose while engaging the reader.

Begin chapters directly with content - no preamble like "Chapter 3:" unless it's part of the prose."""
    
    def process(self, state: ChapterState) -> AgentOutput:
        """Generate chapter content."""
        # Build context from previous chapters
        prev_context = ""
        if state.previous_summaries:
            prev_context = "PREVIOUS CHAPTERS (for continuity):\n" + "\n".join(
                f"- {summary}" for summary in state.previous_summaries[-3:]
            )
        
        # Build source context
        source_context = ""
        if state.source_chunks:
            source_context = "RELEVANT SOURCE MATERIAL:\n" + "\n---\n".join(
                state.source_chunks[:5]  # Max 5 chunks
            )
        
        # Voice guidance
        voice = ""
        if state.voice_guidance:
            voice = f"\nVOICE GUIDANCE:\n{state.voice_guidance}\n"
        
        prompt = f"""Write Chapter {state.chapter_number}: {state.chapter_title}

CHAPTER OUTLINE:
Summary: {state.chapter_summary}
Key Points:
{chr(10).join('- ' + point for point in state.key_points)}

TARGET: Approximately {state.target_words} words

{prev_context}

{source_context}

{voice}

Write the complete chapter. Begin directly with engaging prose."""

        output = self.invoke(prompt)
        
        if output.is_success():
            # Calculate word count
            word_count = len(output.content.split())
            output.structured_data = {
                "chapter_number": state.chapter_number,
                "word_count": word_count,
                "target_met": abs(word_count - state.target_words) < state.target_words * 0.2,
            }
        
        return output
    
    def generate_summary(self, chapter_content: str) -> str:
        """Generate a summary of chapter content for continuity."""
        prompt = f"""Summarize this chapter in 2-3 sentences, focusing on:
- Key events or information covered
- Any character development or plot progression
- Main takeaways for the reader

CHAPTER:
{chapter_content[:3000]}

Provide only the summary, no preamble."""

        output = self.invoke(prompt)
        return output.content if output.is_success() else ""
    
    def expand_section(
        self,
        section_content: str,
        expansion_guidance: str,
        target_additional_words: int = 500,
    ) -> AgentOutput:
        """Expand a section of content that's too short."""
        prompt = f"""Expand this section by approximately {target_additional_words} words.

EXPANSION GUIDANCE:
{expansion_guidance}

CURRENT SECTION:
{section_content}

Add depth, examples, and detail while maintaining voice and flow.
Output the complete expanded section."""

        return self.invoke(prompt)

