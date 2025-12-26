"""
Embedding Service for vector representations of text.

Primary: OpenAI text-embedding-3-small (1536 dimensions)
Fallback: sentence-transformers for offline/testing

Provides text embeddings for:
- Voice profile analysis
- Source material chunking and retrieval (RAG)
- Content chunk similarity search
"""

import os
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def _extract_openai_embedding_tokens(response) -> int:
    """
    Best-effort extraction of token usage from the OpenAI embeddings response.
    
    The OpenAI python SDK has changed response types across versions, so we handle
    both attribute-style and dict-style access.
    """
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return 0

    # Attribute-style usage objects
    for key in ("total_tokens", "prompt_tokens", "input_tokens"):
        val = getattr(usage, key, None)
        if isinstance(val, int):
            return val

    # Dict-style usage
    if isinstance(usage, dict):
        for key in ("total_tokens", "prompt_tokens", "input_tokens"):
            val = usage.get(key)
            if isinstance(val, int):
                return val

    return 0


def _record_embedding_usage(
    *,
    agent_name: str,
    provider: str,
    model: str,
    input_tokens: int,
    embedding_dimensions: Optional[int],
    duration_ms: int,
    success: bool,
    error_message: Optional[str] = None,
    batch_size: Optional[int] = None,
    extra_data: Optional[dict] = None,
):
    """
    Record an embedding call to the LLM usage log if cost context is available.
    
    This allows embedding costs to be aggregated alongside chat/vision calls.
    """
    try:
        from agents.base.agent import get_cost_context
    except Exception:
        return

    ctx = get_cost_context()
    db = ctx.get("db_session")
    if not db:
        return

    try:
        from app.services.cost_tracker import CostTracker

        tracker = CostTracker(db)
        tracker.record(
            agent_name=agent_name,
            agent_role="embedding",
            provider=provider,
            model=model,
            call_type="embedding",
            input_tokens=int(input_tokens or 0),
            output_tokens=0,
            duration_ms=int(duration_ms or 0),
            success=bool(success),
            error_message=error_message,
            embedding_dimensions=embedding_dimensions,
            project_id=ctx.get("project_id"),
            task_id=ctx.get("task_id"),
            workflow_run_id=ctx.get("workflow_run_id"),
            chapter_number=ctx.get("chapter_number"),
            metadata={
                "batch_size": batch_size,
                **(extra_data or {}),
            },
        )
    except Exception as e:
        # Cost tracking must never break embeddings.
        logger.warning(f"Failed to record embedding usage: {e}")


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    OPENAI = "openai"
    LOCAL = "local"  # sentence-transformers


@dataclass
class EmbeddingResult:
    """Result from an embedding operation."""
    embedding: list[float]
    model: str
    dimensions: int
    text_length: int
    provider: EmbeddingProvider


@dataclass
class EmbeddingConfig:
    """Configuration for the embedding service."""
    provider: EmbeddingProvider = EmbeddingProvider.OPENAI
    openai_model: str = "text-embedding-3-small"  # 1536 dimensions
    local_model: str = "all-mpnet-base-v2"  # 768 dimensions (will NOT pad)
    target_dimensions: int = 1536
    batch_size: int = 100
    
    # When using local model, we project to target_dimensions using a learned projection
    # For now, we require OpenAI for production (1536 native)
    allow_dimension_mismatch: bool = False


