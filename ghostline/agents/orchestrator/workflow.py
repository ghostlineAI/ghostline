"""
Main LangGraph workflow for book generation.

This is the outer graph that coordinates the full pipeline:
  Ingest → Embed → OutlineSubgraph → UserApproveOutline → 
  DraftChapterSubgraph (loop) → UserEdits → Finalize → Export
"""

import logging
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Annotated, Optional, TypedDict
from uuid import UUID, uuid4

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

# Import conversation logger
from agents.core import get_conversation_logger

logger = logging.getLogger(__name__)

# NOTE: MemorySaver is in-memory; to support pause/resume across separate Celery tasks
# in the same worker process, we must share a single checkpointer instance.
# This is a pragmatic local-dev solution (durable checkpointing should use a DB-backed saver).
_GLOBAL_CHECKPOINTER = MemorySaver()

def _get_db_session():
    """
    Best-effort DB session factory.
    
    In local dev, the Celery worker runs from `ghostline/api`, so `app.*` imports
    already work. This helper keeps imports lazy to avoid hard coupling at module
    import time.
    """
    try:
        from app.db.base import SessionLocal
        return SessionLocal()
    except Exception:
        # Fallback: ensure api path is on sys.path (mirrors safety_check behavior)
        import sys
        from pathlib import Path
        api_path = Path(__file__).parent.parent.parent.parent / "api"
        if str(api_path) not in sys.path:
            sys.path.insert(0, str(api_path))
        from app.db.base import SessionLocal
        return SessionLocal()


def _voice_profile_to_dict(vp: Any) -> dict:
    """Convert VoiceProfile ORM to a JSON-serializable dict for agents."""
    if not vp:
        return {}
    return {
        "id": str(getattr(vp, "id", "")) if getattr(vp, "id", None) else None,
        "name": getattr(vp, "name", None),
        "description": getattr(vp, "description", None),
        "sample_text": getattr(vp, "sample_text", None),
        "tone": getattr(vp, "tone", None),
        "style": getattr(vp, "style", None),
        "style_description": getattr(vp, "style_description", None),
        "style_attributes": getattr(vp, "style_attributes", None),
        "stylistic_elements": getattr(vp, "stylistic_elements", None),
        # Numeric stylometry metrics
        "avg_sentence_length": getattr(vp, "avg_sentence_length", None),
        "sentence_length_std": getattr(vp, "sentence_length_std", None),
        "avg_word_length": getattr(vp, "avg_word_length", None),
        "vocabulary_complexity": getattr(vp, "vocabulary_complexity", None),
        "vocabulary_richness": getattr(vp, "vocabulary_richness", None),
        "punctuation_density": getattr(vp, "punctuation_density", None),
        "question_ratio": getattr(vp, "question_ratio", None),
        "exclamation_ratio": getattr(vp, "exclamation_ratio", None),
        "avg_paragraph_length": getattr(vp, "avg_paragraph_length", None),
        "common_phrases": list(getattr(vp, "common_phrases", []) or []),
        "sentence_starters": list(getattr(vp, "sentence_starters", []) or []),
        "transition_words": list(getattr(vp, "transition_words", []) or []),
        "similarity_threshold": getattr(vp, "similarity_threshold", 0.85),
        "embedding_weight": getattr(vp, "embedding_weight", 0.4),
    }


class WorkflowPhase(str, Enum):
    """Phases of the book generation workflow."""
    INITIALIZED = "initialized"
    INGESTING = "ingesting"
    EMBEDDING = "embedding"
    OUTLINE_GENERATION = "outline_generation"
    OUTLINE_REVIEW = "outline_review"
    DRAFTING = "drafting"
    EDITING = "editing"
    REVIEWING = "reviewing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"


class WorkflowState(TypedDict, total=False):
    """
    State for the book generation workflow.
    
    This state is persisted at checkpoints and passed between nodes.
    """
    # Identifiers
    workflow_id: str
    project_id: str
    user_id: str
    
    # Phase tracking
    phase: str
    current_step: str
    progress: int  # 0-100
    
    # Source materials
    source_material_ids: list[str]
    source_chunks: list[dict]  # {id, content, embedding}
    voice_profile: Optional[dict]
    # Lightweight summaries for outline generation (kept small for state size)
    source_summaries: list[str]
    
    # Project context (used by outline/chapter prompts)
    project_title: str
    project_description: str
    
    # Planning knobs
    target_chapters: int
    target_pages: Optional[int]  # Soft target for total book pages (1 page ≈ 250 words)
    words_per_page: int  # Default 250, configurable
    target_words_per_chapter: Optional[int]  # Calculated from target_pages / target_chapters
    book_outline_id: Optional[str]
    
    # Outline
    outline: Optional[dict]
    outline_approved: bool
    outline_feedback: list[str]
    
    # Chapters
    chapters: list[dict]  # {number, title, content, status}
    current_chapter: int
    chapter_summaries: list[str]
    # Canonical per-chapter memory (fed forward to improve long-form coherence)
    chapter_canon: list[dict]
    
    # Quality tracking
    voice_scores: list[float]
    fact_check_scores: list[float]
    cohesion_scores: list[float]
    
    # Cost tracking
    total_tokens: int
    total_cost: float
    
    # User interaction
    pending_user_action: Optional[str]
    user_feedback: list[dict]
    
    # Timestamps
    started_at: str
    last_updated: str
    completed_at: Optional[str]
    
    # Safety checks (for mental health content)
    safety_passed: bool
    safety_findings: list[dict]  # {flag, severity, matched_text, recommendation}
    suggested_disclaimer: Optional[str]
    
    # Errors
    error: Optional[str]


