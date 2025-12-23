"""
Generation Service for AI-powered content creation.

This service coordinates the LLM calls for generating:
- Book outlines from source materials
- Chapter content based on outlines and voice profiles
- Chapter revisions with style matching
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.book_outline import BookOutline
from app.models.chapter import Chapter
from app.models.content_chunk import ContentChunk
from app.models.project import Project
from app.models.source_material import SourceMaterial
from app.models.voice_profile import VoiceProfile
from app.services.llm import LLMResponse, LLMService, get_llm_service
from app.services.embeddings import EmbeddingService, get_embedding_service


@dataclass
class OutlineGenerationResult:
    """Result from outline generation."""
    outline_structure: dict
    chapter_count: int
    estimated_word_count: int
    llm_response: LLMResponse


@dataclass
class ChapterGenerationResult:
    """Result from chapter generation."""
    content: str
    word_count: int
    summary: str
    llm_response: LLMResponse


@dataclass
class VoiceAnalysisResult:
    """Result from voice profile analysis."""
    embedding: list[float]
    style_description: str
    key_phrases: list[str]
    avg_sentence_length: float
    vocabulary_level: str
    llm_response: LLMResponse


class GenerationService:
    """
    Service for AI-powered content generation.
    
    Coordinates between LLM service, embeddings, and database models
    to generate high-quality ghostwritten content.
    """
    
    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.llm = llm_service or get_llm_service()
        self.embeddings = embedding_service or get_embedding_service()
    
    def generate_outline(
        self,
        project: Project,
        source_chunks: list[ContentChunk],
        voice_profile: Optional[VoiceProfile] = None,
        target_chapters: int = 10,
    ) -> OutlineGenerationResult:
        """
        Generate a book outline from source materials.
        
        Args:
            project: The project to generate outline for
            source_chunks: Chunked content from source materials
            voice_profile: Optional voice profile to match
            target_chapters: Target number of chapters
            
        Returns:
            OutlineGenerationResult with structured outline
        """
        # Build context from source chunks
        source_context = self._build_source_context(source_chunks, max_tokens=6000)
        
        # Build voice guidance if available
        voice_guidance = ""
        if voice_profile:
            voice_guidance = f"""
Voice Profile Guidance:
- Style: {voice_profile.style_description or 'Not specified'}
- Tone: Match the author's natural voice and vocabulary
"""
        
        system_prompt = """You are an expert book outline architect. Your task is to create 
compelling, well-structured book outlines that capture the essence of the source material
while maintaining narrative flow and reader engagement.

Output your response as a structured JSON object with the following format:
{
    "title": "Book Title",
    "premise": "One paragraph describing the book's central premise",
    "chapters": [
        {
            "number": 1,
            "title": "Chapter Title",
            "summary": "2-3 sentence summary of chapter content",
            "key_points": ["point 1", "point 2", "point 3"],
            "estimated_words": 3000
        }
    ],
    "themes": ["theme 1", "theme 2"],
    "target_audience": "Description of ideal reader"
}"""

        prompt = f"""Based on the following source material, create a comprehensive book outline
with {target_chapters} chapters.

Project Title: {project.title}
Project Description: {project.description or 'Not provided'}

{voice_guidance}

SOURCE MATERIAL:
{source_context}

Generate a detailed, engaging book outline that:
1. Captures the key ideas and information from the source material
2. Organizes content logically with clear chapter progression
3. Maintains reader interest throughout
4. Balances depth with accessibility

