"""
Fact Checker Agent for verifying content accuracy.

This agent checks content against source materials and
flags potential inaccuracies or unsupported claims.

GROUNDING: Uses claim-to-source mapping to verify each factual claim
is supported by the provided source materials.
"""

import json
import re
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
class ClaimMapping:
    """Maps a claim to its supporting source."""
    claim: str
    source_citation: Optional[str]  # Citation if supported
    source_content: Optional[str]  # The source text that supports it
    is_supported: bool
    confidence: float  # 0-1, how confident we are in the mapping
    notes: str = ""


class FactCheckState(BaseModel):
    """State for fact checking."""
    content: str
    source_chunks: list[str] = Field(default_factory=list)  # Legacy: plain text
    source_chunks_with_citations: list[dict] = Field(default_factory=list)  # {"content": str, "citation": str}
    previous_chapters: list[str] = Field(default_factory=list)
    
    # Configuration
    strict_mode: bool = False  # If True, all claims must be verified
    
    # Results
    findings: list[dict] = Field(default_factory=list)
    claim_mappings: list[dict] = Field(default_factory=list)  # List of ClaimMapping dicts
    accuracy_score: Optional[float] = None
    needs_revision: bool = False
    unsupported_claims: list[str] = Field(default_factory=list)


class FactCheckerAgent(BaseAgent[FactCheckState]):
    """
    Agent that verifies factual accuracy and consistency.
    
    Specializes in:
    - Checking claims against source materials
    - Identifying unsupported statements
    - Detecting internal contradictions
    - Flagging potential issues for human review
    """
    
    def _default_config(self) -> AgentConfig:
        return AgentConfig(
            role=AgentRole.FACT_CHECKER,
            model="claude-sonnet-4-20250514",
            provider=LLMProvider.ANTHROPIC,
            temperature=0.3,  # Low for precision
            max_tokens=4096,
        )
    
    def get_system_prompt(self) -> str:
        return """You are an expert fact checker and editor. Your job is to:

1. Identify all factual claims in the content
2. MAP each claim to a specific source (if one exists)
3. Flag claims that aren't supported by sources
4. Identify any internal contradictions
5. Note any claims that seem questionable

CITATION FORMAT (REQUIRED):
All citations MUST use this exact format:
[citation: filename.ext - "exact quote from source"]

Examples:
- [citation: mentalhealth1.pdf - "Taking a step back isn't a delay"]
- [citation: notes.txt - "meditation helps me wade through"]

CLAIM-TO-SOURCE MAPPING:
For EACH factual claim, you must:
- Quote the claim exactly as it appears in the content
- Find the source that supports it using the EXACT citation format above
- Include the actual quote from the source that supports it
- Indicate if it's: VERIFIED (exact match), PARAPHRASED (same meaning), or UNSUPPORTED
- Provide a confidence score (0.0-1.0):
  * 1.0 = Exact quote match found in source
  * 0.8-0.9 = Close paraphrase with same meaning
  * 0.5-0.7 = Related content but modified
  * 0.0-0.4 = Cannot verify or seems fabricated

FLAG LOW-CONFIDENCE CITATIONS:
If confidence < 0.7, mark as "needs_human_review": true

For each issue found, provide:
- The specific claim or statement
- Why it's problematic
- Suggested correction or flag for human review
- Which source (if any) could support it with modifications

Be thorough but not overly pedantic. Focus on:
- Verifiable facts and figures
- Quotes and attributions  
- Timeline consistency
- Internal logic
- Grounding in source materials

CRITICAL: Never invent quotes. If you cannot find exact supporting text, mark as UNSUPPORTED.

Output findings as structured JSON for easy processing."""
    
    def process(self, state: FactCheckState) -> AgentOutput:
        """Check content for factual accuracy with claim-to-source mapping."""
        # Build source context with citations (prefer new format)
        source_context = ""
        available_sources = []
        
        if state.source_chunks_with_citations:
            chunks_text = []
            for i, chunk_data in enumerate(state.source_chunks_with_citations[:15]):
                citation = chunk_data.get("citation", f"[Source {i+1}]")
                content = chunk_data.get("content", "")
                available_sources.append(citation)
                chunks_text.append(f"---\n{citation}\n{content}\n---")
            source_context = "SOURCE MATERIALS (with citations):\n" + "\n".join(chunks_text)
        elif state.source_chunks:
            source_context = "SOURCE MATERIALS:\n" + "\n---\n".join(state.source_chunks[:5])
        
        # Build continuity context
        continuity_context = ""
        if state.previous_chapters:
            continuity_context = "PREVIOUS CHAPTERS (for continuity checking):\n" + "\n---\n".join(
                [ch[:1000] for ch in state.previous_chapters[-2:]]
            )
        
        # Build claim mapping instructions
        claim_mapping_instructions = ""
        if available_sources:
            claim_mapping_instructions = f"""
CLAIM-TO-SOURCE MAPPING REQUIRED:
Available sources: {', '.join(available_sources[:5])}...
For each factual claim, identify which source (if any) supports it.
"""
        
        prompt = f"""Check this content for factual accuracy and map claims to sources.

{source_context}

{continuity_context}

{claim_mapping_instructions}

CONTENT TO CHECK:
{state.content}

Identify all issues and provide as JSON:
{{
    "accuracy_score": 0.0-1.0,
    "claim_mappings": [
        {{
            "claim": "exact quote of the factual claim from the content",
            "source_citation": "[citation: filename.ext - \"exact quote\"] or null if unsupported",
            "source_quote": "the exact text from the source that supports this claim",
            "verification_status": "VERIFIED|PARAPHRASED|UNSUPPORTED",
            "is_supported": true/false,
            "confidence": 0.0-1.0,
            "needs_human_review": true/false (true if confidence < 0.7),
            "notes": "explanation of how the claim maps to the source"
        }}
    ],
    "findings": [
        {{
            "type": "unsupported|contradiction|questionable|inaccurate|low_confidence",
            "severity": "low|medium|high",
            "location": "quote or describe where in content",
            "issue": "description of the problem",
            "suggestion": "recommended fix or 'flag for human review'"
        }}
    ],
    "unsupported_claims": ["list", "of", "claims", "without", "sources"],
    "low_confidence_citations": ["list", "of", "claims", "with", "confidence", "<0.7"],
    "summary": "Brief overall assessment including grounding percentage and any concerns"
}}

If content is accurate and well-grounded, return high accuracy_score with detailed claim_mappings."""

        output = self.invoke(prompt)
        
        if output.is_success():
            results = self._parse_json(output.content)
            output.structured_data = results
            
            # Determine if revision needed
            findings = results.get("findings", [])
            high_severity = [f for f in findings if f.get("severity") == "high"]
            unsupported = results.get("unsupported_claims", [])
            claim_mappings = results.get("claim_mappings", [])
            
            # Calculate grounding score
            if claim_mappings:
                supported_count = sum(1 for c in claim_mappings if c.get("is_supported"))
                grounding_score = supported_count / len(claim_mappings)
            else:
                grounding_score = 0.5  # Unknown if no mappings
            
            output.confidence = results.get("accuracy_score", 0.5)
            
            # Add grounding metrics to structured data
            results["grounding_score"] = grounding_score
            results["total_claims"] = len(claim_mappings)
            results["supported_claims"] = sum(1 for c in claim_mappings if c.get("is_supported"))
            
            if high_severity:
                output.reasoning = f"Found {len(high_severity)} high-severity issues requiring revision"
            elif len(unsupported) > 3:
                output.reasoning = f"Found {len(unsupported)} unsupported claims - consider adding sources"
        
        return output
    
    def check_continuity(
        self,
        current_chapter: str,
        previous_chapters: list[str],
    ) -> AgentOutput:
        """Check for continuity issues across chapters."""
        prev_context = "\n\n---\n\n".join([ch[:1500] for ch in previous_chapters[-3:]])
        
        prompt = f"""Check for continuity issues between chapters.

PREVIOUS CHAPTERS:
{prev_context}

CURRENT CHAPTER:
{current_chapter}

Look for:
1. Timeline inconsistencies
2. Character/entity contradictions
3. Facts that changed without explanation
4. Logical gaps in narrative

Report as JSON:
{{
    "continuity_score": 0.0-1.0,
    "issues": [
        {{
            "type": "timeline|contradiction|gap|other",
            "description": "specific issue",
            "previous_reference": "what was said before",
            "current_reference": "what is said now",
            "suggestion": "how to resolve"
        }}
    ]
}}"""

        output = self.invoke(prompt)
        
        if output.is_success():
            output.structured_data = self._parse_json(output.content)
        
        return output
    
    def verify_claim(
        self,
        claim: str,
        source_chunks: list[str],
    ) -> AgentOutput:
        """Verify a specific claim against sources."""
        sources = "\n---\n".join(source_chunks[:5])
        
        prompt = f"""Verify this specific claim against the provided sources.

CLAIM: {claim}

SOURCES:
{sources}

Respond with JSON:
{{
    "verified": true/false,
    "confidence": 0.0-1.0,
    "supporting_evidence": "quote or reference from sources if found",
    "notes": "any caveats or additional context"
}}"""

        output = self.invoke(prompt)
        
        if output.is_success():
            output.structured_data = self._parse_json(output.content)
        
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
            return {"accuracy_score": 0.5, "findings": [], "summary": "Could not parse results"}
    
    def verify_citations_against_sources(
        self,
        claim_mappings: list[dict],
        source_chunks: list[dict],
    ) -> list[dict]:
        """
        Post-process claim mappings to verify citations actually exist in sources.
        
        Args:
            claim_mappings: List of claim mapping dicts from fact check
            source_chunks: List of {"content": str, "citation": str} source chunks
            
        Returns:
            Updated claim mappings with verification results
        """
        # Build a searchable index of source content
        source_index = {}
        for chunk in source_chunks:
            citation = chunk.get("citation", "")
            content = chunk.get("content", "").lower()
            if citation not in source_index:
                source_index[citation] = ""
            source_index[citation] += " " + content
        
        all_source_text = " ".join(source_index.values()).lower()
        
        verified_mappings = []
        for mapping in claim_mappings:
            source_quote = mapping.get("source_quote", "")
            if source_quote:
                # Check if the quote actually exists in sources
                quote_lower = source_quote.lower()[:100]  # First 100 chars
                
                if quote_lower in all_source_text:
                    mapping["quote_verified"] = True
                else:
                    # Quote not found - flag it
                    mapping["quote_verified"] = False
                    mapping["needs_human_review"] = True
                    mapping["confidence"] = min(mapping.get("confidence", 0.5), 0.5)
                    mapping["notes"] = (mapping.get("notes", "") + 
                        " [WARNING: Source quote could not be verified in provided materials]").strip()
            else:
                mapping["quote_verified"] = None  # No quote provided
            
            verified_mappings.append(mapping)
        
        return verified_mappings
    
    def get_citation_quality_report(self, claim_mappings: list[dict]) -> dict:
        """
        Generate a quality report for citations.
        
        Returns:
            Dict with citation quality metrics
        """
        total = len(claim_mappings)
        if total == 0:
            return {
                "total_claims": 0,
                "verified": 0,
                "needs_review": 0,
                "unsupported": 0,
                "quality_score": 1.0,
            }
        
        verified = sum(1 for m in claim_mappings if m.get("is_supported") and m.get("confidence", 0) >= 0.7)
        needs_review = sum(1 for m in claim_mappings if m.get("needs_human_review"))
        unsupported = sum(1 for m in claim_mappings if not m.get("is_supported"))
        
        quality_score = verified / total if total > 0 else 0
        
        return {
            "total_claims": total,
            "verified": verified,
            "needs_review": needs_review,
            "unsupported": unsupported,
            "quality_score": quality_score,
            "recommendation": (
                "Good" if quality_score >= 0.8 else
                "Review needed" if quality_score >= 0.5 else
                "Significant revision needed"
            ),
        }

