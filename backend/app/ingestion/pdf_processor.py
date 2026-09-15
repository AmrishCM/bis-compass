import fitz  # PyMuPDF
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_processor import BaseDocumentProcessor, ProcessedDocument
import logging
import io

logger = logging.getLogger(__name__)

class PDFProcessor(BaseDocumentProcessor):
    """Processor for PDF files"""

    def __init__(self):
        super().__init__()
        self.supported_extensions = [".pdf"]

    async def process(self, file_path: str, source_metadata: Optional[Dict[str, Any]] = None) -> ProcessedDocument:
        """Process a PDF file"""
        try:
            # Open PDF document
            doc = fitz.open(file_path)

            # Extract text content
            content_parts = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                content_parts.append(f"--- Page {page_num + 1} ---\n{text}")

            content = "\n\n".join(content_parts)

            # Extract metadata
            metadata = self._extract_basic_metadata(file_path)
            pdf_metadata = doc.metadata

            metadata.update({
                "page_count": len(doc),
                "title": pdf_metadata.get("title", ""),
                "author": pdf_metadata.get("author", ""),
                "subject": pdf_metadata.get("subject", ""),
                "creator": pdf_metadata.get("creator", ""),
                "producer": pdf_metadata.get("producer", ""),
                "creation_date": pdf_metadata.get("creationDate", ""),
                "modification_date": pdf_metadata.get("modDate", ""),
                "is_encrypted": doc.is_encrypted,
                "is_pdf": True
            })

            # Add source metadata if provided
            if source_metadata:
                metadata.update(source_metadata)

            # Create chunks (by pages for PDF)
            chunks = self._create_chunks_by_pages(doc)

            document_id = f"pdf_{metadata['checksum'][:8]}"
            source_id = f"src_{metadata['checksum'][:8]}"

            doc.close()

            return ProcessedDocument(
                content=content,
                metadata=metadata,
                chunks=chunks,
                document_id=document_id,
                source_id=source_id,
                processed_at=datetime.now(),
                file_size=metadata["file_size"],
                checksum=metadata["checksum"]
            )

        except Exception as e:
            logger.error(f"Error processing PDF file {file_path}: {str(e)}")
            raise

    def _create_chunks_by_pages(self, doc) -> List[Dict[str, Any]]:
        """Create chunks by PDF pages"""
        chunks = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()

            if text.strip():  # Only add non-empty pages
                chunks.append({
                    "content": text.strip(),
                    "page_number": page_num + 1,
                    "start_char": 0,  # Simplified - in reality would track character positions
                    "end_char": len(text),
                    "length": len(text)
                })

        return chunks