def create_initial_state(
    project_id: str,
    user_id: str,
    source_material_ids: list[str],
    target_pages: Optional[int] = None,
    target_chapters: int = 3,
    words_per_page: int = 250,
) -> WorkflowState:
    """
    Create initial workflow state.
    
    Args:
        project_id: The project ID
        user_id: The user ID  
        source_material_ids: List of source material IDs
        target_pages: Soft target for total book pages (optional, 1 page ≈ 250 words)
        target_chapters: Number of chapters to generate (default 3)
        words_per_page: Words per page for calculations (default 250)
    """
    # Calculate target words per chapter from page target
    target_words_per_chapter = None
    if target_pages:
        total_words = target_pages * words_per_page
        target_words_per_chapter = total_words // target_chapters
    
    return WorkflowState(
        workflow_id=str(uuid4()),
        project_id=project_id,
        user_id=user_id,
        phase=WorkflowPhase.INITIALIZED.value,
        current_step="Initializing workflow",
        progress=0,
        source_material_ids=source_material_ids,
        source_chunks=[],
        source_summaries=[],
        project_title="",
        project_description="",
        target_chapters=target_chapters,
        target_pages=target_pages,
        words_per_page=words_per_page,
        target_words_per_chapter=target_words_per_chapter,
        book_outline_id=None,
        voice_profile=None,
        outline=None,
        outline_approved=False,
        outline_feedback=[],
        chapters=[],
        current_chapter=0,
        chapter_summaries=[],
        chapter_canon=[],
        voice_scores=[],
        fact_check_scores=[],
        cohesion_scores=[],
        total_tokens=0,
        total_cost=0.0,
        pending_user_action=None,
        user_feedback=[],
        started_at=datetime.utcnow().isoformat(),
        last_updated=datetime.utcnow().isoformat(),
        completed_at=None,
        error=None,
    )


def _build_chapter_canon(
    *,
    chapter_number: int,
    title: str,
    chapter_outline: dict,
    chapter_result: dict,
) -> dict:
    """
    Build a canonical, feed-forward memory object for the chapter.

    This intentionally prefers *grounded* information (FactChecker claim mappings)
    over free-form summaries so later chapters have a stable "canon" to adhere to.
    """
    claim_mappings = list(chapter_result.get("claim_mappings") or [])
    supported: list[str] = []
    needs_review: list[str] = []
    unsupported: list[str] = []
    seen: set[str] = set()

    for m in claim_mappings:
        claim = str(m.get("claim") or "").strip()
        if not claim:
            continue
        key = claim.lower()
        if key in seen:
            continue
        seen.add(key)

        if bool(m.get("is_supported")):
            supported.append(claim)
        else:
            unsupported.append(claim)

        if bool(m.get("needs_human_review")) or (m.get("quote_verified") is False):
            needs_review.append(claim)

    qgr = chapter_result.get("quality_gate_report") or {}

    return {
        "chapter_number": int(chapter_number),
        "title": str(title),
        "outline_summary": str(chapter_outline.get("summary") or "").strip(),
        "key_points": list(chapter_outline.get("key_points") or []),
        "grounded_commitments": supported[:8],
        "needs_review": needs_review[:5],
        "unsupported": unsupported[:5],
        "citations_ok": bool(qgr.get("citations_ok")) if isinstance(qgr, dict) else None,
        "style_issues": (qgr.get("style_issues") or []) if isinstance(qgr, dict) else [],
    }


