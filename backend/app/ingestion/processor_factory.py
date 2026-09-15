from typing import Dict, Type, Optional, List
from .base_processor import BaseDocumentProcessor
from .text_processor import TextProcessor
from .pdf_processor import PDFProcessor
from .docx_processor import DOCXProcessor
from .image_processor import BaseImageProcessor, TesseractOCRProvider, EasyOCRProvider, AzureOCRProvider
import logging

logger = logging.getLogger(__name__)

class DocumentProcessorFactory:
    """Factory for creating document processors based on file extension"""

    def __init__(self):
        self._processors: Dict[str, Type[BaseDocumentProcessor]] = {}
        self._register_default_processors()

    def _register_default_processors(self):
        """Register default document processors"""
        self.register_processor(".txt", TextProcessor)
        self.register_processor(".text", TextProcessor)
        self.register_processor(".md", TextProcessor)
        self.register_processor(".rst", TextProcessor)
        self.register_processor(".pdf", PDFProcessor)
        self.register_processor(".docx", DOCXProcessor)
        self.register_processor(".doc", DOCXProcessor)
        # Image processors need special handling due to OCR dependency
        # They will be handled separately

    def register_processor(self, extension: str, processor_class: Type[BaseDocumentProcessor]):
        """Register a processor for a file extension"""
        self._processors[extension.lower()] = processor_class
        logger.debug(f"Registered processor {processor_class.__name__} for extension {extension}")

    def get_processor(self, file_path: str) -> Optional[BaseDocumentProcessor]:
        """Get appropriate processor for a file"""
        from pathlib import Path
        extension = Path(file_path).suffix.lower()
        processor_class = self._processors.get(extension)

        if processor_class:
            try:
                return processor_class()
            except Exception as e:
                logger.error(f"Error instantiating processor {processor_class}: {str(e)}")
                return None

        return None

    def get_image_processor(self, file_path: str, ocr_provider_type: str = "tesseract", **ocr_kwargs) -> Optional[BaseImageProcessor]:
        """Get an image processor with specified OCR provider"""
        from pathlib import Path
        extension = Path(file_path).suffix.lower()

        image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]
        if extension not in image_extensions:
            return None

        # Create OCR provider based on type
        ocr_provider = None
        if ocr_provider_type.lower() == "tesseract":
            ocr_provider = TesseractOCRProvider()
        elif ocr_provider_type.lower() == "easyocr":
            ocr_provider = EasyOCRProvider()
        elif ocr_provider_type.lower() == "azure":
            ocr_provider = AzureOCRProvider(**ocr_kwargs)
        else:
            logger.warning(f"Unknown OCR provider type: {ocr_provider_type}, defaulting to tesseract")
            ocr_provider = TesseractOCRProvider()

        try:
            # We need to create a concrete image processor class
            # For simplicity, we'll dynamically create one
            class ConcreteImageProcessor(BaseImageProcessor):
                def __init__(self, ocr_provider):
                    super().__init__(ocr_provider)

            return ConcreteImageProcessor(ocr_provider)
        except Exception as e:
            logger.error(f"Error creating image processor: {str(e)}")
            return None

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions"""
        return list(self._processors.keys())

# Global factory instance
_processor_factory: Optional[DocumentProcessorFactory] = None

def get_processor_factory() -> DocumentProcessorFactory:
    """Get the global document processor factory"""
    global _processor_factory
    if _processor_factory is None:
        _processor_factory = DocumentProcessorFactory()
    return _processor_factory