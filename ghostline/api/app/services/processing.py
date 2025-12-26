"""
Processing Service for source material ingestion and chunking.

Handles:
- Document text extraction
- Text chunking for RAG
- Embedding generation for chunks
- Voice profile creation from writing samples
"""

import os
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.content_chunk import ContentChunk
from app.models.project import Project
from app.models.source_material import ProcessingStatus, SourceMaterial
from app.models.voice_profile import VoiceProfile
from app.services.document_processor import (
    DocumentProcessor,
    ExtractedText,
    get_document_processor,
)
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.storage import StorageService


@dataclass
class ProcessingResult:
    """Result from processing a source material."""
    material_id: UUID
    chunks_created: int
    total_words: int
    status: ProcessingStatus
    error_message: Optional[str] = None


@dataclass 
class VoiceProfileResult:
    """Result from creating a voice profile."""
    profile_id: UUID
    embedding_dimensions: int
    style_description: str
    samples_analyzed: int


class ProcessingService:
    """
    Service for processing source materials.
    
    Handles the ingestion pipeline:
    1. Extract text from uploaded documents
    2. Chunk text for RAG retrieval
    3. Generate embeddings for each chunk
    4. Store chunks in database
    """
    
    def __init__(
        self,
        document_processor: Optional[DocumentProcessor] = None,
        embedding_service: Optional[EmbeddingService] = None,
        storage_service: Optional[StorageService] = None,
    ):
        self.doc_processor = document_processor or get_document_processor()
        self.embeddings = embedding_service or get_embedding_service()
        self.storage = storage_service or StorageService()
    
    def process_source_material(
        self,
        material: SourceMaterial,
        db: Session,
    ) -> ProcessingResult:
        """
        Process a source material: extract text, chunk, and embed.
        
        Args:
            material: The SourceMaterial to process
            db: Database session
            
        Returns:
            ProcessingResult with processing status
        """
        cost_token = None
        try:
            # Ensure all ingestion-time AI calls (VLM + embeddings) are recorded.
            from agents.base.agent import set_cost_context, clear_cost_context
            cost_token = set_cost_context(
                project_id=material.project_id,
                task_id=None,
                workflow_run_id=f"ingest_{material.id}",
                db_session=db,
            )
        except Exception:
            clear_cost_context = None  # type: ignore

        try:
            # Update status to processing
            material.processing_status = ProcessingStatus.PROCESSING
            db.commit()
            
            # Get file content
            file_content = self._get_file_content(material)
            if not file_content:
                material.processing_status = ProcessingStatus.FAILED
                material.processing_error = "Could not retrieve file content"
                db.commit()
                return ProcessingResult(
                    material_id=material.id,
                    chunks_created=0,
                    total_words=0,
                    status=ProcessingStatus.FAILED,
                    error_message="Could not retrieve file content",
                )
            
            # Extract text
            extracted = self.doc_processor.extract_from_bytes(
                content=file_content,
                filename=material.filename,
            )
            
            # Store extracted content
            material.extracted_content = extracted.content
            material.word_count = extracted.word_count
            
            # Create chunks
            chunks_created = self._create_chunks(
                material=material,
                extracted=extracted,
                db=db,
            )
            
            # Update status
            material.processing_status = ProcessingStatus.COMPLETED
            db.commit()
            
            return ProcessingResult(
                material_id=material.id,
                chunks_created=chunks_created,
                total_words=extracted.word_count,
                status=ProcessingStatus.COMPLETED,
            )
            
        except Exception as e:
            material.processing_status = ProcessingStatus.FAILED
            material.processing_error = str(e)
            db.commit()
            
            return ProcessingResult(
                material_id=material.id,
                chunks_created=0,
                total_words=0,
                status=ProcessingStatus.FAILED,
                error_message=str(e),
            )
        finally:
            if cost_token is not None and clear_cost_context is not None:
                try:
                    clear_cost_context(cost_token)
                except Exception:
                    pass
    
    def _get_file_content(self, material: SourceMaterial) -> Optional[bytes]:
        """Get file content from storage."""
        # Try local storage first
        if material.local_path and os.path.exists(material.local_path):
            with open(material.local_path, 'rb') as f:
                return f.read()
        
        # Try to get from storage service
        try:
            content = self.storage.get_file_content(material.s3_key)
            if isinstance(content, str):
                return content.encode('utf-8')
            return content
        except Exception:
            return None
    
    def _create_chunks(
        self,
        material: SourceMaterial,
        extracted: ExtractedText,
        db: Session,
    ) -> int:
        """Create content chunks with embeddings."""
        # Delete existing chunks for this material
        db.query(ContentChunk).filter(
            ContentChunk.source_material_id == material.id
        ).delete()
        
        if not extracted.chunks:
            return 0
        
        # Generate embeddings for all chunks
        embedding_results = self.embeddings.embed_texts(extracted.chunks)
        
        # Create chunk records
        chunks_created = 0
        for i, (chunk_text, emb_result) in enumerate(zip(extracted.chunks, embedding_results)):
            chunk = ContentChunk(
                source_material_id=material.id,
                project_id=material.project_id,
                content=chunk_text,
                chunk_index=i,
                word_count=len(chunk_text.split()),
                embedding=emb_result.embedding,
            )
            db.add(chunk)
            chunks_created += 1
        
        db.commit()
        return chunks_created
    
    def create_voice_profile(
        self,
        project: Project,
        writing_samples: list[SourceMaterial],
        db: Session,
    ) -> VoiceProfileResult:
        """
        Create a voice profile from writing samples.
        
        Args:
            project: The project to create profile for
            writing_samples: Source materials marked as writing samples
            db: Database session
            
        Returns:
            VoiceProfileResult with profile details
        """
        cost_token = None
        clear_cost_context = None  # set if we successfully import it
        try:
            from agents.base.agent import set_cost_context, clear_cost_context
            cost_token = set_cost_context(
                project_id=project.id,
                task_id=None,
                workflow_run_id=f"voice_profile_{project.id}",
                db_session=db,
            )
        except Exception:
            clear_cost_context = None  # type: ignore
        try:
            # Collect text from writing samples
            sample_texts = []
            for material in writing_samples:
                if material.extracted_content:
                    sample_texts.append(material.extracted_content[:5000])  # First 5k chars
            
            if not sample_texts:
                raise ValueError("No text content in writing samples")
            
            # Combine and create embedding
            combined_text = "\n\n---\n\n".join(sample_texts)
            embedding_result = self.embeddings.embed_text(combined_text)
            
            # Analyze style with LLM (optional, can be done separately)
            style_description = self._analyze_style(sample_texts)
            
            # Create or update voice profile
            existing_profile = db.query(VoiceProfile).filter(
                VoiceProfile.project_id == project.id
            ).first()
            
            if existing_profile:
                existing_profile.voice_embedding = embedding_result.embedding
                existing_profile.style_description = style_description
                profile = existing_profile
            else:
                profile = VoiceProfile(
                    project_id=project.id,
                    voice_embedding=embedding_result.embedding,
                    style_description=style_description,
                )
                db.add(profile)
            
            db.commit()
            db.refresh(profile)
            
            return VoiceProfileResult(
                profile_id=profile.id,
                embedding_dimensions=embedding_result.dimensions,
                style_description=style_description,
                samples_analyzed=len(sample_texts),
            )
        finally:
            if cost_token is not None and clear_cost_context is not None:
                try:
                    clear_cost_context(cost_token)
                except Exception:
                    pass
    
    def _analyze_style(self, sample_texts: list[str]) -> str:
        """Basic style analysis without LLM."""
        import re
        
        combined = " ".join(sample_texts)
        
        # Basic metrics
        words = combined.split()
        sentences = re.split(r'[.!?]+', combined)
        
        word_count = len(words)
        sentence_count = len([s for s in sentences if s.strip()])
        avg_sentence_length = word_count / max(sentence_count, 1)
        
        # Vocabulary diversity
        unique_words = len(set(w.lower() for w in words))
        vocab_diversity = unique_words / max(word_count, 1)
        
        # Build description
        length_desc = "short" if avg_sentence_length < 15 else "medium" if avg_sentence_length < 25 else "long"
        vocab_desc = "simple" if vocab_diversity < 0.4 else "moderate" if vocab_diversity < 0.6 else "rich"
        
        return f"Writing style with {length_desc} sentences ({avg_sentence_length:.1f} words avg) and {vocab_desc} vocabulary diversity ({vocab_diversity:.2f})."
    
    def find_relevant_chunks(
        self,
        query: str,
        project_id: UUID,
        db: Session,
        top_k: int = 10,
    ) -> list[ContentChunk]:
        """
        Find content chunks most relevant to a query (RAG retrieval).
        
        Args:
            query: The query text
            project_id: Project to search within
            db: Database session
            top_k: Number of chunks to return
            
        Returns:
            List of most relevant ContentChunks
        """
        # Generate query embedding
        query_embedding = self.embeddings.embed_text(query)
        
        # Get all chunks for the project
        chunks = db.query(ContentChunk).filter(
            ContentChunk.project_id == project_id
        ).all()
        
        if not chunks:
            return []
        
        # Get embeddings and find similar
        chunk_embeddings = [c.embedding for c in chunks if c.embedding]
        
        if not chunk_embeddings:
            return chunks[:top_k]  # Return first chunks if no embeddings
        
        # Find most similar
        similar_indices = self.embeddings.find_most_similar(
            query_embedding=query_embedding.embedding,
            candidate_embeddings=chunk_embeddings,
            top_k=top_k,
        )
        
        # Return chunks in order of relevance
        return [chunks[idx] for idx, _ in similar_indices]
    
    def reprocess_material(
        self,
        material_id: UUID,
        db: Session,
    ) -> ProcessingResult:
        """
        Reprocess a source material (useful after updating chunk settings).
        
        Args:
            material_id: ID of material to reprocess
            db: Database session
            
        Returns:
            ProcessingResult
        """
        material = db.query(SourceMaterial).filter(
            SourceMaterial.id == material_id
        ).first()
        
        if not material:
            return ProcessingResult(
                material_id=material_id,
                chunks_created=0,
                total_words=0,
                status=ProcessingStatus.FAILED,
                error_message="Material not found",
            )
        
        return self.process_source_material(material, db)


# Singleton
_processing_service: Optional[ProcessingService] = None


def get_processing_service() -> ProcessingService:
    """Get the global processing service instance."""
    global _processing_service
    if _processing_service is None:
        _processing_service = ProcessingService()
    return _processing_service
