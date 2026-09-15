import docx
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_processor import BaseDocumentProcessor, ProcessedDocument
import logging

logger = logging.getLogger(__name__)

class DOCXProcessor(BaseDocumentProcessor):
    """Processor for DOCX files"""

    def __init__(self):
        super().__init__()
        self.supported_extensions = [".docx", ".doc"]

    async def process(self, file_path: str, source_metadata: Optional[Dict[str, Any]] = None) -> ProcessedDocument:
        """Process a DOCX file"""
        try:
            # Open DOCX document
            doc = docx.Document(file_path)

            # Extract text content
            content_parts = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content_parts.append(paragraph.text)

            content = "\n\n".join(content_parts)

            # Extract metadata
            metadata = self._extract_basic_metadata(file_path)
            core_props = doc.core_properties

            metadata.update({
                "paragraph_count": len(doc.paragraphs),
                "title": core_props.title or "",
                "author": core_props.author or "",
                "subject": core_props.subject or "",
                "keywords": core_props.keywords or "",
                "created_date": core_props.created.isoformat() if core_props.created else "",
                "modified_date": core_props.modified.isoformat() if core_props.modified else "",
                "last_modified_by": core_props.last_modified_by or "",
                "revision": core_props.revision,
                "is_docx": True
            })

            # Add source metadata if provided
            if source_metadata:
                metadata.update(source_metadata)

            # Create chunks (by paragraphs for DOCX)
            chunks = self._create_chunks_by_paragraphs(doc.paragraphs)

            document_id = f"docx_{metadata['checksum'][:8]}"
            source_id = f"src_{metadata['checksum'][:8]}"

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
            logger.error(f"Error processing DOCX file {file_path}: {str(e)}")
            raise

    def _create_chunks_by_paragraphs(self, paragraphs) -> List[Dict[str, Any]]:
        """Create chunks by grouping paragraphs"""
        chunks = []
        current_chunk_paragraphs = []
        current_chunk_text = []
        current_length = 0
        chunk_size = 1000  # Target chunk size in characters
        start_para_index = 0
        para_index = 0

        for para in paragraphs:
            para_text = para.text.strip()
            if not para_text:
                para_index += 1
                continue

            para_length = len(para_text) + 2  # +2 for newline separation

            if current_length + para_length > chunk_size and current_chunk_paragraphs:
                # Create chunk
                chunk_content = "\n\n".join(current_chunk_text)
                chunks.append({
                    "content": chunk_content,
                    "start_paragraph": start_para_index,
                    "end_paragraph": para_index - 1,
                    "paragraph_count": len(current_chunk_paragraphs),
                    "length": len(chunk_content)
                })

                # Start new chunk
                current_chunk_paragraphs = [para]
                current_chunk_text = [para_text]
                current_length = para_length
                start_para_index = para_index
            else:
                current_chunk_paragraphs.append(para)
                current_chunk_text.append(para_text)
                current_length += para_length

            para_index += 1

        # Add final chunk
        if current_chunk_paragraphs:
            chunk_content = "\n\n".join(current_chunk_text)
            chunks.append({
                "content": chunk_content,
                "start_paragraph": start_para_index,
                "end_paragraph": para_index - 1,
                "paragraph_count": len(current_chunk_paragraphs),
                "length": len(chunk_content)
            })

        return chunks