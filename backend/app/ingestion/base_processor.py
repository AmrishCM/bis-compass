from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib

@dataclass
class ProcessedDocument:
    """Result of document processing"""
    content: str
    metadata: Dict[str, Any]
    chunks: List[Dict[str, Any]]
    document_id: str
    source_id: str
    processed_at: datetime
    file_size: int
    checksum: str

class BaseDocumentProcessor(ABC):
    """Base class for document processors"""

    def __init__(self):
        self.supported_extensions = []

    @abstractmethod
    async def process(self, file_path: str, source_metadata: Optional[Dict[str, Any]] = None) -> ProcessedDocument:
        """Process a document and extract content and metadata"""
        pass

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _extract_basic_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract basic file metadata"""
        import os
        import mimetypes
        from pathlib import Path

        file_path_obj = Path(file_path)
        stat = file_path_obj.stat()
        checksum = self._calculate_checksum(file_path)
        return {
            "file_name": file_path_obj.name,
            "file_extension": file_path_obj.suffix.lower(),
            "file_size": stat.st_size,
            "mime_type": mimetypes.guess_type(file_path)[0] or "application/octet-stream",
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "checksum": checksum,
        }