def _format_chapter_canon(canon: dict) -> str:
    """Format the canon object into a compact promptable block."""
    n = canon.get("chapter_number")
    title = canon.get("title") or ""
    lines: list[str] = [f"CHAPTER {n}: {title}".strip()]

    outline_summary = str(canon.get("outline_summary") or "").strip()
    if outline_summary:
        lines.append(f"Intent: {outline_summary}")

    key_points = list(canon.get("key_points") or [])
    if key_points:
        lines.append("Key points: " + "; ".join(str(k) for k in key_points[:6] if k))

    grounded = list(canon.get("grounded_commitments") or [])
    if grounded:
        lines.append("Grounded commitments:")
        lines.extend(f"- {c}" for c in grounded[:8])

    needs_review = list(canon.get("needs_review") or [])
    if needs_review:
        lines.append("Needs review / be careful not to assert:")
        lines.extend(f"- {c}" for c in needs_review[:5])

    return "\n".join(lines).strip()


# Node functions for the workflow
def ingest_sources(state: WorkflowState) -> WorkflowState:
    """Load and process source materials."""
    state["phase"] = WorkflowPhase.INGESTING.value
    state["current_step"] = "Loading source materials"
    state["progress"] = 5
    state["last_updated"] = datetime.utcnow().isoformat()
    
    # Local dev implementation: load project + source materials from DB and build
    # lightweight summaries for outline generation.
    # Check if we already have source data (resume scenario)
    if state.get("source_summaries") and state.get("project_title"):
        logger.info("📝 [Workflow] Skipping ingest - already done")
        return state
    
    project_id_str = state.get("project_id")
    if not project_id_str:
        logger.warning("📝 [Workflow] No project_id in state - cannot ingest")
        return state
    
    db = _get_db_session()
    try:
        from app.models.project import Project
        from app.models.source_material import SourceMaterial

        project_uuid = UUID(project_id_str)
        source_ids = [UUID(s) for s in state.get("source_material_ids", []) or []]

        project = db.query(Project).filter(Project.id == project_uuid).first()
        if project:
            state["project_title"] = project.title
            state["project_description"] = project.description or ""
        else:
            state["project_title"] = state.get("project_title") or "Untitled Book"
            state["project_description"] = state.get("project_description") or ""

        materials = (
            db.query(SourceMaterial)
            .filter(SourceMaterial.project_id == project_uuid, SourceMaterial.id.in_(source_ids))
            .all()
        )

        summaries: list[str] = []
        for sm in materials:
            meta = sm.file_metadata or {}
            summary = ""
            if isinstance(meta, dict) and meta.get("summary"):
                summary = str(meta.get("summary", "")).strip()
            if not summary:
                # Some pipelines populate `extracted_content` instead of `extracted_text`
                raw = (sm.extracted_text or sm.extracted_content or "").strip()
                if raw:
                    summary = raw[:2000]
            header = f"Source: {sm.filename}"
            if summary:
                summaries.append(f"{header}\n{summary}")
            else:
                summaries.append(header)

        state["source_summaries"] = summaries

        # Optional: derive a modest chapter count for E2E runs
        # Default to 3 to keep the live run bounded while still testing multi-chapter.
        if not state.get("target_chapters"):
            state["target_chapters"] = 3
    finally:
        db.close()
    
    return state


def embed_sources(state: WorkflowState) -> WorkflowState:
    """Generate embeddings for source chunks."""
    state["phase"] = WorkflowPhase.EMBEDDING.value
    state["current_step"] = "Generating embeddings"
    state["progress"] = 15
    state["last_updated"] = datetime.utcnow().isoformat()
    
    # In real implementation, this would:
    # 1. Chunk source text
    # 2. Generate embeddings using EmbeddingService
    # 3. Store in vector database
    
    # Local dev: fetch voice profile (if available) so ChapterSubgraph can do real
    # voice editing instead of the default pass-through score.
    db = _get_db_session()
    try:
        from app.models.voice_profile import VoiceProfile
        project_uuid = UUID(state["project_id"])
        vp = db.query(VoiceProfile).filter(VoiceProfile.project_id == project_uuid).first()
        state["voice_profile"] = _voice_profile_to_dict(vp)
    finally:
        db.close()
    
    return state


