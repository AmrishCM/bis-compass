from fastapi import APIRouter, Depends, HTTPException
from typing import List
import logging
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.standard import Source, Standard

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sources", tags=["Authoritative Knowledge Sources"])

@router.get("", summary="List Verified Sources with Authority Levels and Checksums")
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(Source).order_by(Source.authority_level.asc()).all()

    results = []
    for s in sources:
        standards_count = db.query(Standard).filter(Standard.source_id == s.id).count()
        results.append({
            "id": s.id,
            "organization": s.organization,
            "title": s.title,
            "url": s.url,
            "source_type": s.source_type,
            "authority_level": s.authority_level,
            "authority_label": "Official BIS" if s.authority_level == 1 else ("Government Portal" if s.authority_level == 2 else "Regulatory / Ministry"),
            "publication_date": s.publication_date.isoformat() if s.publication_date else None,
            "last_verified": s.last_verified.isoformat() if s.last_verified else None,
            "version": s.version,
            "checksum": s.checksum,
            "standards_count": standards_count,
            "is_authoritative": s.authority_level <= 3
        })

    return {
        "success": True,
        "total": len(results),
        "sources": results
    }
