#!/usr/bin/env python3
"""
Test Phase 7.2: OpenAI Embedding Service

Tests:
1. OpenAI embedding client works with live API
2. Fallback to local embeddings when OpenAI unavailable
3. Cosine similarity computation
4. Batch embedding
"""

import os
import sys
from pathlib import Path

# Add the api directory to the path
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))


def test_embedding_service_imports():
    """Test that embedding service can be imported."""
    print("=" * 60)
    print("TEST: Import EmbeddingService")
    print("=" * 60)
    
    try:
        from app.services.embeddings import (
            EmbeddingService,
            EmbeddingConfig,
            EmbeddingProvider,
            EmbeddingResult,
            OpenAIEmbeddingClient,
            LocalEmbeddingClient,
        )
        print("  ✅ All embedding classes imported")
        return True
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False


def test_openai_embedding():
    """Test OpenAI embedding with live API."""
    print("\n" + "=" * 60)
    print("TEST: OpenAI Embedding (Live API)")
    print("=" * 60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  ⚠️  SKIPPED: OPENAI_API_KEY not set")
        return None  # Skip, not failure
    
    try:
        from app.services.embeddings import (
            EmbeddingService,
            EmbeddingConfig,
            EmbeddingProvider,
        )
        
        config = EmbeddingConfig(provider=EmbeddingProvider.OPENAI)
        service = EmbeddingService(config)
        
        # Test single embedding
        result = service.embed_text("Hello, world!")
        
        print(f"  Model: {result.model}")
        print(f"  Dimensions: {result.dimensions}")
        print(f"  Provider: {result.provider}")
        
        if result.dimensions == 1536:
            print("  ✅ Correct dimensions (1536)")
        else:
            print(f"  ❌ Wrong dimensions: {result.dimensions}")
            return False
        
        if result.provider == EmbeddingProvider.OPENAI:
            print("  ✅ Using OpenAI provider")
        else:
            print(f"  ❌ Wrong provider: {result.provider}")
            return False
        
        # Verify embedding is not all zeros
        if any(v != 0.0 for v in result.embedding):
            print("  ✅ Embedding contains non-zero values")
        else:
            print("  ❌ Embedding is all zeros")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_batch_embedding():
    """Test batch embedding."""
    print("\n" + "=" * 60)
    print("TEST: Batch Embedding")
    print("=" * 60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  ⚠️  SKIPPED: OPENAI_API_KEY not set")
        return None
    
    try:
        from app.services.embeddings import EmbeddingService
        
        service = EmbeddingService()
        
        texts = [
            "The quick brown fox",
            "jumps over the lazy dog",
            "",  # Empty text should be handled
            "Machine learning is fascinating",
        ]
        
        results = service.embed_texts(texts)
        
        if len(results) == len(texts):
            print(f"  ✅ Got {len(results)} results for {len(texts)} texts")
        else:
            print(f"  ❌ Expected {len(texts)} results, got {len(results)}")
            return False
        
        # Check empty text handling
        empty_result = results[2]
        if all(v == 0.0 for v in empty_result.embedding):
            print("  ✅ Empty text returns zero vector")
        else:
            print("  ❌ Empty text should return zero vector")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_similarity():
    """Test cosine similarity computation."""
    print("\n" + "=" * 60)
    print("TEST: Cosine Similarity")
    print("=" * 60)
    
    try:
        from app.services.embeddings import EmbeddingService
        
        service = EmbeddingService()
        
        # Test with known vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]  # Identical
        vec3 = [0.0, 1.0, 0.0]  # Orthogonal
        vec4 = [-1.0, 0.0, 0.0]  # Opposite
        
        sim_identical = service.similarity(vec1, vec2)
        sim_orthogonal = service.similarity(vec1, vec3)
        sim_opposite = service.similarity(vec1, vec4)
        
        print(f"  Identical vectors: {sim_identical:.4f}")
        print(f"  Orthogonal vectors: {sim_orthogonal:.4f}")
        print(f"  Opposite vectors: {sim_opposite:.4f}")
        
        all_ok = True
        
        if abs(sim_identical - 1.0) < 0.001:
            print("  ✅ Identical = 1.0")
        else:
            print("  ❌ Identical should be 1.0")
            all_ok = False
        
        if abs(sim_orthogonal - 0.0) < 0.001:
            print("  ✅ Orthogonal = 0.0")
        else:
            print("  ❌ Orthogonal should be 0.0")
            all_ok = False
        
        if abs(sim_opposite - (-1.0)) < 0.001:
            print("  ✅ Opposite = -1.0")
        else:
            print("  ❌ Opposite should be -1.0")
            all_ok = False
        
        return all_ok
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_semantic_similarity():
    """Test semantic similarity with real embeddings."""
    print("\n" + "=" * 60)
    print("TEST: Semantic Similarity (Live)")
    print("=" * 60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  ⚠️  SKIPPED: OPENAI_API_KEY not set")
        return None
    
    try:
        from app.services.embeddings import EmbeddingService
        
        service = EmbeddingService()
        
        # Similar texts
        text1 = "The cat sat on the mat"
        text2 = "A feline rested on the rug"
        
        # Different texts
        text3 = "Quantum physics explains subatomic behavior"
        
        emb1 = service.embed_text(text1)
        emb2 = service.embed_text(text2)
        emb3 = service.embed_text(text3)
        
        sim_similar = service.similarity(emb1.embedding, emb2.embedding)
        sim_different = service.similarity(emb1.embedding, emb3.embedding)
        
        print(f"  'cat on mat' vs 'feline on rug': {sim_similar:.4f}")
        print(f"  'cat on mat' vs 'quantum physics': {sim_different:.4f}")
        
        if sim_similar > sim_different:
            print("  ✅ Similar texts have higher similarity")
            return True
        else:
            print("  ❌ Similar texts should have higher similarity than different texts")
            return False
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_local_fallback():
    """Test local embedding fallback."""
    print("\n" + "=" * 60)
    print("TEST: Local Embedding Fallback")
    print("=" * 60)
    
    try:
        from app.services.embeddings import (
            EmbeddingService,
            EmbeddingConfig,
            EmbeddingProvider,
        )
        
        config = EmbeddingConfig(
            provider=EmbeddingProvider.LOCAL,
            allow_dimension_mismatch=True,
        )
        service = EmbeddingService(config)
        
        result = service.embed_text("Test text for local embedding")
        
        print(f"  Model: {result.model}")
        print(f"  Dimensions: {result.dimensions}")
        print(f"  Provider: {result.provider}")
        
        if result.provider == EmbeddingProvider.LOCAL:
            print("  ✅ Using local provider")
        else:
            print(f"  ❌ Wrong provider: {result.provider}")
            return False
        
        if any(v != 0.0 for v in result.embedding):
            print("  ✅ Embedding contains non-zero values")
        else:
            print("  ❌ Embedding is all zeros")
            return False
        
        # Note: local model dimensions may differ from 1536
        if result.dimensions != 1536:
            print(f"  ⚠️  Note: Local dimensions ({result.dimensions}) differ from DB expected (1536)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    """Run all embedding tests."""
    print("\n" + "=" * 60)
    print("PHASE 7.2: EMBEDDING SERVICE TESTS")
    print("=" * 60)
    
    results = []
    
    results.append(("Import", test_embedding_service_imports()))
    results.append(("OpenAI Embedding", test_openai_embedding()))
    results.append(("Batch Embedding", test_batch_embedding()))
    results.append(("Similarity Math", test_similarity()))
    results.append(("Semantic Similarity", test_semantic_similarity()))
    results.append(("Local Fallback", test_local_fallback()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = 0
    skipped = 0
    failed = 0
    
    for name, result in results:
        if result is True:
            status = "✅ PASS"
            passed += 1
        elif result is None:
            status = "⚠️  SKIP"
            skipped += 1
        else:
            status = "❌ FAIL"
            failed += 1
        print(f"  {status}: {name}")
    
    print(f"\n  Passed: {passed}, Skipped: {skipped}, Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 Phase 7.2 Embedding Service: ALL TESTS PASSED (or skipped)")
        return 0
    else:
        print("\n💥 Phase 7.2 Embedding Service: SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())


