import asyncio
import chardet
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_processor import BaseDocumentProcessor, ProcessedDocument
import logging

logger = logging.getLogger(__name__)

class TextProcessor(BaseDocumentProcessor):
    """Processor for plain text files"""

    def __init__(self):
        super().__init__()
        self.supported_extensions = [".txt", ".text", ".md", ".rst"]

    async def process(self, file_path: str, source_metadata: Optional[Dict[str, Any]] = None) -> ProcessedDocument:
        """Process a text file"""
        try:
            # Detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                detected = chardet.detect(raw_data)
                encoding = detected['encoding'] or 'utf-8'

            # Read content
            content = raw_data.decode(encoding)

            # Extract metadata
            metadata = self._extract_basic_metadata(file_path)
            metadata.update({
                "encoding": encoding,
                "language": "text",  # Could be enhanced with langdetect
                "line_count": len(content.splitlines()),
                "word_count": len(content.split()),
                "char_count": len(content)
            })

            # Add source metadata if provided
            if source_metadata:
                metadata.update(source_metadata)

            # Create simple chunks (by paragraphs for now)
            chunks = self._create_chunks(content)

            document_id = f"txt_{metadata['checksum'][:8]}"
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
            logger.error(f"Error processing text file {file_path}: {str(e)}")
            raise

    def _create_chunks(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """Create text chunks with overlap"""
        chunks = []
        lines = content.splitlines()

        current_chunk = []
        current_length = 0
        start_line = 0

        for i, line in enumerate(lines):
            line_length = len(line) + 1  # +1 for newline

            if current_length + line_length > chunk_size and current_chunk:
                # Create chunk
                chunk_content = '\n'.join(current_chunk)
                chunks.append({
                    "content": chunk_content,
                    "start_line": start_line,
                    "end_line": i - 1,
                    "length": len(chunk_content)
                })

                # Start new chunk with overlap
                overlap_lines = []
                overlap_length = 0
                for j in range(len(current_chunk) - 1, -1, -1):
                    line_len = len(current_chunk[j]) + 1
                    if overlap_length + line_len > overlap:
                        break
                    overlap_lines.insert(0, current_chunk[j])
                    overlap_length += line_len

                current_chunk = overlap_lines + [line]
                current_length = overlap_length + line_length
                start_line = i - len(overlap_lines)
            else:
                current_chunk.append(line)
                current_length += line_length

        # Add final chunk
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            chunks.append({
                "content": chunk_content,
                "start_line": start_line,
                "end_line": len(lines) - 1,
                "length": len(chunk_content)
            })

        return chunks