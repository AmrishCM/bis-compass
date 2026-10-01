import asyncio
import aiofiles
import os
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
import logging

from app.ingestion.processor_factory import get_processor_factory
from app.ingestion.base_processor import ProcessedDocument
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class DocumentIngestionService:
    """Service for ingesting and processing documents"""

    def __init__(self, upload_dir: Optional[str] = None):
        self.settings = get_settings()
        self.upload_dir = upload_dir or self.settings.UPLOAD_DIR
        self.processor_factory = get_processor_factory()

        # Ensure upload directory exists
        try:
            os.makedirs(self.upload_dir, exist_ok=True)
        except OSError:
            import tempfile
            self.upload_dir = os.path.join(tempfile.gettempdir(), "bis_compass_uploads")
            os.makedirs(self.upload_dir, exist_ok=True)

    async def ingest_file(
        self,
        file_content: Union[bytes, str],
        filename: str,
        source_metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedDocument:
        """Ingest a file from bytes or string content"""
        try:
            # Save file to upload directory
            file_path = await self._save_file(file_content, filename)

            # Process the file
            processed_doc = await self.process_file(file_path, source_metadata)

            logger.info(f"Successfully ingested file: {filename}")
            return processed_doc

        except Exception as e:
            logger.error(f"Error ingesting file {filename}: {str(e)}")
            raise

    async def ingest_url(
        self,
        url: str,
        source_metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedDocument:
        """Ingest a file from a URL"""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

                # Extract filename from URL or headers
                filename = self._extract_filename_from_response(response, url)
                file_content = response.content

                # Ingest the file content
                return await self.ingest_file(file_content, filename, source_metadata)

        except Exception as e:
            logger.error(f"Error ingesting URL {url}: {str(e)}")
            raise

    async def process_file(
        self,
        file_path: str,
        source_metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedDocument:
        """Process an existing file"""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # Get appropriate processor
            processor = self.processor_factory.get_processor(file_path)
            if not processor:
                # Try as image file
                processor = self.processor_factory.get_image_processor(file_path)

            if not processor:
                raise ValueError(f"No processor available for file: {file_path}")

            # Process the file
            processed_doc = await processor.process(file_path, source_metadata)

            logger.info(f"Successfully processed file: {file_path}")
            return processed_doc

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            raise

    async def _save_file(self, file_content: Union[bytes, str], filename: str) -> str:
        """Save file content to upload directory"""
        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        file_path = os.path.join(self.upload_dir, safe_filename)

        # Handle duplicate filenames
        counter = 1
        original_path = file_path
        while os.path.exists(file_path):
            name, ext = os.path.splitext(original_path)
            file_path = f"{name}_{counter}{ext}"
            counter += 1

        # Write file
        if isinstance(file_content, str):
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(file_content)
        else:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)

        return file_path

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        import re
        # Remove path components
        filename = os.path.basename(filename)
        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255 - len(ext)] + ext
        return filename

    def _extract_filename_from_response(self, response, url: str) -> str:
        """Extract filename from HTTP response"""
        # Try to get filename from Content-Disposition header
        content_disposition = response.headers.get("content-disposition")
        if content_disposition:
            import re
            filename_match = re.search(r'filename[*]?=([^;]+)', content_disposition, re.IGNORECASE)
            if filename_match:
                filename = filename_match.group(1).strip('"\'')
                if filename:
                    return filename

        # Try to get filename from URL
        from urllib.parse import urlparse, unquote
        path = urlparse(url).path
        if path:
            filename = unquote(os.path.basename(path))
            if filename and '.' in filename:
                return filename

        # Default filename
        return "downloaded_file"

    async def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions"""
        return self.processor_factory.get_supported_extensions()

    async def is_supported_file(self, filename: str) -> bool:
        """Check if a file extension is supported"""
        ext = Path(filename).suffix.lower()
        supported = await self.get_supported_extensions()
        return ext in supported

# Global service instance
_ingestion_service: Optional[DocumentIngestionService] = None

def get_ingestion_service() -> DocumentIngestionService:
    """Get the global document ingestion service"""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = DocumentIngestionService()
    return _ingestion_service