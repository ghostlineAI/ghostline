"""
Pydantic schemas for structured LLM outputs.

These models are used to validate and normalize JSON returned by agents.
When validation fails, we fall back to a best-effort JSON extraction rather than
silently accepting malformed structures.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class OutlineChapter(BaseModel):
    number: int
    title: str
    summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    estimated_words: int = 0
    sources_referenced: list[str] = Field(default_factory=list)


class BookOutlineModel(BaseModel):
    title: str = ""
    premise: str = ""
    chapters: list[OutlineChapter] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    target_audience: str = ""


class FactFinding(BaseModel):
    type: Literal["unsupported", "contradiction", "questionable", "inaccurate", "low_confidence"]
    severity: Literal["low", "medium", "high"]
    location: str = ""
    issue: str = ""
    suggestion: str = ""


class ClaimMappingModel(BaseModel):
    claim: str
    source_citation: Optional[str] = None
    source_quote: Optional[str] = None
    verification_status: Literal["VERIFIED", "PARAPHRASED", "UNSUPPORTED"]
    is_supported: bool
    confidence: float = Field(ge=0.0, le=1.0)
    needs_human_review: bool = False
    notes: str = ""


class FactCheckResultModel(BaseModel):
    accuracy_score: float = Field(default=0.5, ge=0.0, le=1.0)
    claim_mappings: list[ClaimMappingModel] = Field(default_factory=list)
    findings: list[FactFinding] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    low_confidence_citations: list[str] = Field(default_factory=list)
    summary: str = ""


class CohesionIssueModel(BaseModel):
    type: Literal["transition", "pacing", "structure", "alignment", "gap"]
    location: str = ""
    description: str = ""
    severity: Literal["low", "medium", "high"]
    suggestion: str = ""


class CohesionResultModel(BaseModel):
    cohesion_score: float = Field(default=0.5, ge=0.0, le=1.0)
    issues: list[CohesionIssueModel] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    summary: str = ""