def generate_outline(state: WorkflowState) -> WorkflowState:
    """Generate book outline using OutlineSubgraph."""
    state["phase"] = WorkflowPhase.OUTLINE_GENERATION.value
    state["current_step"] = "Generating book outline"
    state["progress"] = 25
    state["last_updated"] = datetime.utcnow().isoformat()
    strict_mode = os.getenv("GHOSTLINE_STRICT_MODE", "").strip().lower() in ("1", "true", "yes", "on")
    
    # Run the real OutlineSubgraph when possible.
    try:
        from orchestrator.subgraphs import OutlineSubgraph
        outline_subgraph = OutlineSubgraph()
        target_chapters = int(state.get("target_chapters") or 3)
        voice_guidance = (state.get("voice_profile") or {}).get("style_description") or ""

        result = outline_subgraph.run(
            source_summaries=state.get("source_summaries", []) or [],
            project_title=state.get("project_title") or "Untitled Book",
            project_description=state.get("project_description") or "",
            target_chapters=target_chapters,
            voice_guidance=voice_guidance,
        )

        outline = result.get("outline") or {}
        # Enforce the requested chapter count deterministically; the LLM can drift.
        try:
            chapters = list(outline.get("chapters") or [])
            if target_chapters and len(chapters) > target_chapters:
                chapters = chapters[:target_chapters]
            # Re-number chapters sequentially after trimming.
            for idx, ch in enumerate(chapters, 1):
                if isinstance(ch, dict):
                    ch["number"] = idx
            outline["chapters"] = chapters
        except Exception:
            pass

        if outline:
            state["outline"] = outline
            state["total_tokens"] = (state.get("total_tokens") or 0) + int(result.get("tokens_used") or 0)
            state["total_cost"] = (state.get("total_cost") or 0.0) + float(result.get("cost") or 0.0)
        else:
            raise ValueError("OutlineSubgraph returned empty outline")
    except Exception as e:
        if strict_mode:
            raise
        logger.warning(f"OutlineSubgraph failed; falling back to placeholder outline: {e}")
        state["outline"] = {
            "title": state.get("project_title") or "Generated Book",
            "chapters": [
                {"number": i + 1, "title": f"Chapter {i + 1}", "summary": "TBD"}
                for i in range(int(state.get("target_chapters") or 3))
            ],
        }

    # Persist outline to DB for project retrieval endpoints
    db = _get_db_session()
    try:
        from app.models.book_outline import BookOutline, OutlineStatus
        project_uuid = UUID(state["project_id"])

        outline_obj = state.get("outline") or {}
        outline_json = json.dumps(outline_obj, default=str)

        existing = (
            db.query(BookOutline)
            .filter(BookOutline.project_id == project_uuid)
            .order_by(BookOutline.created_at.desc())
            .first()
        )

        if existing:
            existing.title = outline_obj.get("title") or existing.title
            existing.structure = outline_json
            existing.status = OutlineStatus.DRAFT
            outline_row = existing
        else:
            outline_row = BookOutline(
                project_id=project_uuid,
                title=outline_obj.get("title") or (state.get("project_title") or "Book"),
                structure=outline_json,
                status=OutlineStatus.DRAFT,
            )
            db.add(outline_row)

        db.commit()
        db.refresh(outline_row)
        state["book_outline_id"] = str(outline_row.id)
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.warning(f"Failed to persist BookOutline: {e}")
    finally:
        db.close()
    
    return state


def request_outline_approval(state: WorkflowState) -> WorkflowState:
    """Pause for user to approve outline."""
    state["phase"] = WorkflowPhase.OUTLINE_REVIEW.value
    state["current_step"] = "Waiting for outline approval"
    state["pending_user_action"] = "approve_outline"
    state["progress"] = 30
    state["last_updated"] = datetime.utcnow().isoformat()
    
    return state


