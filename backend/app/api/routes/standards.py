from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
import logging
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.standard import Standard, Clause, Scheme, Source

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/standards", tags=["Indian Standards Directory"])

@router.get("", summary="List & Search Indian Standards")
def list_standards(
    q: Optional[str] = Query(None, description="Search term in standard number or title"),
    status: Optional[str] = Query(None, description="Filter by status (active, under_revision, etc.)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(Standard).join(Source)

    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            (Standard.standard_number.ilike(search_pattern)) |
            (Standard.title.ilike(search_pattern)) |
            (Standard.scope.ilike(search_pattern))
        )

    if status:
        query = query.filter(Standard.status == status)

    total = query.count()
    standards = query.order_by(Standard.id.asc()).offset(offset).limit(limit).all()

    results = []
    for s in standards:
        results.append({
            "id": s.id,
            "standard_number": s.standard_number,
            "title": s.title,
            "scope": s.scope,
            "status": s.status,
            "edition": s.edition,
            "publication_date": s.publication_date.isoformat() if s.publication_date else None,
            "effective_date": s.effective_date.isoformat() if s.effective_date else None,
            "clause_count": len(s.clauses),
            "scheme_count": len(s.schemes),
            "source": {
                "organization": s.source.organization if s.source else "BIS",
                "authority_level": s.source.authority_level if s.source else 1,
                "url": s.source.url if s.source else None
            } if s.source else None
        })

    return {
        "success": True,
        "total": total,
        "limit": limit,
        "offset": offset,
        "standards": results
    }

@router.get("/{standard_id}", summary="Get Indian Standard Details with Clauses and Schemes")
def get_standard_detail(
    standard_id: int,
    db: Session = Depends(get_db)
):
    std = db.query(Standard).filter(Standard.id == standard_id).first()
    if not std:
        raise HTTPException(status_code=404, detail=f"Standard ID {standard_id} not found")

    clauses = db.query(Clause).filter(Clause.standard_id == standard_id).order_by(Clause.id.asc()).all()
    schemes = db.query(Scheme).filter(Scheme.standard_id == standard_id).all()

    return {
        "success": True,
        "standard": {
            "id": std.id,
            "standard_number": std.standard_number,
            "title": std.title,
            "scope": std.scope,
            "status": std.status,
            "edition": std.edition,
            "publication_date": std.publication_date.isoformat() if std.publication_date else None,
            "effective_date": std.effective_date.isoformat() if std.effective_date else None,
            "source": {
                "organization": std.source.organization,
                "title": std.source.title,
                "url": std.source.url,
                "authority_level": std.source.authority_level,
                "version": std.source.version,
                "checksum": std.source.checksum
            } if std.source else None,
            "clauses": [
                {
                    "id": c.id,
                    "clause_number": c.clause_number,
                    "heading": c.heading,
                    "text": c.text,
                    "page": c.page,
                    "section": c.section
                } for c in clauses
            ],
            "schemes": [
                {
                    "id": sc.id,
                    "scheme_name": sc.scheme_name,
                    "description": sc.description,
                    "conditions": sc.conditions,
                    "documents_required": sc.documents_required,
                    "testing_required": sc.testing_required
                } for sc in schemes
            ]
        }
    }
