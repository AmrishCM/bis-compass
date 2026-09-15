from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import json
import logging

from app.db.session import get_db
from app.models.standard import AuditLog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audit", tags=["Audit Trail & Governance"])

@router.get("", summary="Get System Audit Logs")
def get_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    
    total = query.count()
    logs = query.order_by(AuditLog.id.desc()).offset(offset).limit(limit).all()

    results = []
    for log in logs:
        sources = []
        try:
            if log.retrieval_sources:
                sources = json.loads(log.retrieval_sources) if isinstance(log.retrieval_sources, str) else log.retrieval_sources
        except Exception:
            sources = [str(log.retrieval_sources)]

        citations = []
        try:
            if log.citations:
                citations = json.loads(log.citations) if isinstance(log.citations, str) else log.citations
        except Exception:
            citations = [str(log.citations)]

        results.append({
            "id": log.id,
            "user_id": log.user_id or "Anonymous User",
            "action": log.action,
            "query": log.query,
            "selected_model": log.selected_model or "Configured LLM",
            "retrieval_sources": sources,
            "citations": citations,
            "execution_time_ms": log.execution_time_ms or 0,
            "created_at": log.created_at.isoformat() if log.created_at else None
        })

    return {
        "success": True,
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": results
    }