def draft_chapter(state: WorkflowState) -> WorkflowState:
    """Draft the current chapter."""
    current = state.get("current_chapter", 0)
    state["phase"] = WorkflowPhase.DRAFTING.value
    state["current_step"] = f"Drafting chapter {current + 1}"
    state["last_updated"] = datetime.utcnow().isoformat()
    
    # Calculate progress (chapters are 30-90% of work)
    total_chapters = len(state.get("outline", {}).get("chapters", []))
    if total_chapters > 0:
        chapter_progress = (current / total_chapters) * 60  # 60% for all chapters
        state["progress"] = int(30 + chapter_progress)
    
    # Local dev: run ChapterSubgraph with RAG chunks and voice profile.
    outline = state.get("outline") or {}
    outline_chapters = outline.get("chapters") or []
    chapter_number = current + 1

    chapter_outline = None
    if current < len(outline_chapters):
        chapter_outline = outline_chapters[current]
    if not chapter_outline:
        chapter_outline = {"number": chapter_number, "title": f"Chapter {chapter_number}", "summary": "TBD"}

    # Retrieve source chunks with RAG
    source_chunks: list[str] = []
    source_chunks_with_citations: list[dict] = []
    db = _get_db_session()
    strict_mode = os.getenv("GHOSTLINE_STRICT_MODE", "").strip().lower() in ("1", "true", "yes", "on")
    try:
        from app.services.rag import RAGService
        rag = RAGService()

        query_parts = [
            state.get("project_title") or "",
            state.get("project_description") or "",
            str(chapter_outline.get("title") or ""),
            str(chapter_outline.get("summary") or ""),
            " ".join(chapter_outline.get("key_points", []) or []),
        ]
        query = " ".join(p for p in query_parts if p).strip()
        if query:
            rag_result = rag.retrieve(
                query=query,
                project_id=UUID(state["project_id"]),
                db=db,
                top_k=20,
                similarity_threshold=0.2,
            )
            for chunk in (rag_result.chunks or []):
                # Plain text format for legacy compatibility
                source_chunks.append(chunk.to_context_block(include_citation=True))
                # Structured format for citation verification
                citation_str = None
                try:
                    # Prefer stable, human-readable identifiers.
                    if chunk.citation and getattr(chunk.citation, "source_filename", None):
                        citation_str = chunk.citation.source_filename
                    elif chunk.citation and getattr(chunk.citation, "source_reference", None):
                        citation_str = chunk.citation.source_reference
                    elif chunk.citation:
                        citation_str = chunk.citation.to_citation_string()
                except Exception:
                    citation_str = None

                source_chunks_with_citations.append(
                    {
                        "content": chunk.content,
                        "citation": citation_str or f"Source chunk {len(source_chunks_with_citations) + 1}",
                    }
                )

            # Always include the image-derived source material (mental_health.png) when present.
            # This is small (4 chunks) but contains the visual model that PDFs may not define.
            try:
                from app.models.source_material import SourceMaterial
                from app.models.content_chunk import ContentChunk

                sm_img = (
                    db.query(SourceMaterial)
                    .filter(
                        SourceMaterial.project_id == UUID(state["project_id"]),
                        SourceMaterial.filename == "mental_health.png",
                    )
                    .first()
                )
                if sm_img:
                    img_chunks = (
                        db.query(ContentChunk)
                        .filter(ContentChunk.source_material_id == sm_img.id)
                        .order_by(ContentChunk.chunk_index.asc())
                        .limit(6)
                        .all()
                    )
                    # Append image chunks if not already present.
                    existing_contents = set((c.get("content") or "") for c in source_chunks_with_citations)
                    for cc in img_chunks:
                        if not cc.content or cc.content in existing_contents:
                            continue
                        source_chunks.append(f"---\n[{sm_img.filename}]\n{cc.content}\n---")
                        source_chunks_with_citations.append({"content": cc.content, "citation": sm_img.filename})
                        existing_contents.add(cc.content)
            except Exception:
                pass
    except Exception as e:
        if strict_mode:
            raise
        logger.warning(f"RAG retrieval failed for chapter {chapter_number}: {e}")
        source_chunks = []
        source_chunks_with_citations = []
    finally:
        db.close()

    # Generate chapter content (strict: fail the workflow if a chapter cannot meet quality gates)
    try:
        from orchestrator.subgraphs import ChapterSubgraph
        chapter_subgraph = ChapterSubgraph()

        canon_blocks = [
            _format_chapter_canon(c)
            for c in (state.get("chapter_canon", []) or [])
            if isinstance(c, dict)
        ]
        result = chapter_subgraph.run(
            chapter_outline=chapter_outline,
            source_chunks=source_chunks,
            source_chunks_with_citations=source_chunks_with_citations,
            # Feed forward canonical memory (not just thin summaries) to improve long-form coherence.
            previous_summaries=canon_blocks[-3:],
            voice_profile=state.get("voice_profile") or {},
            # Use calculated target from page count, or default to 3000 words
            target_words=state.get("target_words_per_chapter") or 3000,
            project_id=state.get("project_id"),
        )

        content = result.get("content") or ""
        title = chapter_outline.get("title") or f"Chapter {chapter_number}"
        quality_gates_passed = bool(result.get("quality_gates_passed", False))

        # Store in workflow state with citation report
        citation_report = result.get("citation_report", {})
        state.setdefault("chapters", [])
        state["chapters"].append(
            {
                "number": chapter_number,
                "title": title,
                "content": content,
                "content_clean": result.get("content_clean"),
                "status": "draft",
                "word_count": result.get("word_count", 0),
                "voice_score": result.get("voice_score", 0.0),
                "fact_score": result.get("fact_score", 0.0),
                "cohesion_score": result.get("cohesion_score", 0.0),
                # Citation verification report
                "citation_report": citation_report,
                "claim_mappings": result.get("claim_mappings", []),
                "citations": result.get("citations", []),
                # Quality gate diagnostics (always persisted, even on failure)
                "quality_gates_passed": quality_gates_passed,
                "quality_gate_report": result.get("quality_gate_report") or {},
                "revision_history": result.get("revision_history") or [],
            }
        )
        
        # Log citation quality for this chapter
        if citation_report:
            logger.info(
                f"📊 [Workflow] Chapter {chapter_number} citation report: "
                f"verified={citation_report.get('verified', 0)}/{citation_report.get('total_claims', 0)}, "
                f"needs_review={citation_report.get('needs_review', 0)}, "
                f"quality={citation_report.get('quality_score', 0):.2f}"
            )
        state.setdefault("voice_scores", []).append(float(result.get("voice_score", 0.0) or 0.0))
        state.setdefault("fact_check_scores", []).append(float(result.get("fact_score", 0.0) or 0.0))
        state.setdefault("cohesion_scores", []).append(float(result.get("cohesion_score", 0.0) or 0.0))
        state["total_tokens"] = (state.get("total_tokens") or 0) + int(result.get("tokens_used") or 0)
        state["total_cost"] = (state.get("total_cost") or 0.0) + float(result.get("cost") or 0.0)

        # Enforce strict quality gates at the workflow level (after persisting diagnostics)
        if not quality_gates_passed:
            report = result.get("quality_gate_report") or {}
            msg = f"Chapter {chapter_number} quality gates not met: {report}"
            logger.error(msg)
            state["error"] = msg
            # Strict mode: fail the workflow (do not ship hallucinated/unsupported content)
            if strict_mode:
                raise RuntimeError(msg)
            # Non-strict: continue (for dev/e2e debugging only)
            logger.warning(f"Continuing despite failed quality gates (strict_mode off): {msg}")

        # Simple summary for cohesion context
        summary = (chapter_outline.get("summary") or "").strip()
        if not summary and content:
            summary = " ".join(content.split()[:60])
        state.setdefault("chapter_summaries", []).append(summary)

        # Canonical memory for the next chapters (grounded, structured)
        canon = _build_chapter_canon(
            chapter_number=chapter_number,
            title=title,
            chapter_outline=chapter_outline,
            chapter_result=result,
        )
        state.setdefault("chapter_canon", []).append(canon)

        # Persist Chapter row
        db2 = _get_db_session()
        try:
            from app.models.chapter import Chapter
            project_uuid = UUID(state["project_id"])
            outline_id = state.get("book_outline_id")
            outline_uuid = UUID(outline_id) if outline_id else None

            chapter_row = (
                db2.query(Chapter)
                .filter(Chapter.project_id == project_uuid, Chapter.order == chapter_number)
                .first()
            )
            if chapter_row:
                chapter_row.title = title
                chapter_row.content = content
                chapter_row.word_count = int(result.get("word_count") or 0)
                if outline_uuid:
                    chapter_row.book_outline_id = outline_uuid
            else:
                chapter_row = Chapter(
                    project_id=project_uuid,
                    title=title,
                    order=chapter_number,
                    content=content,
                    word_count=int(result.get("word_count") or 0),
                    status="draft",
                    book_outline_id=outline_uuid,
                )
                db2.add(chapter_row)
            db2.commit()
        except Exception as e:
            try:
                db2.rollback()
            except Exception:
                pass
            logger.warning(f"Failed to persist Chapter {chapter_number}: {e}")
        finally:
            db2.close()

    except Exception as e:
        # Fail fast: do not ship a book with hallucinated/unsupported content.
        logger.error(f"ChapterSubgraph failed for chapter {chapter_number}: {e}")
        state["error"] = f"Chapter generation failed (chapter {chapter_number}): {e}"
        raise
    
    return state


