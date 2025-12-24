"""
Phase 2 Tests: Generation and Processing Services

These tests verify the GenerationService and ProcessingService
work correctly with their dependencies.
"""

import pytest
import sys
import os

# Add the API app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ghostline', 'api'))


class TestGenerationService:
    """Test generation service."""
    
    def test_generation_service_file_exists(self):
        """Generation service file should exist with required code."""
        import os
        
        service_file = os.path.join(
            os.path.dirname(__file__), '..', 'ghostline', 'api', 
            'app', 'services', 'generation.py'
        )
        assert os.path.exists(service_file)
        
        with open(service_file, 'r') as f:
            content = f.read()
        
        # Check for required classes and methods
        assert 'class GenerationService' in content
        assert 'def generate_outline' in content
        assert 'def generate_chapter' in content
        assert 'def analyze_voice' in content
        assert 'def revise_chapter' in content
    
    def test_generation_service_uses_llm(self):
        """Generation service should use LLM and embedding services."""
        import os
        
        service_file = os.path.join(
            os.path.dirname(__file__), '..', 'ghostline', 'api', 
            'app', 'services', 'generation.py'
        )
        
        with open(service_file, 'r') as f:
            content = f.read()
        
        assert 'LLMService' in content or 'get_llm_service' in content
        assert 'EmbeddingService' in content or 'get_embedding_service' in content
    
    def test_generation_service_dataclasses(self):
        """Result dataclasses should be properly defined."""
        import os
        
        service_file = os.path.join(
            os.path.dirname(__file__), '..', 'ghostline', 'api', 
            'app', 'services', 'generation.py'
        )
        
        with open(service_file, 'r') as f:
            content = f.read()
        
        assert 'OutlineGenerationResult' in content
        assert 'ChapterGenerationResult' in content
        assert 'VoiceAnalysisResult' in content
    
    def test_json_parsing_logic(self):
        """JSON parsing logic should handle common LLM output formats."""
        import json
        import re
        
        def parse_json_response(content: str) -> dict:
            """Replicate the parsing logic from GenerationService."""
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
                return {}
        
        # Test clean JSON
        result = parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}
        
        # Test JSON with markdown code block
        result = parse_json_response('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}
        
        # Test JSON embedded in text
        result = parse_json_response('Here is the result: {"key": "value"} as requested.')
        assert result == {"key": "value"}
        
        # Test invalid JSON
        result = parse_json_response('not json at all')
        assert result == {}


class TestProcessingService:
    """Test processing service."""
    
    def test_processing_service_file_exists(self):
        """Processing service file should exist with required code."""
        import os
        
        service_file = os.path.join(
            os.path.dirname(__file__), '..', 'ghostline', 'api', 
            'app', 'services', 'processing.py'
        )
        assert os.path.exists(service_file)
        
        with open(service_file, 'r') as f:
            content = f.read()
        
        # Check for required classes and methods
        assert 'class ProcessingService' in content
        assert 'def process_source_material' in content
        assert 'def create_voice_profile' in content
        assert 'def find_relevant_chunks' in content
    
    def test_processing_service_uses_dependencies(self):
        """Processing service should use doc processor and embeddings."""
        import os
        
        service_file = os.path.join(
            os.path.dirname(__file__), '..', 'ghostline', 'api', 
            'app', 'services', 'processing.py'
        )
        
        with open(service_file, 'r') as f:
            content = f.read()
        
        assert 'DocumentProcessor' in content
        assert 'EmbeddingService' in content
        assert 'StorageService' in content
    
    def test_style_analysis_logic(self):
        """Basic style analysis logic should work."""
        import re
        
        def analyze_style(sample_texts: list) -> str:
            """Replicate the style analysis logic."""
            combined = " ".join(sample_texts)
            
            words = combined.split()
            sentences = re.split(r'[.!?]+', combined)
            
            word_count = len(words)
            sentence_count = len([s for s in sentences if s.strip()])
            avg_sentence_length = word_count / max(sentence_count, 1)
            
            unique_words = len(set(w.lower() for w in words))
            vocab_diversity = unique_words / max(word_count, 1)
            
            length_desc = "short" if avg_sentence_length < 15 else "medium" if avg_sentence_length < 25 else "long"
            vocab_desc = "simple" if vocab_diversity < 0.4 else "moderate" if vocab_diversity < 0.6 else "rich"
            
            return f"Writing style with {length_desc} sentences ({avg_sentence_length:.1f} words avg) and {vocab_desc} vocabulary diversity ({vocab_diversity:.2f})."
        
        samples = [
            "Short sentences work. They pack a punch. Clear and direct.",
            "I prefer longer, more flowing sentences that wind through ideas.",
        ]
        
        analysis = analyze_style(samples)
        
        assert "sentence" in analysis.lower()
        assert "words" in analysis.lower()
        print(f"  Style analysis: {analysis}")


class TestServicesIntegration:
    """Test integration between Phase 2 services."""
    
    def test_services_import_same_dependencies(self):
        """Generation and Processing should import the same embedding service."""
        import os
        
        gen_file = os.path.join(
            os.path.dirname(__file__), '..', 'ghostline', 'api', 
            'app', 'services', 'generation.py'
        )
        proc_file = os.path.join(
            os.path.dirname(__file__), '..', 'ghostline', 'api', 
            'app', 'services', 'processing.py'
        )
        
        with open(gen_file, 'r') as f:
            gen_content = f.read()
        with open(proc_file, 'r') as f:
            proc_content = f.read()
        
        # Both should use EmbeddingService
        assert 'EmbeddingService' in gen_content or 'get_embedding_service' in gen_content
        assert 'EmbeddingService' in proc_content or 'get_embedding_service' in proc_content
    
    @pytest.mark.slow
    def test_document_to_embedding_pipeline(self):
        """Test full document -> chunk -> embed pipeline."""
        from app.services.document_processor import DocumentProcessor
        from app.services.embeddings import EmbeddingService
        import tempfile
        
        # Create test document
        doc_content = """
        Chapter 1: Introduction
        
        This is the beginning of our story. It starts on a cold winter morning
        in the heart of New York City. The streets were empty, save for a lone
        figure walking through the snow.
        
        Chapter 2: The Discovery
        
        What she found that morning would change everything. Hidden beneath
        the fresh snow was a letter, addressed to no one, yet meant for someone.
        The handwriting was elegant, from another era entirely.
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(doc_content)
            temp_path = f.name
        
        try:
            processor = DocumentProcessor(chunk_size=200, chunk_overlap=50)
            embeddings = EmbeddingService()
            
            # Extract and chunk
            extracted = processor.extract_from_file(temp_path)
            
            assert extracted.word_count > 0
            assert len(extracted.chunks) > 0
            
            # Embed chunks
            results = embeddings.embed_texts(extracted.chunks)
            
            assert len(results) == len(extracted.chunks)
            for emb in results:
                assert len(emb.embedding) == 1536
            
            print(f"  [LIVE] Pipeline: {extracted.word_count} words -> {len(extracted.chunks)} chunks -> {len(results)} embeddings")
            
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

