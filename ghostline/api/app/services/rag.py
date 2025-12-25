"""
RAG (Retrieval-Augmented Generation) Service.

Provides:
- pgvector-based similarity search for content chunks
- Citation tracking for grounded generation
- Context building for LLM prompts
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.embeddings import EmbeddingService, get_embedding_service

# Avoid circular imports - models are only needed for type hints and inside functions
if TYPE_CHECKING:
    from app.models.content_chunk import ContentChunk
    from app.models.project import Project

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """A citation reference to source material."""
    chunk_id: UUID
    source_material_id: UUID
    source_reference: Optional[str]  # e.g., "Chapter 3, p.45"
    source_filename: Optional[str]
    content_preview: str  # First 200 chars
    similarity_score: float
    
    def to_citation_string(self) -> str:
        """Format as a citation string for LLM prompts."""
        if self.source_reference:
            return f"[{self.source_reference}]"
        elif self.source_filename:
            return f"[{self.source_filename}]"
        else:
            return f"[Source {str(self.chunk_id)[:8]}]"


@dataclass
class RetrievedChunk:
    """A chunk retrieved from the database with its citation."""
    content: str
    citation: Citation
    word_count: int
    chunk_index: int
    
    def to_context_block(self, include_citation: bool = True) -> str:
        """Format as a context block for LLM prompts."""
        if include_citation:
            return f"---\n{self.citation.to_citation_string()}\n{self.content}\n---"
        return self.content


@dataclass
class RAGResult:
    """Result from a RAG query."""
    query: str
    chunks: list[RetrievedChunk] = field(default_factory=list)
    total_tokens_estimate: int = 0
    
    def build_context(
        self,
        max_tokens: int = 4000,
        include_citations: bool = True,
    ) -> str:
        """
        Build a context string from retrieved chunks.
        
        Args:
            max_tokens: Maximum tokens to include (rough estimate)
            include_citations: Whether to include citation markers
            
        Returns:
            Formatted context string
        """
        context_parts = []
        token_count = 0
        chars_per_token = 4  # Rough estimate
        
        for chunk in self.chunks:
            chunk_text = chunk.to_context_block(include_citations)
            chunk_tokens = len(chunk_text) // chars_per_token
            
            if token_count + chunk_tokens > max_tokens:
                break
            
            context_parts.append(chunk_text)
            token_count += chunk_tokens
        
        self.total_tokens_estimate = token_count
        return "\n\n".join(context_parts)
    
    def get_citations(self) -> list[Citation]:
        """Get all citations from retrieved chunks."""
        return [chunk.citation for chunk in self.chunks]
    
    def get_citation_summary(self) -> str:
        """Get a summary of all citations for reference."""
        citations = self.get_citations()
        if not citations:
            return "No sources retrieved."
        
        lines = ["Sources used:"]
        for i, citation in enumerate(citations, 1):
            lines.append(f"  {i}. {citation.to_citation_string()} - {citation.content_preview[:50]}...")
        
        return "\n".join(lines)


class RAGService:
    """
    Service for retrieval-augmented generation.
    
    Uses pgvector for similarity search and tracks citations
    for grounded, verifiable content generation.
    """
    
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.embeddings = embedding_service or get_embedding_service()
    
    def retrieve(
        self,
        query: str,
        project_id: UUID,
        db: Session,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        source_material_ids: Optional[list[UUID]] = None,
    ) -> RAGResult:
        """
        Retrieve relevant chunks for a query using pgvector similarity search.
        
        Args:
            query: The search query
            project_id: Project to search within
            db: Database session
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            source_material_ids: Optional filter by specific source materials
            
        Returns:
            RAGResult with retrieved chunks and citations
        """
        # Generate query embedding
        query_embedding = self.embeddings.embed_text(query)
        
        if query_embedding.dimensions != 1536:
            logger.warning(
                f"Query embedding has {query_embedding.dimensions} dims, "
                "expected 1536 for pgvector. Results may be incorrect."
            )
        
        # Build the pgvector similarity query
        # Using cosine distance: <=> operator
        # Note: pgvector returns DISTANCE, not similarity
        # similarity = 1 - distance
        
        embedding_str = "[" + ",".join(str(x) for x in query_embedding.embedding) + "]"
        
        # Base query with pgvector cosine distance
        # IMPORTANT: use `(:query_embedding)::vector` (not `:query_embedding::vector`)
        # so SQLAlchemy binds the parameter correctly before PostgreSQL casts it.
        sql = text("""
            SELECT 
                cc.id,
                cc.content,
                cc.chunk_index,
                cc.word_count,
                cc.source_reference,
                cc.source_material_id,
                sm.filename,
                1 - (cc.embedding <=> (:query_embedding)::vector) as similarity
            FROM content_chunks cc
            JOIN source_materials sm ON cc.source_material_id = sm.id
            WHERE cc.project_id = :project_id
              AND cc.embedding IS NOT NULL
              AND 1 - (cc.embedding <=> (:query_embedding)::vector) >= :threshold
            ORDER BY cc.embedding <=> (:query_embedding)::vector
            LIMIT :top_k
        """)
        
        params = {
            "query_embedding": embedding_str,
            "project_id": str(project_id),
            "threshold": similarity_threshold,
            "top_k": top_k,
        }
        
        try:
            result = db.execute(sql, params)
            rows = result.fetchall()
        except Exception as e:
            logger.error(f"pgvector query failed: {e}")
            # Ensure the session is usable for fallback queries/commits
            try:
                db.rollback()
            except Exception:
                pass
            # Fall back to non-vector retrieval
            return self._fallback_retrieve(query, project_id, db, top_k)
        
        # Build results
        chunks = []
        for row in rows:
            citation = Citation(
                chunk_id=row.id,
                source_material_id=row.source_material_id,
                source_reference=row.source_reference,
                source_filename=row.filename,
                content_preview=row.content[:200] if row.content else "",
                similarity_score=row.similarity,
            )
            
            chunk = RetrievedChunk(
                content=row.content,
                citation=citation,
                word_count=row.word_count or len(row.content.split()),
                chunk_index=row.chunk_index,
            )
            chunks.append(chunk)
        
        logger.info(f"RAG retrieved {len(chunks)} chunks for query: {query[:50]}...")
        
        return RAGResult(query=query, chunks=chunks)
    
    def _fallback_retrieve(
        self,
        query: str,
        project_id: UUID,
        db: Session,
        top_k: int,
    ) -> RAGResult:
        """
        Fallback retrieval when pgvector is unavailable.
        Uses simple text matching.
        """
        logger.warning("Using fallback retrieval (no vector search)")
        
        # Import model inside function to avoid circular imports
        from app.models.content_chunk import ContentChunk
        
        # Simple keyword-based retrieval
        keywords = query.lower().split()[:5]  # First 5 words
        
        chunks_query = db.query(ContentChunk).filter(
            ContentChunk.project_id == project_id
        )
        
        # Get all chunks and score by keyword overlap
        all_chunks = chunks_query.all()
        scored = []
        
        for chunk in all_chunks:
            content_lower = chunk.content.lower()
            score = sum(1 for kw in keywords if kw in content_lower) / max(len(keywords), 1)
            if score > 0:
                scored.append((chunk, score))
        
        # Sort by score and take top_k
        scored.sort(key=lambda x: x[1], reverse=True)
        top_chunks = scored[:top_k]
        
        results = []
        for chunk, score in top_chunks:
            source_material = chunk.source_material
            citation = Citation(
                chunk_id=chunk.id,
                source_material_id=chunk.source_material_id,
                source_reference=chunk.source_reference,
                source_filename=source_material.filename if source_material else None,
                content_preview=chunk.content[:200],
                similarity_score=score,
            )
            
            results.append(RetrievedChunk(
                content=chunk.content,
                citation=citation,
                word_count=chunk.word_count or len(chunk.content.split()),
                chunk_index=chunk.chunk_index,
            ))
        
        return RAGResult(query=query, chunks=results)
    
    def retrieve_for_chapter(
        self,
        chapter_outline: dict,
        project_id: UUID,
        db: Session,
        top_k: int = 10,
    ) -> RAGResult:
        """
        Retrieve chunks relevant to a chapter outline.
        
        Uses the chapter title, summary, and key points to build the query.
        """
        # Build a comprehensive query from the chapter outline
        query_parts = []
        
        if "title" in chapter_outline:
            query_parts.append(chapter_outline["title"])
        
        if "summary" in chapter_outline:
            query_parts.append(chapter_outline["summary"])
        
        if "key_points" in chapter_outline:
            query_parts.extend(chapter_outline["key_points"][:3])
        
        query = " ".join(query_parts)
        
        return self.retrieve(
            query=query,
            project_id=project_id,
            db=db,
            top_k=top_k,
        )
    
    def retrieve_for_fact_check(
        self,
        claim: str,
        project_id: UUID,
        db: Session,
        top_k: int = 3,
        similarity_threshold: float = 0.5,  # Higher threshold for fact checking
    ) -> RAGResult:
        """
        Retrieve chunks that might support or refute a claim.
        
        Uses a higher similarity threshold to ensure relevance.
        """
        return self.retrieve(
            query=claim,
            project_id=project_id,
            db=db,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )


# Global singleton
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get the global RAG service instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def reset_rag_service():
    """Reset the global RAG service (for testing)."""
    global _rag_service
    _rag_service = None

