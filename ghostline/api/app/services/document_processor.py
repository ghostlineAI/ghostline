"""
Document Processor Service for extracting text from various file formats.

Supports:
- PDF documents
- Word documents (DOCX)
- Plain text files
- HTML files
- Markdown files

Uses the 'unstructured' library for robust extraction.
"""

import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

# Lazy import for unstructured to avoid startup overhead
_partition_function = None


class DocumentType(str, Enum):
    """Supported document types."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"
    MARKDOWN = "md"
    UNKNOWN = "unknown"


@dataclass
class ExtractedText:
    """Result from document text extraction."""
    content: str
    word_count: int
    page_count: Optional[int]
    document_type: DocumentType
    metadata: dict
    chunks: list[str]  # Pre-chunked text for RAG


@dataclass
class TextChunk:
    """A chunk of text for embedding and retrieval."""
    text: str
    start_idx: int
    end_idx: int
    page_number: Optional[int]
    section_title: Optional[str]


class DocumentProcessor:
    """
    Service for extracting and chunking text from documents.
    
    Handles various file formats and provides chunked output
    suitable for embedding and RAG retrieval.
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """
        Initialize the document processor.
        
        Args:
            chunk_size: Target size for text chunks (in characters)
            chunk_overlap: Overlap between adjacent chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def _detect_type(self, filename: str) -> DocumentType:
        """Detect document type from filename extension."""
        ext = Path(filename).suffix.lower()
        type_map = {
            ".pdf": DocumentType.PDF,
            ".docx": DocumentType.DOCX,
            ".doc": DocumentType.DOCX,
            ".txt": DocumentType.TXT,
            ".text": DocumentType.TXT,
            ".html": DocumentType.HTML,
            ".htm": DocumentType.HTML,
            ".md": DocumentType.MARKDOWN,
            ".markdown": DocumentType.MARKDOWN,
        }
        return type_map.get(ext, DocumentType.UNKNOWN)
    
    def extract_from_file(
        self,
        file_path: str,
        use_unstructured: bool = True,
    ) -> ExtractedText:
        """
        Extract text from a file.
        
        Args:
            file_path: Path to the document file
            use_unstructured: Whether to use unstructured library (more robust)
            
        Returns:
            ExtractedText with content and metadata
        """
        doc_type = self._detect_type(file_path)
        
        if use_unstructured:
            return self._extract_with_unstructured(file_path, doc_type)
        else:
            return self._extract_basic(file_path, doc_type)
    
    def extract_from_bytes(
        self,
        content: bytes,
        filename: str,
    ) -> ExtractedText:
        """
        Extract text from file bytes.
        
        Args:
            content: File content as bytes
            filename: Original filename (for type detection)
            
        Returns:
            ExtractedText with content and metadata
        """
        doc_type = self._detect_type(filename)
        
        # Write to temporary file for processing
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            return self.extract_from_file(tmp_path)
        finally:
            # Clean up temp file
            os.unlink(tmp_path)
    
    def _extract_with_unstructured(
        self,
        file_path: str,
        doc_type: DocumentType,
    ) -> ExtractedText:
        """Extract using unstructured library."""
        try:
            from unstructured.partition.auto import partition
            
            elements = partition(filename=file_path)
            
            # Combine all text elements
            text_parts = []
            page_numbers = set()
            
            for element in elements:
                text_parts.append(str(element))
                # Try to get page number from metadata
                if hasattr(element, 'metadata') and hasattr(element.metadata, 'page_number'):
                    if element.metadata.page_number:
                        page_numbers.add(element.metadata.page_number)
            
            full_text = "\n\n".join(text_parts)
            
            # Chunk the text
            chunks = self._chunk_text(full_text)
            
            return ExtractedText(
                content=full_text,
                word_count=len(full_text.split()),
                page_count=max(page_numbers) if page_numbers else None,
                document_type=doc_type,
                metadata={"elements_count": len(elements)},
                chunks=[c.text for c in chunks],
            )
            
        except ImportError:
            # Fall back to basic extraction if unstructured not available
            return self._extract_basic(file_path, doc_type)
        except Exception as e:
            # If unstructured fails, try basic extraction
            print(f"[DocumentProcessor] Unstructured failed: {e}, trying basic extraction")
            return self._extract_basic(file_path, doc_type)
    
    def _extract_basic(
        self,
        file_path: str,
        doc_type: DocumentType,
    ) -> ExtractedText:
        """Basic text extraction without unstructured."""
        if doc_type == DocumentType.TXT:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        elif doc_type == DocumentType.MARKDOWN:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        elif doc_type == DocumentType.HTML:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw = f.read()
            # Basic HTML stripping
            import re
            content = re.sub(r'<[^>]+>', ' ', raw)
            content = re.sub(r'\s+', ' ', content)
        else:
            # For PDF/DOCX without unstructured, return empty with warning
            content = f"[Unable to extract from {doc_type.value} without unstructured library]"
        
        chunks = self._chunk_text(content)
        
        return ExtractedText(
            content=content,
            word_count=len(content.split()),
            page_count=None,
            document_type=doc_type,
            metadata={"extraction_method": "basic"},
            chunks=[c.text for c in chunks],
        )
    
    def _chunk_text(
        self,
        text: str,
        separators: Optional[list[str]] = None,
    ) -> list[TextChunk]:
        """
        Split text into overlapping chunks suitable for embedding.
        
        Uses a recursive splitting strategy:
        1. Try to split on paragraph boundaries
        2. Fall back to sentence boundaries
        3. Finally split on spaces if needed
        """
        if separators is None:
            separators = ["\n\n", "\n", ". ", " "]
        
        if not text or len(text) <= self.chunk_size:
            return [TextChunk(
                text=text,
                start_idx=0,
                end_idx=len(text),
                page_number=None,
                section_title=None,
            )]
        
        chunks = []
        current_idx = 0
        
        while current_idx < len(text):
            # Get chunk end position
            chunk_end = min(current_idx + self.chunk_size, len(text))
            
            # Try to find a good break point
            if chunk_end < len(text):
                # Look for separator near the end of chunk
                best_break = chunk_end
                for sep in separators:
                    # Search backwards from chunk_end
                    search_start = max(current_idx + self.chunk_size // 2, current_idx)
                    last_sep = text.rfind(sep, search_start, chunk_end)
                    if last_sep > 0:
                        best_break = last_sep + len(sep)
                        break
                chunk_end = best_break
            
            # Extract chunk
            chunk_text = text[current_idx:chunk_end].strip()
            
            if chunk_text:
                chunks.append(TextChunk(
                    text=chunk_text,
                    start_idx=current_idx,
                    end_idx=chunk_end,
                    page_number=None,
                    section_title=None,
                ))
            
            # Move to next chunk with overlap
            current_idx = chunk_end - self.chunk_overlap
            if current_idx >= len(text) - self.chunk_overlap:
                break
        
        return chunks
    
    def chunk_for_rag(
        self,
        text: str,
        max_chunks: Optional[int] = None,
    ) -> list[TextChunk]:
        """
        Chunk text specifically for RAG retrieval.
        
        Args:
            text: The full text to chunk
            max_chunks: Maximum number of chunks to return (None for all)
            
        Returns:
            List of TextChunk objects
        """
        chunks = self._chunk_text(text)
        
        if max_chunks and len(chunks) > max_chunks:
            chunks = chunks[:max_chunks]
        
        return chunks


# Singleton instance
_document_processor: Optional[DocumentProcessor] = None


def get_document_processor(
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> DocumentProcessor:
    """Get the global document processor instance."""
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    return _document_processor

