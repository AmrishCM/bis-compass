from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional
import tempfile
import os
import logging
from pathlib import Path

from app.ingestion.processor_factory import get_processor_factory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Document Ingestion & OCR"])

@router.post("/upload", summary="Upload Product Specification, Test Sheet, or Manual")
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form("specification")
):
    """
    Extract readable text from PDF, DOCX, TXT, or image files
    using PyMuPDF, python-docx, or text processors.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")

    suffix = Path(file.filename).suffix.lower()
    allowed = [".pdf", ".docx", ".doc", ".txt", ".md"]
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{suffix}'. Allowed: {', '.join(allowed)}"
        )

    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        factory = get_processor_factory()
        processor = factory.get_processor(tmp_path)
        if not processor:
            raise HTTPException(status_code=400, detail=f"No processor available for {suffix}")

        processed_doc = await processor.process(tmp_path)
        extracted_text = processed_doc.content if hasattr(processed_doc, "content") else str(processed_doc)
        chunks = processed_doc.chunks if hasattr(processed_doc, "chunks") else []
        metadata = processed_doc.metadata if hasattr(processed_doc, "metadata") else {}
        char_count = len(extracted_text)
        word_count = len(extracted_text.split())

        return {
            "success": True,
            "filename": file.filename,
            "document_type": document_type,
            "file_size_bytes": len(content),
            "character_count": char_count,
            "word_count": word_count,
            "extracted_text": extracted_text,
            "chunks": chunks,
            "metadata": metadata,
            "preview": extracted_text[:500] + ("..." if char_count > 500 else "")
        }

    except Exception as e:
        logger.error(f"Document extraction failed for {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
