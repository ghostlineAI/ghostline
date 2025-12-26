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
            # Cap to keep providers happy; this is a *voice anchor* not full-document retrieval.
            embedding_result = self.embeddings.embed_text(combined_text[:8000])
            
            # Analyze style with LLM (optional, can be done separately)
            style_description = self._analyze_style(sample_texts)

            # Extract deterministic stylometry features + phrase lists for stronger prompt guidance
            try:
                from app.services.voice_metrics import VoiceMetricsService

                voice_metrics = VoiceMetricsService(embedding_service=self.embeddings)
                styl = voice_metrics.extract_features(combined_text)
            except Exception:
                styl = None

            common_phrases, sentence_starters, transition_words = self._extract_voice_phrase_lists(sample_texts)
            
            # Create or update voice profile
            existing_profile = db.query(VoiceProfile).filter(
                VoiceProfile.project_id == project.id
            ).first()
            
            if existing_profile:
                existing_profile.voice_embedding = embedding_result.embedding
                existing_profile.style_description = style_description
                existing_profile.sample_text = combined_text[:2000]
                existing_profile.common_phrases = common_phrases
                existing_profile.sentence_starters = sentence_starters
                existing_profile.transition_words = transition_words
                if styl is not None:
                    existing_profile.avg_sentence_length = styl.avg_sentence_length
                    existing_profile.sentence_length_std = styl.sentence_length_std
                    existing_profile.avg_word_length = styl.avg_word_length
                    existing_profile.vocabulary_complexity = styl.vocabulary_complexity
                    existing_profile.vocabulary_richness = styl.vocabulary_richness
                    existing_profile.punctuation_density = styl.punctuation_density
                    existing_profile.question_ratio = styl.question_ratio
                    existing_profile.exclamation_ratio = styl.exclamation_ratio
                    existing_profile.avg_paragraph_length = styl.avg_paragraph_length
                    existing_profile.stylistic_elements = {
                        **(existing_profile.stylistic_elements or {}),
                        "stylometry": {
                            "avg_sentence_length": styl.avg_sentence_length,
                            "sentence_length_std": styl.sentence_length_std,
                            "avg_word_length": styl.avg_word_length,
                            "vocabulary_complexity": styl.vocabulary_complexity,
                            "vocabulary_richness": styl.vocabulary_richness,
                            "punctuation_density": styl.punctuation_density,
                            "question_ratio": styl.question_ratio,
                            "exclamation_ratio": styl.exclamation_ratio,
                            "comma_density": styl.comma_density,
                            "semicolon_density": styl.semicolon_density,
                            "avg_paragraph_length": styl.avg_paragraph_length,
                            "paragraph_count": styl.paragraph_count,
                            "sentence_count": styl.sentence_count,
                            "total_words": styl.total_words,
                            "total_characters": styl.total_characters,
                        },
                    }
                profile = existing_profile
            else:
                profile = VoiceProfile(
                    project_id=project.id,
                    voice_embedding=embedding_result.embedding,
                    style_description=style_description,
                    sample_text=combined_text[:2000],
                    common_phrases=common_phrases,
                    sentence_starters=sentence_starters,
                    transition_words=transition_words,
                    avg_sentence_length=getattr(styl, "avg_sentence_length", None) if styl is not None else None,
                    sentence_length_std=getattr(styl, "sentence_length_std", None) if styl is not None else None,
                    avg_word_length=getattr(styl, "avg_word_length", None) if styl is not None else None,
                    vocabulary_complexity=getattr(styl, "vocabulary_complexity", None) if styl is not None else None,
                    vocabulary_richness=getattr(styl, "vocabulary_richness", None) if styl is not None else None,
                    punctuation_density=getattr(styl, "punctuation_density", None) if styl is not None else None,
                    question_ratio=getattr(styl, "question_ratio", None) if styl is not None else None,
                    exclamation_ratio=getattr(styl, "exclamation_ratio", None) if styl is not None else None,
                    avg_paragraph_length=getattr(styl, "avg_paragraph_length", None) if styl is not None else None,
                    stylistic_elements=(
                        {
                            "stylometry": {
                                "avg_sentence_length": styl.avg_sentence_length,
                                "sentence_length_std": styl.sentence_length_std,
                                "avg_word_length": styl.avg_word_length,
                                "vocabulary_complexity": styl.vocabulary_complexity,
                                "vocabulary_richness": styl.vocabulary_richness,
                                "punctuation_density": styl.punctuation_density,
                                "question_ratio": styl.question_ratio,
                                "exclamation_ratio": styl.exclamation_ratio,
                                "comma_density": styl.comma_density,
                                "semicolon_density": styl.semicolon_density,
                                "avg_paragraph_length": styl.avg_paragraph_length,
                                "paragraph_count": styl.paragraph_count,
                                "sentence_count": styl.sentence_count,
                                "total_words": styl.total_words,
                                "total_characters": styl.total_characters,
                            }
                        }
                        if styl is not None
                        else {}
                    ),
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

    def _extract_voice_phrase_lists(self, sample_texts: list[str]) -> tuple[list[str], list[str], list[str]]:
        """
        Deterministically extract lightweight phrase lists to help steer voice:
        - common_phrases (bigrams/trigrams)
        - sentence_starters (first 1-2 words of sentences)
        - transition_words (frequent transition words/phrases)
        """
        import re
        from collections import Counter

        combined = "\n\n".join(t for t in sample_texts if t).strip()
        if not combined:
            return [], [], []

        # Sentence starters
        sentence_split = re.split(r"(?<=[.!?])\s+", combined)
        starters: Counter[str] = Counter()
        word_pat = re.compile(r"\b\w+\b")
        for s in sentence_split:
            w = word_pat.findall(s.lower())
            if len(w) >= 2:
                starters[" ".join(w[:2])] += 1
            elif len(w) == 1:
                starters[w[0]] += 1
        sentence_starters = [p for p, c in starters.most_common(20) if c >= 2][:10]

        # Common phrases (bigrams/trigrams)
        stop = {
            "the", "a", "an", "and", "or", "but", "if", "then", "to", "of", "in", "on", "for", "with",
            "is", "are", "was", "were", "be", "been", "it", "that", "this", "i", "you", "we", "they",
        }
        words = [w for w in word_pat.findall(combined.lower()) if w]
        bigrams = Counter()
        trigrams = Counter()
        for i in range(len(words) - 1):
            w1, w2 = words[i], words[i + 1]
            if w1 in stop and w2 in stop:
                continue
            bigrams[f"{w1} {w2}"] += 1
        for i in range(len(words) - 2):
            w1, w2, w3 = words[i], words[i + 1], words[i + 2]
            if w1 in stop and w2 in stop and w3 in stop:
                continue
            trigrams[f"{w1} {w2} {w3}"] += 1
        common_phrases = [p for p, c in (trigrams + bigrams).most_common(30) if c >= 2][:10]

        # Transition words (hand-curated set, counted in samples)
        transitions = [
            "but", "and", "so", "because", "however", "still", "yet", "instead",
            "also", "especially", "for example", "for instance", "in other words",
            "in practice", "at the same time", "on the other hand", "in the end",
        ]
        lower = combined.lower()
        trans_counts: Counter[str] = Counter()
        for t in transitions:
            # crude whole-phrase count
            trans_counts[t] = lower.count(t)
        transition_words = [t for t, c in trans_counts.most_common(20) if c > 0][:12]

        return common_phrases, sentence_starters, transition_words
    
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