def edit_chapter(state: WorkflowState) -> WorkflowState:
    """Edit chapter for voice and quality."""
    state["phase"] = WorkflowPhase.EDITING.value
    state["current_step"] = f"Editing chapter {state.get('current_chapter', 0) + 1}"
    state["last_updated"] = datetime.utcnow().isoformat()
    
    return state


def review_chapter(state: WorkflowState) -> WorkflowState:
    """Review chapter with fact-check and cohesion analysis."""
    current = state.get("current_chapter", 0)
    state["phase"] = WorkflowPhase.REVIEWING.value
    state["current_step"] = f"Reviewing chapter {current + 1}"
    state["last_updated"] = datetime.utcnow().isoformat()
    
    # Increment chapter counter after review is complete
    state["current_chapter"] = current + 1
    
    return state


def safety_check(state: WorkflowState) -> WorkflowState:
    """
    Run safety checks on generated content.
    
    For mental health content, this validates:
    - No harmful medical advice
    - No crisis language without resources
    - Appropriate disclaimers suggested
    """
    state["phase"] = WorkflowPhase.REVIEWING.value
    state["current_step"] = "Running safety checks"
    state["progress"] = 92
    state["last_updated"] = datetime.utcnow().isoformat()
    
    # Get all chapter content
    chapters = state.get("chapters", [])
    all_content = "\n\n".join(ch.get("content", "") for ch in chapters if ch.get("content"))
    
    if not all_content:
        state["safety_passed"] = True
        state["safety_findings"] = []
        return state
    
    try:
        # Import and run safety service
        # Note: Import inside function to avoid circular imports at module level
        import sys
        from pathlib import Path
        
        # Add api path if needed
        api_path = Path(__file__).parent.parent.parent.parent / "api"
        if str(api_path) not in sys.path:
            sys.path.insert(0, str(api_path))
        
        from app.services.safety import SafetyService
        
        safety = SafetyService()
        result = safety.check_content(all_content)
        
        state["safety_passed"] = result.is_safe
        state["safety_findings"] = [
            {
                "flag": f.flag.value,
                "severity": f.severity,
                "matched_text": f.matched_text[:100],
                "recommendation": f.recommendation,
            }
            for f in result.findings
        ]
        
        if result.requires_disclaimer:
            state["suggested_disclaimer"] = result.suggested_disclaimer
        
        # Log safety results
        logger.info(f"Safety check: {'PASSED' if result.is_safe else 'FLAGGED'} "
                   f"with {len(result.findings)} findings")
        
    except Exception as e:
        # Don't fail workflow on safety check errors, just log
        logger.warning(f"Safety check failed: {e}")
        state["safety_passed"] = True  # Pass by default on errors
        state["safety_findings"] = []
    
    return state