class BaseEmbeddingClient(ABC):
    """Abstract base class for embedding clients."""
    
    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        pass
    
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (batched)."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name."""
        pass
    
    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimensions."""
        pass


class OpenAIEmbeddingClient(BaseEmbeddingClient):
    """OpenAI embedding client using text-embedding-3-small."""
    
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self._client = None
        self._dimensions = 1536  # text-embedding-3-small native dimension
    
    @property
    def client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self._client = OpenAI(api_key=api_key)
        return self._client
    
    @property
    def model_name(self) -> str:
        return self.model
    
    @property
    def dimensions(self) -> int:
        return self._dimensions
    
    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text using OpenAI."""
        if not text or not text.strip():
            return [0.0] * self._dimensions

        start = time.time()
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            duration_ms = int((time.time() - start) * 1000)
            input_tokens = _extract_openai_embedding_tokens(response)
            _record_embedding_usage(
                agent_name="OpenAIEmbeddingClient",
                provider="openai",
                model=self.model,
                input_tokens=input_tokens,
                embedding_dimensions=self._dimensions,
                duration_ms=duration_ms,
                success=True,
                batch_size=1,
                extra_data={"text_length": len(text)},
            )
            return response.data[0].embedding
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            _record_embedding_usage(
                agent_name="OpenAIEmbeddingClient",
                provider="openai",
                model=self.model,
                input_tokens=0,
                embedding_dimensions=self._dimensions,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e),
                batch_size=1,
                extra_data={"text_length": len(text)},
            )
            raise
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts using OpenAI (batched)."""
        if not texts:
            return []
        
        # Filter empty texts but track indices
        non_empty = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
        
        if not non_empty:
            return [[0.0] * self._dimensions for _ in texts]
        
        # Batch request to OpenAI
        indices, valid_texts = zip(*non_empty)
        
        start = time.time()
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=list(valid_texts),
            )
            duration_ms = int((time.time() - start) * 1000)
            input_tokens = _extract_openai_embedding_tokens(response)
            _record_embedding_usage(
                agent_name="OpenAIEmbeddingClient",
                provider="openai",
                model=self.model,
                input_tokens=input_tokens,
                embedding_dimensions=self._dimensions,
                duration_ms=duration_ms,
                success=True,
                batch_size=len(valid_texts),
                extra_data={"total_inputs": len(texts)},
            )
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            _record_embedding_usage(
                agent_name="OpenAIEmbeddingClient",
                provider="openai",
                model=self.model,
                input_tokens=0,
                embedding_dimensions=self._dimensions,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e),
                batch_size=len(valid_texts),
                extra_data={"total_inputs": len(texts)},
            )
            raise
        
        # Map back to original positions
        results = [[0.0] * self._dimensions for _ in texts]
        for i, emb_data in enumerate(response.data):
            original_idx = indices[i]
            results[original_idx] = emb_data.embedding
        
        return results


class LocalEmbeddingClient(BaseEmbeddingClient):
    """Local embedding client using sentence-transformers (for offline/testing)."""
    
    def __init__(self, model: str = "all-mpnet-base-v2"):
        self._model_name = model
        self._model = None
        self._dimensions: Optional[int] = None  # Will be set when model loads or fallback initializes
        self._use_hash_fallback = False
    
    def _hash_embed(self, text: str, dims: int) -> list[float]:
        """
        Lightweight deterministic local embedding fallback (no heavy deps).
        
        This is *not* intended to match OpenAI embedding quality; it exists so
        the system can run offline/unit tests without requiring torch +
        sentence-transformers.
        """
        import hashlib
        import re
        
        if not text or not text.strip():
            return [0.0] * dims
        
        # Tokenize into simple word-like units
        tokens = re.findall(r"[A-Za-z0-9']+", text.lower())
        if not tokens:
            return [0.0] * dims
        
        vec = np.zeros(dims, dtype=np.float32)
        for tok in tokens:
            digest = hashlib.sha256(tok.encode("utf-8")).digest()
            # Stable bucket
            idx = int.from_bytes(digest[:4], "little") % dims
            # Stable sign
            sign = 1.0 if (digest[4] & 1) == 0 else -1.0
            vec[idx] += sign
        
        norm = float(np.linalg.norm(vec))
        if norm == 0.0:
            return [0.0] * dims
        vec /= norm
        return vec.tolist()
    
    @property
    def model(self):
        """Lazy-load the sentence-transformers model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
                # Get actual dimensions from the model
                test_emb = self._model.encode("test", normalize_embeddings=True)
                self._dimensions = len(test_emb)
                self._use_hash_fallback = False
                logger.info(
                    f"Loaded local embedding model: {self._model_name} ({self._dimensions} dims)"
                )
            except ModuleNotFoundError:
                # Graceful fallback: deterministic hash embeddings
                self._use_hash_fallback = True
                self._dimensions = 1536
                self._model = None
                logger.warning(
                    "sentence-transformers not installed; using deterministic hash embeddings "
                    "for LOCAL provider (offline/testing only)."
                )
        return self._model
    
    @property
    def model_name(self) -> str:
        # If we couldn't load sentence-transformers, report a clear fallback model name.
        if self._use_hash_fallback:
            return f"local-hash-{self.dimensions}"
        return self._model_name
    
    @property
    def dimensions(self) -> int:
        if self._dimensions is None:
            # Trigger model load to get dimensions
            _ = self.model
        return self._dimensions or 1536
    
    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text using sentence-transformers."""
        if not text or not text.strip():
            return [0.0] * self.dimensions

        start = time.time()
        try:
            _ = self.model  # ensures fallback flag/dims are set
            if self._use_hash_fallback:
                emb = self._hash_embed(text, self.dimensions)
            else:
                embedding = self.model.encode(text, normalize_embeddings=True)
                emb = embedding.tolist()

            duration_ms = int((time.time() - start) * 1000)
            _record_embedding_usage(
                agent_name="LocalEmbeddingClient",
                provider="local",
                model=self.model_name,
                input_tokens=0,
                embedding_dimensions=self.dimensions,
                duration_ms=duration_ms,
                success=True,
                batch_size=1,
                extra_data={"text_length": len(text), "hash_fallback": bool(self._use_hash_fallback)},
            )
            return emb
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            _record_embedding_usage(
                agent_name="LocalEmbeddingClient",
                provider="local",
                model=self.model_name,
                input_tokens=0,
                embedding_dimensions=self.dimensions,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e),
                batch_size=1,
                extra_data={"text_length": len(text), "hash_fallback": bool(self._use_hash_fallback)},
            )
            raise
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts using sentence-transformers."""
        if not texts:
            return []

        start = time.time()
        try:
            _ = self.model  # ensures fallback flag/dims are set
            if self._use_hash_fallback:
                results = [self._hash_embed(t, self.dimensions) for t in texts]
            else:
                # Handle empty texts
                non_empty_mask = [bool(t and t.strip()) for t in texts]
                valid_texts = [t for t, valid in zip(texts, non_empty_mask) if valid]

                if not valid_texts:
                    results = [[0.0] * self.dimensions for _ in texts]
                else:
                    # Batch encode
                    embeddings = self.model.encode(valid_texts, normalize_embeddings=True)

                    # Map back to original positions
                    results = []
                    valid_idx = 0
                    for is_valid in non_empty_mask:
                        if is_valid:
                            results.append(embeddings[valid_idx].tolist())
                            valid_idx += 1
                        else:
                            results.append([0.0] * self.dimensions)

            duration_ms = int((time.time() - start) * 1000)
            _record_embedding_usage(
                agent_name="LocalEmbeddingClient",
                provider="local",
                model=self.model_name,
                input_tokens=0,
                embedding_dimensions=self.dimensions,
                duration_ms=duration_ms,
                success=True,
                batch_size=len(texts),
                extra_data={"hash_fallback": bool(self._use_hash_fallback)},
            )
            return results
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            _record_embedding_usage(
                agent_name="LocalEmbeddingClient",
                provider="local",
                model=self.model_name,
                input_tokens=0,
                embedding_dimensions=self.dimensions,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e),
                batch_size=len(texts),
                extra_data={"hash_fallback": bool(self._use_hash_fallback)},
            )
            raise


