"""
Embedding Service for vector representations of text.

Provides text embeddings for:
- Voice profile analysis
- Source material chunking and retrieval (RAG)
- Content chunk similarity search
"""

import os
from dataclasses import dataclass
from typing import Optional

import numpy as np

# Lazy imports to avoid loading heavy models until needed
_sentence_transformer = None


def get_sentence_transformer():
    """Lazy load sentence-transformers to avoid startup overhead."""
    global _sentence_transformer
    if _sentence_transformer is None:
        from sentence_transformers import SentenceTransformer
        
        # Use the same model specified in the database (1536 dimensions)
        # all-MiniLM-L6-v2 produces 384 dims, so we use text-embedding-3-small style
        # For local, we'll use a model that can be adjusted
        model_name = os.getenv("EMBEDDING_MODEL", "all-mpnet-base-v2")
        _sentence_transformer = SentenceTransformer(model_name)
    return _sentence_transformer


@dataclass
class EmbeddingResult:
    """Result from an embedding operation."""
    embedding: list[float]
    model: str
    dimensions: int
    text_length: int


class EmbeddingService:
    """
    Service for generating text embeddings.
    
    Uses sentence-transformers for local embedding generation.
    The database expects 1536-dimensional vectors (matching OpenAI's ada-002),
    but we can pad/project smaller embeddings or use a larger model.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", "all-mpnet-base-v2")
        self._model = None
        self._target_dims = 1536  # Database expects this dimension
    
    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model
    
    def embed_text(self, text: str) -> EmbeddingResult:
        """
        Generate an embedding for a single text.
        
        Args:
            text: The text to embed
            
        Returns:
            EmbeddingResult with the embedding vector
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return EmbeddingResult(
                embedding=[0.0] * self._target_dims,
                model=self.model_name,
                dimensions=self._target_dims,
                text_length=0,
            )
        
        # Generate embedding
        embedding = self.model.encode(text, normalize_embeddings=True)
        
        # Convert to list and handle dimension mismatch
        embedding_list = embedding.tolist()
        actual_dims = len(embedding_list)
        
        # Pad or truncate to target dimensions
        if actual_dims < self._target_dims:
            # Pad with zeros
            embedding_list.extend([0.0] * (self._target_dims - actual_dims))
        elif actual_dims > self._target_dims:
            # Truncate
            embedding_list = embedding_list[:self._target_dims]
        
        return EmbeddingResult(
            embedding=embedding_list,
            model=self.model_name,
            dimensions=self._target_dims,
            text_length=len(text),
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
        
        # Filter out empty texts but track indices
        non_empty_indices = []
        non_empty_texts = []
        for i, text in enumerate(texts):
            if text and text.strip():
                non_empty_indices.append(i)
                non_empty_texts.append(text)
        
        # Generate embeddings for non-empty texts
        if non_empty_texts:
            embeddings = self.model.encode(non_empty_texts, normalize_embeddings=True)
        else:
            embeddings = []
        
        # Build results, handling empty texts
        results = []
        embedding_idx = 0
        for i, text in enumerate(texts):
            if i in non_empty_indices:
                emb = embeddings[embedding_idx].tolist()
                embedding_idx += 1
                
                # Pad/truncate
                if len(emb) < self._target_dims:
                    emb.extend([0.0] * (self._target_dims - len(emb)))
                elif len(emb) > self._target_dims:
                    emb = emb[:self._target_dims]
                
                results.append(EmbeddingResult(
                    embedding=emb,
                    model=self.model_name,
                    dimensions=self._target_dims,
                    text_length=len(text),
                ))
            else:
                # Empty text
                results.append(EmbeddingResult(
                    embedding=[0.0] * self._target_dims,
                    model=self.model_name,
                    dimensions=self._target_dims,
                    text_length=0,
                ))
        
        return results
    
    def compute_similarity(
        self,
        embedding1: list[float],
        embedding2: list[float],
    ) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        arr1 = np.array(embedding1)
        arr2 = np.array(embedding2)
        
        # Handle zero vectors
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(arr1, arr2) / (norm1 * norm2))
    
    def find_most_similar(
        self,
        query_embedding: list[float],
        candidate_embeddings: list[list[float]],
        top_k: int = 5,
    ) -> list[tuple[int, float]]:
        """
        Find the most similar embeddings to a query.
        
        Args:
            query_embedding: The query vector
            candidate_embeddings: List of candidate vectors
            top_k: Number of results to return
            
        Returns:
            List of (index, similarity_score) tuples, sorted by similarity descending
        """
        if not candidate_embeddings:
            return []
        
        query = np.array(query_embedding)
        candidates = np.array(candidate_embeddings)
        
        # Normalize
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return []
        query = query / query_norm
        
        candidate_norms = np.linalg.norm(candidates, axis=1, keepdims=True)
        # Avoid division by zero
        candidate_norms = np.maximum(candidate_norms, 1e-10)
        candidates_normalized = candidates / candidate_norms
        
        # Compute similarities
        similarities = np.dot(candidates_normalized, query)
        
        # Get top k indices
        if len(similarities) <= top_k:
            top_indices = np.argsort(similarities)[::-1]
        else:
            top_indices = np.argpartition(similarities, -top_k)[-top_k:]
            top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]
        
        return [(int(idx), float(similarities[idx])) for idx in top_indices]


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

