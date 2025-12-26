"""
Document Processor Service for extracting text from various file formats.

Supports:
- PDF documents
- Word documents (DOCX)
- Plain text files
- HTML files
- Markdown files
- Images (using VLM for understanding, OCR as fallback)

Uses the 'unstructured' library for robust extraction.
Uses Vision Language Models (Claude/GPT-4V) for image understanding.
"""

import base64
import os
import tempfile
import time
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
    IMAGE = "image"  # For OCR processing
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
            # Image types - will use OCR
            ".png": DocumentType.IMAGE,
            ".jpg": DocumentType.IMAGE,
            ".jpeg": DocumentType.IMAGE,
            ".gif": DocumentType.IMAGE,
            ".webp": DocumentType.IMAGE,
            ".tiff": DocumentType.IMAGE,
            ".tif": DocumentType.IMAGE,
            ".bmp": DocumentType.IMAGE,
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
            
            # Enable OCR for images and PDFs with images
            partition_kwargs = {"filename": file_path}
            
            if doc_type == DocumentType.IMAGE:
                # For images, use VLM (Vision Language Model) for understanding
                # This is much more powerful than OCR - can understand diagrams,
                # handwritten notes, charts, screenshots, etc.
                vlm_result = self._extract_with_vlm(file_path)
                if vlm_result and vlm_result.word_count > 10:
                    return vlm_result
                
                # Fallback to OCR if VLM fails or returns minimal content
                try:
                    from unstructured.partition.image import partition_image
                    elements = partition_image(
                        filename=file_path,
                        strategy="ocr_only",  # Force OCR for images
                    )
                except ImportError:
                    # Fallback to auto partition
                    elements = partition(**partition_kwargs)
            else:
                # For other document types
                elements = partition(**partition_kwargs)
            
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
        elif doc_type == DocumentType.IMAGE:
            # Try VLM first for better understanding
            vlm_result = self._extract_with_vlm(file_path)
            if vlm_result and vlm_result.word_count > 10:
                return vlm_result
            
            # Fallback to pytesseract OCR
            try:
                import pytesseract
                from PIL import Image
                img = Image.open(file_path)
                content = pytesseract.image_to_string(img)
                if not content.strip():
                    content = "[Image contains no extractable text]"
            except ImportError:
                content = "[OCR requires pytesseract and PIL libraries]"
            except Exception as e:
                content = f"[OCR failed: {str(e)}]"
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
    
    def _extract_with_vlm(
        self,
        file_path: str,
    ) -> Optional[ExtractedText]:
        """
        Extract content from an image using a Vision Language Model.
        
        This is much more powerful than OCR because it can:
        - Understand and describe diagrams, charts, and infographics
        - Read and interpret handwritten notes
        - Extract text with proper context and structure
        - Describe visual elements that pure text extraction would miss
        - Understand relationships between visual elements
        
        Uses Claude's vision capabilities via LangChain for consistency
        with our agent framework.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            ExtractedText with VLM-generated content, or None if VLM fails
        """
        try:
            # Check for API key
            import os
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                print("[DocumentProcessor] No ANTHROPIC_API_KEY found, skipping VLM extraction")
                return None
            
            # Read and encode image
            with open(file_path, "rb") as f:
                image_data = f.read()
            
            # Determine media type
            ext = Path(file_path).suffix.lower()
            media_type_map = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            media_type = media_type_map.get(ext, "image/png")
            
            # Encode to base64
            image_b64 = base64.b64encode(image_data).decode("utf-8")
            
            # Use LangChain for consistency with our agent framework
            from langchain_anthropic import ChatAnthropic
            from langchain_core.messages import HumanMessage
            
            llm = ChatAnthropic(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                temperature=0.1,  # Low temperature for accurate extraction
            )
            
            # Create vision message
            message = HumanMessage(
                content=[
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": """Analyze this image thoroughly and extract ALL content. Your goal is to capture everything that could be useful for a book or document.

Please provide:

1. **EXTRACTED TEXT**: If there is any text in the image (typed, handwritten, or in graphics), transcribe it exactly as it appears. Preserve formatting, bullet points, numbered lists, etc.

2. **VISUAL DESCRIPTION**: Describe any diagrams, charts, graphs, illustrations, or visual elements. Explain what they represent and any data or relationships they show.

3. **CONTEXT & MEANING**: Explain what this image is about. What topic does it cover? What key insights or information does it convey?

4. **STRUCTURE**: If this appears to be notes, a presentation slide, a diagram, or another structured format, describe that structure.

5. **KEY TAKEAWAYS**: Summarize the main points or information contained in this image.

Be thorough - this content will be used as source material for generating a book, so capture every relevant detail."""
                    }
                ]
            )
            
            # Invoke the VLM (and cost-track it if possible)
            started = time.time()
            response = None
            try:
                response = llm.invoke([message])
            except Exception as e:
                duration_ms = int((time.time() - started) * 1000)
                # Record failed vision call (if context is available)
                try:
                    from agents.base.agent import get_cost_context
                    from app.services.cost_tracker import CostTracker

                    ctx = get_cost_context()
                    db = ctx.get("db_session")
                    if db:
                        tracker = CostTracker(db)
                        tracker.record(
                            agent_name="DocumentProcessorVLM",
                            agent_role="vision",
                            provider="anthropic",
                            model="claude-sonnet-4-20250514",
                            call_type="vision",
                            input_tokens=0,
                            output_tokens=0,
                            duration_ms=duration_ms,
                            success=False,
                            error_message=str(e),
                            project_id=ctx.get("project_id"),
                            task_id=ctx.get("task_id"),
                            workflow_run_id=ctx.get("workflow_run_id"),
                            chapter_number=ctx.get("chapter_number"),
                            metadata={
                                "file_path": str(file_path),
                                "media_type": media_type,
                                "bytes": len(image_data),
                            },
                        )
                except Exception:
                    pass
                raise

            duration_ms = int((time.time() - started) * 1000)
            content = response.content

            # Record to DB cost logs if we have an active cost context
            try:
                from agents.base.agent import get_cost_context
                from app.services.cost_tracker import CostTracker

                ctx = get_cost_context()
                db = ctx.get("db_session")
                if db:
                    usage = getattr(response, "usage_metadata", None) or {}
                    input_tokens = int(usage.get("input_tokens") or 0)
                    output_tokens = int(usage.get("output_tokens") or 0)
                    tracker = CostTracker(db)
                    tracker.record(
                        agent_name="DocumentProcessorVLM",
                        agent_role="vision",
                        provider="anthropic",
                        model="claude-sonnet-4-20250514",
                        call_type="vision",
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        duration_ms=duration_ms,
                        success=True,
                        project_id=ctx.get("project_id"),
                        task_id=ctx.get("task_id"),
                        workflow_run_id=ctx.get("workflow_run_id"),
                        chapter_number=ctx.get("chapter_number"),
                        metadata={
                            "file_path": str(file_path),
                            "media_type": media_type,
                            "bytes": len(image_data),
                        },
                    )
            except Exception:
                # Never block extraction on cost tracking
                pass
            
            if not content or len(content.strip()) < 20:
                print("[DocumentProcessor] VLM returned minimal content")
                return None
            
            # Chunk the extracted content
            chunks = self._chunk_text(content)
            
            print(f"[DocumentProcessor] VLM extracted {len(content.split())} words from image")
            
            return ExtractedText(
                content=content,
                word_count=len(content.split()),
                page_count=1,
                document_type=DocumentType.IMAGE,
                metadata={
                    "extraction_method": "vlm",
                    "model": "claude-sonnet-4-20250514",
                    "source_type": "vision",
                },
                chunks=[c.text for c in chunks],
            )
            
        except ImportError as e:
            print(f"[DocumentProcessor] LangChain not available for VLM: {e}")
            return None
        except Exception as e:
            print(f"[DocumentProcessor] VLM extraction failed: {e}")
            return None
    
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



