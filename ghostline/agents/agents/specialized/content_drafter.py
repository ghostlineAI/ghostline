"""
Content Drafter Agent for writing book chapters.

This agent generates chapter content based on outlines,
source materials, and voice profiles.

GROUNDING REQUIREMENT: All content must be grounded in source materials.
Each claim or fact should reference the source chunk it came from.
"""

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field

from agents.base.agent import (
    AgentConfig,
    AgentOutput,
    AgentRole,
    BaseAgent,
    LLMProvider,
)


@dataclass
class SourceChunk:
    """A source chunk with citation metadata for grounding."""
    content: str
    citation: str  # e.g., "[Chapter 1, p.5]" or "[mental_health.pdf]"
    similarity_score: float = 0.0
    
    def to_context_block(self) -> str:
        """Format as a context block for the prompt."""
        return f"---\n{self.citation}\n{self.content}\n---"


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
    source_chunks: list[str] = Field(default_factory=list)  # Legacy: plain text chunks
    source_chunks_with_citations: list[dict] = Field(default_factory=list)  # New: {"content": str, "citation": str}
    voice_guidance: Optional[str] = None
    
    # Grounding requirement (0.0 = no requirement, 1.0 = all content must be grounded)
    grounding_requirement: float = 0.8
    
    # Output
    content: Optional[str] = None
    word_count: int = 0
    summary: Optional[str] = None
    citations_used: list[str] = Field(default_factory=list)


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
            model="claude-sonnet-4-20250514",
            provider=LLMProvider.ANTHROPIC,
            # Lower temperature for grounded, non-hallucinated writing.
            temperature=0.25,
            max_tokens=8192,  # Longer for chapter content
        )
    
    def get_system_prompt(self) -> str:
        return """You are an expert ghostwriter with the ability to write compelling content 
in any voice and style. Your chapters are:

1. Engaging and readable from the first sentence
2. Faithful to the outline WITHOUT inventing new events, scenes, or autobiographical moments
3. Consistent with the author's established voice
4. Rich with examples, stories, and concrete details
5. Well-paced with natural transitions
6. GROUNDED in source materials - every significant claim must come from the provided sources

CRITICAL HUMANNESS (do not sound like AI):
- Do NOT spam headings. Use at most 3 section headings using '##' for the entire chapter.
- Prefer longer paragraphs and natural transitions over constant section breaks.
- Do NOT introduce named "frameworks" or acronym systems (e.g., "FOUNDATION Framework", "TOOLS framework").
- Avoid formulaic patterns like "Stage 1 / Stage 2 / Stage 3" unless the source uses them.
- Avoid generic motivational/coach language. Write like a real person processing real notes.

FIDELITY TO THE AUTHOR'S NOTES:
- Do NOT invent personal stories (e.g., "The morning I realized...") unless that exact moment is present in the sources.
- If you need a vignette, it must be explicitly grounded as an example drawn from the notes.
- It's OK to add brief connective tissue, but it must remain non-specific and non-factual.
- Every substantive paragraph (≥20 words) MUST include at least one [citation: ...] marker. If you cannot cite it, delete it.
- CITED QUOTES MUST APPEAR IN THE PROSE:
  For every citation you add, you MUST include the quoted text in the actual paragraph (verbatim) in quotation marks,
  ideally immediately before the citation marker. This prevents “hand-wavy” citations.

  Example:
  ... "Taking a step back isn't a delay...it's an integral piece of allowing myself to be most productive for work"
  [citation: mentalhealth1.pdf - "Taking a step back isn't a delay...it's an integral piece of allowing myself to be most productive for work"]

OUTPUT FORMAT CONSTRAINT (VERY IMPORTANT):
- Each substantive paragraph should follow this pattern:
  1) A direct quote in quotation marks (8-25 words) copied from the QUOTE BANK / sources
  2) The matching [citation: ...] marker (same quote)
  3) 1–2 short sentences of commentary that stay close to the quote (no new facts, no new scenes)
- Keep paragraphs tight (prefer 60–110 words total). If you need more, add another quote-paragraph instead of expanding.

STRUCTURAL VARIETY (CRITICAL):
Avoid making every chapter follow the same structural pattern. Vary your approach:
- NOT every chapter should use an acronym framework (like "CALM", "SHIFT", "PEACE")
- Use different organizational strategies for different chapters:
  * Narrative storytelling (journey/transformation arc)
  * Problem-solution format
  * Thematic exploration with examples
  * Practical how-to with action steps
  * Reflective/journal-style introspection
  * Compare-and-contrast perspectives
  * Case study or scenario-based
- Use acronym frameworks SPARINGLY - at most 1 per book, not per chapter
- Let the content's natural structure emerge rather than forcing frameworks

GROUNDING RULES:
- You MUST base your content on the provided source materials
- When making factual claims, use the STANDARDIZED CITATION FORMAT:
  [citation: filename.ext - "exact or paraphrased quote"]
  
  Examples:
  - [citation: mentalhealth1.pdf - "Taking a step back isn't a delay"]
  - [citation: notes.txt - "meditation helps me process difficult emotions"]
  
- Do NOT make up facts, statistics, or claims not supported by sources
- If the sources don't cover something in the outline, note it as needing additional research
- You may synthesize and rephrase, but the core information must come from sources
- The quote inside the citation MUST be copied VERBATIM from the provided source blocks above (no paraphrasing inside the quoted text).
  Keep quotes short (8-25 words) so they can be verified reliably.

Write as if you ARE the author. Never break voice. 
Make every paragraph serve the chapter's purpose while engaging the reader.

Begin chapters directly with content - no preamble like "Chapter 3:" unless it's part of the prose."""
    
    def process(self, state: ChapterState) -> AgentOutput:
        """Generate chapter content with grounded sources."""
        # Build context from previous chapters
        prev_context = ""
        if state.previous_summaries:
            prev_context = "PREVIOUS CHAPTERS (for continuity):\n" + "\n".join(
                f"- {summary}" for summary in state.previous_summaries[-3:]
            )
        
        # Build source context with citations (prefer new format)
        source_context = ""
        citations_available = []
        quote_bank_block = ""
        
        if state.source_chunks_with_citations:
            # New format with citations
            chunks_text = []
            for chunk_data in state.source_chunks_with_citations[:15]:  # Max 15 chunks
                citation = chunk_data.get("citation", "[Unknown Source]")
                content = chunk_data.get("content", "")
                citations_available.append(citation)
                chunks_text.append(f"---\n{citation}\n{content}\n---")
            source_context = "GROUNDED SOURCE MATERIAL (use these to support your claims):\n" + "\n".join(chunks_text)

            # Build a deterministic quote bank from the provided chunks so the model can
            # copy verbatim text into citations (improves verifiability).
            import re
            quotes: list[tuple[str, str]] = []
            seen: set[str] = set()
            for chunk_data in state.source_chunks_with_citations[:15]:
                citation = str(chunk_data.get("citation", "Unknown Source"))
                raw = str(chunk_data.get("content", "") or "")
                # Prefer line-based snippets (these notes are often line-broken)
                for line in re.split(r"[\r\n]+", raw):
                    q = line.strip()
                    if not q:
                        continue
                    # Avoid quotes that would break JSON/citation formatting
                    if '"' in q:
                        continue
                    w = q.split()
                    if len(w) < 8 or len(w) > 25:
                        continue
                    key = q.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    quotes.append((citation, q))
                    if len(quotes) >= 25:
                        break
                if len(quotes) >= 25:
                    break

            if quotes:
                quote_lines = []
                for i, (cit, q) in enumerate(quotes, 1):
                    quote_lines.append(f'{i}. ({cit}) {q}')
                quote_bank_block = (
                    "QUOTE BANK (COPY VERBATIM INTO CITATIONS):\n"
                    "- Every [citation: ... - \"...\"] quote MUST be copied EXACTLY from one of these lines.\n"
                    "- Do NOT invent quotes and do NOT paraphrase inside the quoted text.\n"
                    + "\n".join(quote_lines)
                )
        elif state.source_chunks:
            # Legacy format (plain text)
            source_context = "RELEVANT SOURCE MATERIAL:\n" + "\n---\n".join(
                state.source_chunks[:5]  # Max 5 chunks
            )
        
        # Voice guidance
        voice = ""
        if state.voice_guidance:
            voice = f"\nVOICE GUIDANCE:\n{state.voice_guidance}\n"
        
        # Grounding instructions
        grounding_note = ""
        if state.grounding_requirement > 0:
            grounding_note = f"""
GROUNDING REQUIREMENT: {state.grounding_requirement:.0%} of factual claims must be supported by the source material above.
- Use the STANDARDIZED CITATION FORMAT: [citation: filename.ext - "quote from source"]
- Available source files: {', '.join(set(c.split(' - ')[0].replace('[citation: ', '').replace('[', '') for c in citations_available[:5]))}
- ALWAYS include the actual quote from the source material to enable verification
- Example: [citation: mentalhealth1.pdf - "Taking a step back isn't a delay...it's an integral piece"]
"""
        
        # Structure variety hint
        structure_hint = self._get_structure_hint(state.chapter_number)
        
        prompt = f"""Write Chapter {state.chapter_number}: {state.chapter_title}

CHAPTER OUTLINE:
Summary: {state.chapter_summary}
Key Points:
{chr(10).join('- ' + point for point in state.key_points)}

TARGET: Approximately {state.target_words} words

{structure_hint}

{prev_context}

{source_context}

{quote_bank_block}

{grounding_note}

{voice}

Write the complete chapter. Begin directly with engaging prose. Include [citation] markers where appropriate."""

        output = self.invoke(prompt)
        
        if output.is_success():
            # Calculate word count
            word_count = len(output.content.split())
            
            # Extract citations used
            import re
            citations_used = re.findall(r'\[([^\]]+)\]', output.content)
            citations_used = list(set(citations_used))
            
            # Calculate grounding score
            citation_count = len(citations_used)
            sentences = len(re.split(r'[.!?]+', output.content))
            grounding_score = min(1.0, citation_count / max(sentences / 5, 1))  # Rough heuristic
            
            output.structured_data = {
                "chapter_number": state.chapter_number,
                "word_count": word_count,
                "target_met": abs(word_count - state.target_words) < state.target_words * 0.2,
                "citations_used": citations_used,
                "grounding_score": grounding_score,
                "grounding_met": grounding_score >= state.grounding_requirement,
            }
        
        return output
    
    def _get_structure_hint(self, chapter_number: int) -> str:
        """
        Generate a structural variety hint based on chapter number.
        
        This rotates through different structural approaches to avoid
        every chapter having the same format (e.g., all acronym frameworks).
        """
        structures = [
            ("narrative", "Use a NARRATIVE JOURNEY structure - open with a personal story or scenario, "
             "explore the challenges faced, and end with resolution/growth. Flow naturally without rigid sections."),
            ("practical", "Use a PRACTICAL HOW-TO structure - briefly introduce the concept, then focus on "
             "actionable steps, tips, and concrete examples. Use numbered or bulleted action items sparingly."),
            ("reflective", "Use a REFLECTIVE EXPLORATION structure - take a thoughtful, introspective approach. "
             "Use questions, personal insights, and invite the reader to consider their own experience."),
            ("thematic", "Use a THEMATIC EXPLORATION structure - organize around 2-3 interconnected themes. "
             "Weave examples and stories throughout. Avoid rigid frameworks."),
            ("problem-solution", "Use a PROBLEM-SOLUTION structure - clearly define the challenge, explore why "
             "it matters, then present solutions with evidence from the sources."),
        ]
        
        # Rotate through structures based on chapter number
        idx = (chapter_number - 1) % len(structures)
        structure_name, structure_guidance = structures[idx]
        
        return f"""STRUCTURAL APPROACH FOR THIS CHAPTER:
{structure_guidance}

IMPORTANT: Do NOT use acronym frameworks (like CALM, SHIFT, PEACE, etc.). Let the content flow naturally with this structure."""
    
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