Respond with only the JSON structure, no additional text."""

        response = self.llm.generate_quality(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=4000,
            temperature=0.7,
        )
        
        # Parse the outline structure from response
        outline_structure = self._parse_json_response(response.content)
        
        chapter_count = len(outline_structure.get('chapters', []))
        estimated_words = sum(
            ch.get('estimated_words', 3000) 
            for ch in outline_structure.get('chapters', [])
        )
        
        return OutlineGenerationResult(
            outline_structure=outline_structure,
            chapter_count=chapter_count,
            estimated_word_count=estimated_words,
            llm_response=response,
        )
    
    def generate_chapter(
        self,
        chapter_outline: dict,
        previous_summaries: list[str],
        relevant_chunks: list[ContentChunk],
        voice_profile: Optional[VoiceProfile] = None,
        target_words: int = 3000,
    ) -> ChapterGenerationResult:
        """
        Generate a single chapter based on outline and context.
        
        Args:
            chapter_outline: The outline for this specific chapter
            previous_summaries: Summaries of previous chapters for continuity
            relevant_chunks: Source material chunks relevant to this chapter
            voice_profile: Voice profile to match
            target_words: Target word count for the chapter
            
        Returns:
            ChapterGenerationResult with chapter content
        """
        # Build context
        source_context = self._build_chunk_context(relevant_chunks, max_tokens=4000)
        
        previous_context = ""
        if previous_summaries:
            previous_context = "Previous chapter summaries:\n" + "\n".join(
                f"- {summary}" for summary in previous_summaries[-3:]  # Last 3 chapters
            )
        
        voice_guidance = ""
        if voice_profile and voice_profile.style_description:
            voice_guidance = f"""
VOICE GUIDELINES:
{voice_profile.style_description}
Match the author's natural vocabulary, sentence structure, and tone.
"""

        system_prompt = """You are an expert ghostwriter with the ability to write in any voice 
and style. Your task is to write compelling, engaging book chapters that:
1. Follow the provided outline precisely
2. Match the author's voice and style
3. Maintain continuity with previous chapters
4. Incorporate relevant source material naturally
5. Engage readers with vivid prose and clear explanations"""

        prompt = f"""Write Chapter {chapter_outline.get('number', '')}: {chapter_outline.get('title', '')}

CHAPTER OUTLINE:
Summary: {chapter_outline.get('summary', '')}
Key Points to Cover:
{chr(10).join('- ' + point for point in chapter_outline.get('key_points', []))}

{previous_context}

RELEVANT SOURCE MATERIAL:
{source_context}

{voice_guidance}

TARGET: Write approximately {target_words} words.

Write the complete chapter content. Begin directly with the chapter text, no preamble."""

        response = self.llm.generate_quality(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=min(target_words * 2, 8000),  # Roughly 2 tokens per word
            temperature=0.7,
        )
        
        content = response.content.strip()
        word_count = len(content.split())
        
        # Generate a summary for continuity
        summary = self._generate_summary(content)
        
        return ChapterGenerationResult(
            content=content,
            word_count=word_count,
            summary=summary,
            llm_response=response,
        )
    
    def analyze_voice(
        self,
        writing_samples: list[str],
    ) -> VoiceAnalysisResult:
        """
        Analyze writing samples to create a voice profile.
        
        Args:
            writing_samples: Text samples from the author
            
        Returns:
            VoiceAnalysisResult with voice characteristics
        """
        # Combine samples for analysis
        combined_text = "\n\n---\n\n".join(writing_samples[:5])  # Max 5 samples
        
        # Generate embedding for the combined text
        embedding_result = self.embeddings.embed_text(combined_text)
        
        # Analyze style with LLM
        system_prompt = """You are an expert literary analyst specializing in voice and style analysis.
Analyze writing samples to identify distinctive characteristics."""

        prompt = f"""Analyze the following writing samples and provide a detailed voice profile.

WRITING SAMPLES:
{combined_text}

