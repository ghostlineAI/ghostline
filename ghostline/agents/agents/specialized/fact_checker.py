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

CLAIM-TO-SOURCE MAPPING:
For EACH factual claim, you must:
- Quote the claim exactly
- Find the source that supports it (cite by [citation])
- Indicate if it's supported, partially supported, or unsupported
- Provide a confidence score (0.0-1.0)

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

Output findings as structured JSON for easy processing."""
    
    def process(self, state: FactCheckState) -> AgentOutput:
        """Check content for factual accuracy with claim-to-source mapping."""
        # Build source context with citations (prefer new format)
        source_context = ""
        available_sources = []
        
        if state.source_chunks_with_citations:
            chunks_text = []
            for i, chunk_data in enumerate(state.source_chunks_with_citations[:10]):
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
            "claim": "exact quote of the factual claim",
            "source_citation": "[citation] or null if unsupported",
            "is_supported": true/false,
            "confidence": 0.0-1.0,
            "notes": "any additional context"
        }}
    ],
    "findings": [
        {{
            "type": "unsupported|contradiction|questionable|inaccurate",
            "severity": "low|medium|high",
            "location": "quote or describe where in content",
            "issue": "description of the problem",
            "suggestion": "recommended fix or 'flag for human review'"
        }}
    ],
    "unsupported_claims": ["list", "of", "claims", "without", "sources"],
    "summary": "Brief overall assessment including grounding percentage"
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

