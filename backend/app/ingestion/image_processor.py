from abc import ABC, abstractmethod
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_processor import BaseDocumentProcessor, ProcessedDocument
import logging

logger = logging.getLogger(__name__)

class OCRProvider(ABC):
    """Abstract base class for OCR providers"""

    @abstractmethod
    async def extract_text(self, image_data: bytes) -> str:
        """Extract text from image data"""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the OCR provider"""
        pass

class BaseImageProcessor(BaseDocumentProcessor):
    """Base class for image processors with OCR"""

    def __init__(self, ocr_provider: OCRProvider):
        super().__init__()
        self.ocr_provider = ocr_provider
        self.supported_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]

    async def process(self, file_path: str, source_metadata: Optional[Dict[str, Any]] = None) -> ProcessedDocument:
        """Process an image file using OCR"""
        try:
            # Read image data
            with open(file_path, "rb") as f:
                image_data = f.read()

            # Extract text using OCR
            content = await self.ocr_provider.extract_text(image_data)

            # Extract metadata
            metadata = self._extract_basic_metadata(file_path)
            # In a real implementation, we would extract image-specific metadata
            # like dimensions, color mode, etc. using PIL or similar
            metadata.update({
                "ocr_provider": self.ocr_provider.get_provider_name(),
                "is_image": True,
                "content_length": len(content),
                "word_count": len(content.split()) if content.strip() else 0
            })

            # Add source metadata if provided
            if source_metadata:
                metadata.update(source_metadata)

            # Create chunks (simple approach for OCR text)
            chunks = self._create_chunks_from_ocr_text(content)

            document_id = f"img_{metadata['checksum'][:8]}"
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
            logger.error(f"Error processing image file {file_path}: {str(e)}")
            raise

    def _create_chunks_from_ocr_text(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """Create chunks from OCR text (similar to text processor)"""
        if not content.strip():
            return []

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

# Example OCR provider implementations (would be implemented based on chosen OCR service)
class TesseractOCRProvider(OCRProvider):
    """Tesseract OCR provider"""

    async def extract_text(self, image_data: bytes) -> str:
        # In a real implementation, this would use pytesseract
        # For now, return placeholder
        logger.warning("Tesseract OCR not implemented - returning empty string")
        return ""

    def get_provider_name(self) -> str:
        return "tesseract"

class EasyOCRProvider(OCRProvider):
    """EasyOCR provider"""

    async def extract_text(self, image_data: bytes) -> str:
        # In a real implementation, this would use easyocr
        logger.warning("EasyOCR not implemented - returning empty string")
        return ""

    def get_provider_name(self) -> str:
        return "easyocr"

class AzureOCRProvider(OCRProvider):
    """Azure Computer Vision OCR provider"""

    def __init__(self, endpoint: str, key: str):
        self.endpoint = endpoint
        self.key = key

    async def extract_text(self, image_data: bytes) -> str:
        # In a real implementation, this would call Azure Computer Vision API
        logger.warning("Azure OCR not implemented - returning empty string")
        return ""

    def get_provider_name(self) -> str:
        return "azure_computer_vision"