Provide your analysis as a JSON object:
{{
    "style_description": "2-3 paragraph description of the author's distinctive voice",
    "key_phrases": ["list", "of", "characteristic", "phrases", "or", "expressions"],
    "avg_sentence_length": "short/medium/long",
    "vocabulary_level": "simple/moderate/sophisticated",
    "tone": "description of overall tone",
    "distinctive_features": ["list", "of", "unique", "stylistic", "features"]
}}"""

        response = self.llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=2000,
            temperature=0.5,
        )
        
        # Parse response
        analysis = self._parse_json_response(response.content)
        
        # Calculate actual average sentence length
        import re
        sentences = re.split(r'[.!?]+', combined_text)
        avg_words = sum(len(s.split()) for s in sentences if s.strip()) / max(len(sentences), 1)
        
        return VoiceAnalysisResult(
            embedding=embedding_result.embedding,
            style_description=analysis.get('style_description', ''),
            key_phrases=analysis.get('key_phrases', []),
            avg_sentence_length=avg_words,
            vocabulary_level=analysis.get('vocabulary_level', 'moderate'),
            llm_response=response,
        )
    
    def revise_chapter(
        self,
        chapter_content: str,
        revision_instructions: str,
        voice_profile: Optional[VoiceProfile] = None,
    ) -> ChapterGenerationResult:
        """
        Revise a chapter based on feedback or instructions.
        
        Args:
            chapter_content: The current chapter content
            revision_instructions: What changes to make
            voice_profile: Voice profile to maintain
            
        Returns:
            ChapterGenerationResult with revised content
        """
        voice_guidance = ""
        if voice_profile and voice_profile.style_description:
            voice_guidance = f"Maintain this voice: {voice_profile.style_description}"
        
        system_prompt = """You are an expert editor and ghostwriter. Revise the provided chapter
according to the instructions while maintaining the original voice and quality."""

        prompt = f"""Revise the following chapter according to these instructions:

REVISION INSTRUCTIONS:
{revision_instructions}

{voice_guidance}

CURRENT CHAPTER:
{chapter_content}

Provide the complete revised chapter. Make only the requested changes."""

        response = self.llm.generate_quality(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=8000,
            temperature=0.5,
        )
        
        content = response.content.strip()
        word_count = len(content.split())
        summary = self._generate_summary(content)
        
        return ChapterGenerationResult(
            content=content,
            word_count=word_count,
            summary=summary,
            llm_response=response,
        )
    
    def _build_source_context(
        self,
        chunks: list[ContentChunk],
        max_tokens: int = 6000,
    ) -> str:
        """Build context string from source chunks, respecting token limits."""
        context_parts = []
        estimated_tokens = 0
        
        for chunk in chunks:
            chunk_text = chunk.content or ""
            chunk_tokens = len(chunk_text.split()) * 1.3  # Rough token estimate
            
            if estimated_tokens + chunk_tokens > max_tokens:
                break
            
            context_parts.append(chunk_text)
            estimated_tokens += chunk_tokens
        
        return "\n\n".join(context_parts)
    
    def _build_chunk_context(
        self,
        chunks: list[ContentChunk],
        max_tokens: int = 4000,
    ) -> str:
        """Build context from content chunks."""
        return self._build_source_context(chunks, max_tokens)
    
    def _generate_summary(self, content: str, max_words: int = 100) -> str:
        """Generate a brief summary of content."""
        if len(content.split()) <= max_words:
            return content
        
        response = self.llm.generate_fast(
            prompt=f"Summarize this text in {max_words} words or less:\n\n{content[:4000]}",
            system_prompt="You are a concise summarizer. Provide only the summary, no preamble.",
            max_tokens=200,
            temperature=0.3,
        )
        return response.content.strip()
    
    def _parse_json_response(self, content: str) -> dict:
        """Parse JSON from LLM response, handling common issues."""
        import json
        import re
        
        # Try to extract JSON from the response
        content = content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = re.sub(r'^```\w*\n?', '', content)
            content = re.sub(r'\n?```$', '', content)
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            
            # Return empty dict if parsing fails
            return {}


# Singleton
_generation_service: Optional[GenerationService] = None


def get_generation_service() -> GenerationService:
    """Get the global generation service instance."""
    global _generation_service
    if _generation_service is None:
        _generation_service = GenerationService()
    return _generation_service