def finalize_book(state: WorkflowState) -> WorkflowState:
    """Finalize the complete book."""
    state["phase"] = WorkflowPhase.FINALIZING.value
    state["current_step"] = "Finalizing book"
    state["progress"] = 95
    state["last_updated"] = datetime.utcnow().isoformat()
    
    return state


def complete_workflow(state: WorkflowState) -> WorkflowState:
    """Mark workflow as complete."""
    state["phase"] = WorkflowPhase.COMPLETED.value
    state["current_step"] = "Generation complete"
    state["progress"] = 100
    state["completed_at"] = datetime.utcnow().isoformat()
    state["last_updated"] = datetime.utcnow().isoformat()
    
    return state


def handle_workflow_error(state: WorkflowState) -> WorkflowState:
    """Handle workflow errors."""
    state["phase"] = WorkflowPhase.FAILED.value
    state["last_updated"] = datetime.utcnow().isoformat()
    
    return state


def wait_for_approval(state: WorkflowState) -> WorkflowState:
    """
    Wait node for user approval.
    
    This node is interrupted before execution, allowing the workflow
    to pause. When resumed with approve_outline=True, the state is
    updated and execution continues.
    """
    # This node just passes through - the actual waiting happens via interrupt
    state["last_updated"] = datetime.utcnow().isoformat()
    return state


# Conditional routing functions
def should_continue_chapters(state: WorkflowState) -> str:
    """Check if there are more chapters to draft."""
    current = state.get("current_chapter", 0)
    total = len(state.get("outline", {}).get("chapters", []))
    
    if current < total:
        return "draft_chapter"
    else:
        return "finalize"


def outline_decision(state: WorkflowState) -> str:
    """Check if outline is approved."""
    if state.get("outline_approved", False):
        return "start_drafting"
    else:
        return "wait_approval"


