"""
Fact Checker Agent for verifying content accuracy.

This agent checks content against source materials and
flags potential inaccuracies or unsupported claims.
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
    LLMProvider,
)


class FactCheckState(BaseModel):
    """State for fact checking."""
    content: str
    source_chunks: list[str] = Field(default_factory=list)
    previous_chapters: list[str] = Field(default_factory=list)
    
    # Results
    findings: list[dict] = Field(default_factory=list)
    accuracy_score: Optional[float] = None
    needs_revision: bool = False


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
2. Verify each claim against provided source materials
3. Flag claims that aren't supported by sources
4. Identify any internal contradictions
5. Note any claims that seem questionable

For each issue found, provide:
- The specific claim or statement
- Why it's problematic
- Suggested correction or flag for human review

Be thorough but not overly pedantic. Focus on:
- Verifiable facts and figures
- Quotes and attributions  
- Timeline consistency
- Internal logic

Output findings as structured JSON for easy processing."""
    
    def process(self, state: FactCheckState) -> AgentOutput:
        """Check content for factual accuracy."""
        # Build source context
        source_context = ""
        if state.source_chunks:
            source_context = "SOURCE MATERIALS:\n" + "\n---\n".join(state.source_chunks[:5])
        
        # Build continuity context
        continuity_context = ""
        if state.previous_chapters:
            continuity_context = "PREVIOUS CHAPTERS (for continuity checking):\n" + "\n---\n".join(
                [ch[:1000] for ch in state.previous_chapters[-2:]]
            )
        
        prompt = f"""Check this content for factual accuracy and consistency.

{source_context}

{continuity_context}

CONTENT TO CHECK:
{state.content}

Identify all issues and provide as JSON:
{{
    "accuracy_score": 0.0-1.0,
    "findings": [
        {{
            "type": "unsupported|contradiction|questionable|inaccurate",
            "severity": "low|medium|high",
            "location": "quote or describe where in content",
            "issue": "description of the problem",
            "suggestion": "recommended fix or 'flag for human review'"
        }}
    ],
    "summary": "Brief overall assessment"
}}

If content is accurate, return empty findings with score of 1.0."""

        output = self.invoke(prompt)
        
        if output.is_success():
            results = self._parse_json(output.content)
            output.structured_data = results
            
            # Determine if revision needed
            findings = results.get("findings", [])
            high_severity = [f for f in findings if f.get("severity") == "high"]
            output.confidence = results.get("accuracy_score", 0.5)
            
            if high_severity:
                output.reasoning = f"Found {len(high_severity)} high-severity issues requiring revision"
        
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