class EmbeddingService:
    """
    Unified service for generating text embeddings.
    
    Uses OpenAI text-embedding-3-small (1536 dimensions) by default.
    Falls back to sentence-transformers for offline/testing.
    
    IMPORTANT: The database schema expects 1536-dimensional vectors.
    When using local models, we WARN if dimensions don't match.
    """
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self._client: Optional[BaseEmbeddingClient] = None
        self._initialized = False
    
    @property
    def client(self) -> BaseEmbeddingClient:
        """Get the embedding client, initializing if needed."""
        if self._client is None:
            self._client = self._create_client()
            self._initialized = True
        return self._client
    
    def _create_client(self) -> BaseEmbeddingClient:
        """Create the appropriate embedding client based on config."""
        strict_mode = os.getenv("GHOSTLINE_STRICT_MODE", "").strip().lower() in ("1", "true", "yes", "on")
        if self.config.provider == EmbeddingProvider.OPENAI:
            # Try OpenAI first
            try:
                client = OpenAIEmbeddingClient(model=self.config.openai_model)
                # Test that it works
                _ = client.client  # This will raise if API key missing
                logger.info(f"Using OpenAI embeddings: {self.config.openai_model}")
                return client
            except Exception as e:
                if strict_mode:
                    raise
                logger.warning(f"OpenAI embeddings unavailable ({e}), falling back to local")
                # IMPORTANT: reflect actual provider so audits don't lie.
                self.config.provider = EmbeddingProvider.LOCAL
                return self._create_local_client()
        else:
            return self._create_local_client()
    
    def _create_local_client(self) -> LocalEmbeddingClient:
        """Create a local embedding client."""
        client = LocalEmbeddingClient(model=self.config.local_model)
        
        # Warn about dimension mismatch
        if client.dimensions != self.config.target_dimensions:
            if not self.config.allow_dimension_mismatch:
                logger.warning(
                    f"Local embedding model produces {client.dimensions} dims, "
                    f"but database expects {self.config.target_dimensions} dims. "
                    "This may cause pgvector errors. Set allow_dimension_mismatch=True to suppress."
                )
        
        logger.info(f"Using local embeddings: {self.config.local_model}")
        return client
    
    def embed_text(self, text: str) -> EmbeddingResult:
        """
        Generate an embedding for a single text.
        
        Args:
            text: The text to embed
            
        Returns:
            EmbeddingResult with the embedding vector
        """
        embedding = self.client.embed_text(text)
        
        return EmbeddingResult(
            embedding=embedding,
            model=self.client.model_name,
            dimensions=len(embedding),
            text_length=len(text),
            provider=self.config.provider,
        )
    
    def embed_texts(self, texts: list[str]) -> list[EmbeddingResult]:
        """
        Generate embeddings for multiple texts (batched for efficiency).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of EmbeddingResult objects
        """
        if not texts:
            return []
        
        embeddings = self.client.embed_texts(texts)
        
        results = []
        for text, embedding in zip(texts, embeddings):
            results.append(EmbeddingResult(
                embedding=embedding,
                model=self.client.model_name,
                dimensions=len(embedding),
                text_length=len(text),
                provider=self.config.provider,
            ))
        
        return results
    
    def similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        if len(embedding1) != len(embedding2):
            raise ValueError(
                f"Embedding dimensions must match: {len(embedding1)} vs {len(embedding2)}"
            )
        
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def find_similar(
        self,
        query_embedding: list[float],
        candidate_embeddings: list[list[float]],
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> list[tuple[int, float]]:
        """
        Find the most similar embeddings to a query.
        
        Args:
            query_embedding: The query vector
            candidate_embeddings: List of candidate vectors
            top_k: Number of results to return
            threshold: Minimum similarity score
            
        Returns:
            List of (index, similarity_score) tuples, sorted by similarity
        """
        if not candidate_embeddings:
            return []
        
        similarities = []
        for i, candidate in enumerate(candidate_embeddings):
            if len(candidate) != len(query_embedding):
                continue  # Skip mismatched dimensions
            score = self.similarity(query_embedding, candidate)
            if score >= threshold:
                similarities.append((i, score))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    @property
    def provider(self) -> EmbeddingProvider:
        """Get the current provider."""
        return self.config.provider
    
    @property
    def dimensions(self) -> int:
        """Get the embedding dimensions."""
        return self.client.dimensions


# Global singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def reset_embedding_service():
    """Reset the global embedding service (for testing)."""
    global _embedding_service
    _embedding_service = None