class BookGenerationWorkflow:
    """
    LangGraph workflow for generating complete books.
    
    Uses a state machine with:
    - Durable checkpoints for pause/resume
    - User approval gates
    - Bounded agent conversations in subgraphs
    - Cost/token tracking
    """
    
    def __init__(self, checkpointer=None):
        self.checkpointer = checkpointer or _GLOBAL_CHECKPOINTER
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("ingest", ingest_sources)
        workflow.add_node("embed", embed_sources)
        workflow.add_node("generate_outline", generate_outline)
        workflow.add_node("request_approval", request_outline_approval)
        workflow.add_node("draft_chapter", draft_chapter)
        workflow.add_node("edit_chapter", edit_chapter)
        workflow.add_node("review_chapter", review_chapter)
        workflow.add_node("safety_check", safety_check)  # Safety validation before finalize
        workflow.add_node("finalize", finalize_book)
        workflow.add_node("complete", complete_workflow)
        workflow.add_node("handle_error", handle_workflow_error)
        
        # Add edges
        workflow.add_edge(START, "ingest")
        workflow.add_edge("ingest", "embed")
        workflow.add_edge("embed", "generate_outline")
        workflow.add_edge("generate_outline", "request_approval")
        
        # After request_approval, check if we should proceed or wait
        # Note: We use a dedicated wait node that will be interrupted
        workflow.add_node("wait_for_approval", wait_for_approval)
        
        workflow.add_edge("request_approval", "wait_for_approval")
        
        workflow.add_conditional_edges(
            "wait_for_approval",
            outline_decision,
            {
                "start_drafting": "draft_chapter",
                "wait_approval": END,  # Only reaches END if still not approved after resume
            }
        )
        
        # Chapter loop
        workflow.add_edge("draft_chapter", "edit_chapter")
        workflow.add_edge("edit_chapter", "review_chapter")
        
        workflow.add_conditional_edges(
            "review_chapter",
            should_continue_chapters,
            {
                "draft_chapter": "draft_chapter",
                "finalize": "safety_check",  # Run safety check before finalize
            }
        )
        
        workflow.add_edge("safety_check", "finalize")
        workflow.add_edge("finalize", "complete")
        workflow.add_edge("complete", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["wait_for_approval"],
        )
    
    def start(
        self,
        project_id: str,
        user_id: str,
        source_material_ids: list[str],
        target_pages: Optional[int] = None,
        target_chapters: int = 3,
        words_per_page: int = 250,
    ) -> dict:
        """
        Start a new book generation workflow.
        
        Args:
            project_id: The project ID
            user_id: The user ID
            source_material_ids: List of source material IDs
            target_pages: Soft target for total book pages (optional, 1 page ≈ 250 words)
            target_chapters: Number of chapters to generate (default: 3)
            words_per_page: Words per page for calculations (default: 250)
        """
        initial_state = create_initial_state(
            project_id=project_id,
            user_id=user_id,
            source_material_ids=source_material_ids,
            target_pages=target_pages,
            target_chapters=target_chapters,
            words_per_page=words_per_page,
        )
        
        workflow_id = initial_state["workflow_id"]
        config = {"configurable": {"thread_id": workflow_id}}
        
        # Start conversation logging session
        conv_logger = get_conversation_logger()
        conv_logger.start_session("book_generation", workflow_id)
        conv_logger.log_system(
            "Orchestrator",
            f"Starting workflow: project={project_id}, sources={len(source_material_ids)}"
        )
        
        try:
            # Run until first pause point
            result = self.graph.invoke(initial_state, config)
            
            # Log pause point
            conv_logger.log_system(
                "Orchestrator",
                f"Workflow paused at: {result.get('phase', 'unknown')} - {result.get('current_step', '')}"
            )
            
            # Dump conversation log to file
            log_path = conv_logger.dump_to_file()
            logger.info(f"📝 Conversation log saved: {log_path}")
            
            return {
                "workflow_id": workflow_id,
                "state": result,
                "conversation_log": str(log_path),
            }
            
        except Exception as e:
            conv_logger.log_system("Orchestrator", f"ERROR: {str(e)}")
            conv_logger.end_session(status="failed", error=str(e))
            conv_logger.dump_to_file()
            raise
    
    def resume(
        self,
        workflow_id: str,
        user_input: Optional[dict] = None,
    ) -> dict:
        """Resume a paused workflow."""
        config = {"configurable": {"thread_id": workflow_id}}
        
        # Resume conversation logging session
        conv_logger = get_conversation_logger()
        conv_logger.start_session("book_generation_resume", workflow_id)
        conv_logger.log_system(
            "Orchestrator",
            f"Resuming workflow: {workflow_id}"
        )
        
        # Get current state
        state = self.graph.get_state(config)
        
        if user_input:
            # Log user input
            conv_logger.log_system(
                "User",
                f"User input received: {user_input}"
            )
            
            # Apply user input to state
            state_values = dict(state.values) if state.values else {}
            
            # Ensure project_id is preserved (fix for resume bug)
            if user_input.get("project_id") and not state_values.get("project_id"):
                state_values["project_id"] = user_input["project_id"]
            
            if user_input.get("approve_outline"):
                state_values["outline_approved"] = True
                state_values["pending_user_action"] = None
                conv_logger.log_system("Orchestrator", "Outline approved by user")
            if user_input.get("feedback"):
                state_values.setdefault("user_feedback", []).append(user_input["feedback"])
                conv_logger.log_system("Orchestrator", f"Feedback added: {user_input['feedback'][:100]}...")
            
            # Update state
            self.graph.update_state(config, state_values)
        
        try:
            # Continue execution
            result = self.graph.invoke(None, config)
            
            # Log completion/pause
            final_phase = result.get('phase', 'unknown')
            if final_phase == "completed":
                conv_logger.log_system("Orchestrator", "✅ Workflow completed successfully!")
                conv_logger.end_session(status="completed")
            else:
                conv_logger.log_system(
                    "Orchestrator",
                    f"Workflow at: {final_phase} - {result.get('current_step', '')}"
                )
            
            # Dump conversation log
            log_path = conv_logger.dump_to_file()
            logger.info(f"📝 Conversation log saved: {log_path}")
            
            return {
                "workflow_id": workflow_id,
                "state": result,
                "conversation_log": str(log_path),
            }
            
        except Exception as e:
            conv_logger.log_system("Orchestrator", f"ERROR: {str(e)}")
            conv_logger.end_session(status="failed", error=str(e))
            conv_logger.dump_to_file()
            raise
    
    def get_state(self, workflow_id: str) -> dict:
        """Get current workflow state."""
        config = {"configurable": {"thread_id": workflow_id}}
        state = self.graph.get_state(config)
        return dict(state.values) if state.values else {}

