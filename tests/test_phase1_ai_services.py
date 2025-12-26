"""
Phase 1 Tests: Core AI Services

These tests verify the LLM, Embedding, and Document Processing
services work correctly. Includes LIVE API calls where possible.
"""

import pytest
import sys
import os

# Add the API app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'api'))


class TestLLMService:
    """Test LLM client service."""
    
    def test_llm_service_imports(self):
        """LLM service should import without errors."""
        from app.services.llm import (
            LLMService,
            AnthropicClient,
            OpenAIClient,
            ModelConfig,
            MODELS,
        )
        assert LLMService is not None
        assert len(MODELS) >= 4  # At least 4 models configured
    
    def test_model_configs_valid(self):
        """All model configs should be valid."""
        from app.services.llm import MODELS, ModelProvider
        
        for name, config in MODELS.items():
            assert config.provider in [ModelProvider.ANTHROPIC, ModelProvider.OPENAI]
            assert config.max_tokens > 0
            assert config.input_cost_per_1k >= 0
            assert config.output_cost_per_1k >= 0
    
    def test_llm_service_instantiation(self):
        """LLM service should instantiate without API calls."""
        from app.services.llm import LLMService
        
        service = LLMService()
        assert service.default_model is not None
        assert service.fast_model is not None
    
    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_anthropic_live_call(self):
        """LIVE TEST: Call Anthropic API."""
        from app.services.llm import LLMService
        
        service = LLMService()
        response = service.generate(
            prompt="Say 'hello' and nothing else.",
            model="claude-3-haiku-20240307",  # Use cheap model
            max_tokens=50,
        )
        
        assert response.content is not None
        assert len(response.content) > 0
        assert response.total_tokens > 0
        assert response.estimated_cost > 0
        print(f"  [LIVE] Anthropic response: {response.content[:50]}...")
        print(f"  [LIVE] Tokens: {response.total_tokens}, Cost: ${response.estimated_cost:.6f}")
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )
    def test_openai_live_call(self):
        """LIVE TEST: Call OpenAI API."""
        from app.services.llm import LLMService
        
        service = LLMService()
        response = service.generate(
            prompt="Say 'hello' and nothing else.",
            model="gpt-4o-mini",  # Use cheap model
            max_tokens=50,
        )
        
        assert response.content is not None
        assert len(response.content) > 0
        assert response.total_tokens > 0
        print(f"  [LIVE] OpenAI response: {response.content[:50]}...")
        print(f"  [LIVE] Tokens: {response.total_tokens}, Cost: ${response.estimated_cost:.6f}")


class TestEmbeddingService:
    """Test embedding service."""
    
    def test_embedding_service_imports(self):
        """Embedding service should import without errors."""
        from app.services.embeddings import (
            EmbeddingService,
            EmbeddingResult,
            get_embedding_service,
        )
        assert EmbeddingService is not None
    
    def test_embedding_service_instantiation(self):
        """Embedding service should instantiate (lazy loading)."""
        from app.services.embeddings import EmbeddingService
        
        service = EmbeddingService()
        assert service.model_name is not None
        assert service._target_dims == 1536
    
    @pytest.mark.slow
    def test_embedding_generation_live(self):
        """LIVE TEST: Generate actual embeddings."""
        from app.services.embeddings import EmbeddingService
        
        service = EmbeddingService()
        result = service.embed_text("This is a test sentence for embedding.")
        
        assert result.embedding is not None
        assert len(result.embedding) == 1536  # Target dimension
        assert result.dimensions == 1536
        assert result.text_length > 0
        
        # Verify embedding is normalized-ish (values should be reasonable)
        import numpy as np
        arr = np.array(result.embedding)
        assert abs(np.linalg.norm(arr[:768]) - 1.0) < 0.5  # Original dims normalized
        
        print(f"  [LIVE] Embedding generated: {len(result.embedding)} dims")
    
    @pytest.mark.slow
    def test_embedding_batch_live(self):
        """LIVE TEST: Batch embedding generation."""
        from app.services.embeddings import EmbeddingService
        
        service = EmbeddingService()
        texts = [
            "First test sentence.",
            "Second test sentence.",
            "Third test sentence.",
        ]
        results = service.embed_texts(texts)
        
        assert len(results) == 3
        for result in results:
            assert len(result.embedding) == 1536
        
        print(f"  [LIVE] Batch of {len(results)} embeddings generated")
    
    @pytest.mark.slow
    def test_similarity_calculation(self):
        """Test cosine similarity calculation."""
        from app.services.embeddings import EmbeddingService
        
        service = EmbeddingService()
        
        # Similar texts should have higher similarity
        results = service.embed_texts([
            "The cat sat on the mat.",
            "A cat was sitting on a mat.",
            "The weather forecast predicts rain.",
        ])
        
        sim_12 = service.compute_similarity(results[0].embedding, results[1].embedding)
        sim_13 = service.compute_similarity(results[0].embedding, results[2].embedding)
        
        # Similar texts (0,1) should be more similar than different topics (0,2)
        assert sim_12 > sim_13
        print(f"  [LIVE] Similarity (similar): {sim_12:.4f}, (different): {sim_13:.4f}")


class TestDocumentProcessor:
    """Test document processing service."""
    
    def test_document_processor_imports(self):
        """Document processor should import without errors."""
        from app.services.document_processor import (
            DocumentProcessor,
            DocumentType,
            ExtractedText,
            TextChunk,
        )
        assert DocumentProcessor is not None
    
    def test_document_processor_instantiation(self):
        """Document processor should instantiate."""
        from app.services.document_processor import DocumentProcessor
        
        processor = DocumentProcessor(chunk_size=1000, chunk_overlap=200)
        assert processor.chunk_size == 1000
        assert processor.chunk_overlap == 200
    
    def test_detect_file_types(self):
        """File type detection should work."""
        from app.services.document_processor import DocumentProcessor, DocumentType
        
        processor = DocumentProcessor()
        
        assert processor._detect_type("test.pdf") == DocumentType.PDF
        assert processor._detect_type("test.docx") == DocumentType.DOCX
        assert processor._detect_type("test.txt") == DocumentType.TXT
        assert processor._detect_type("test.md") == DocumentType.MARKDOWN
        assert processor._detect_type("test.html") == DocumentType.HTML
        assert processor._detect_type("test.unknown") == DocumentType.UNKNOWN
    
    def test_text_chunking(self):
        """Text chunking should work correctly."""
        from app.services.document_processor import DocumentProcessor
        
        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
        
        # Create a longer text
        text = " ".join(["This is sentence number " + str(i) + "." for i in range(50)])
        
        chunks = processor._chunk_text(text)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.text) <= 150  # Allow some flexibility
            assert chunk.start_idx >= 0
            assert chunk.end_idx > chunk.start_idx
        
        print(f"  Text of {len(text)} chars -> {len(chunks)} chunks")
    
    def test_extract_from_text_file(self):
        """LIVE TEST: Extract from actual text file."""
        from app.services.document_processor import DocumentProcessor
        import tempfile
        
        processor = DocumentProcessor()
        
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test document.\n\nIt has multiple paragraphs.\n\nAnd some content to extract.")
            temp_path = f.name
        
        try:
            result = processor.extract_from_file(temp_path, use_unstructured=False)
            
            assert result.content is not None
            assert len(result.content) > 0
            assert result.word_count > 0
            assert len(result.chunks) > 0
            
            print(f"  [LIVE] Extracted {result.word_count} words, {len(result.chunks)} chunks")
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    # Run with: pytest tests/test_phase1_ai_services.py -v -s
    pytest.main([__file__, "-v", "-s"])



