from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from app.agents.compliance_gap_agent import get_compliance_gap_agent, DocumentAnalysisContext
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.standard import Standard

from app.agents.orchestrator_agent import OrchestratorAgent, OrchestrationInput

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/compliance", tags=["Compliance Gap Analyzer"])

class ComplianceCheckRequest(BaseModel):
    standard_id: Optional[int] = Field(None, description="ID of the target BIS standard (optional if researching live)")
    document_text: str = Field(..., description="Raw text of product specification, manual, or test report", min_length=10)
    product_description: Optional[str] = Field(None, description="Optional description of product or inferred from document")
    document_title: Optional[str] = Field("Product Documentation", description="Title or filename")
    product_category: Optional[str] = Field(None, description="Optional category hint")

@router.post("/analyze", summary="Analyze Document Compliance Against a Target or Dynamically Researched Standard")
async def analyze_compliance_gap(
    payload: ComplianceCheckRequest,
    db: Session = Depends(get_db)
):
    """
    Performs clause-level compliance gap analysis:
    - If standard_id is omitted, dynamically discovers applicable standards from live authoritative sources
    - Matches document assertions against discovered standard requirements
    - Identifies fulfilled requirements with clause references
    - Identifies missing requirements and actionable remediation
    - Computes compliance readiness percentage and risk level
    """
    if not payload.standard_id:
        # Dynamic live research path
        orchestrator = OrchestratorAgent()
        desc = payload.product_description or payload.document_title or payload.document_text[:300]
        orch_res = await orchestrator.run_full_certification_analysis(
            OrchestrationInput(
                product_description=desc,
                document_text=payload.document_text,
                include_web_search=True
            )
        )
        if orch_res.compliance_analysis:
            res = orch_res.compliance_analysis[0]
            return {
                "success": True,
                "standard_id": res.standard_id,
                "standard_number": res.standard_number,
                "standard_title": res.standard_title,
                "compliance_percentage": res.compliance_percentage,
                "confidence": res.confidence,
                "risk_level": res.risk_level,
                "fulfilled_requirements": [
                    {
                        "id": getattr(r, 'requirement_id', ''),
                        "description": getattr(r, 'description', ''),
                        "type": getattr(r, 'requirement_type', 'General'),
                        "is_mandatory": getattr(r, 'is_mandatory', True),
                        "source_reference": getattr(r, 'source_reference', {}),
                        "details": getattr(r, 'details', {})
                    } for r in res.fulfilled_requirements
                ],
                "missing_requirements": [
                    {
                        "id": getattr(r, 'requirement_id', ''),
                        "description": getattr(r, 'description', ''),
                        "type": getattr(r, 'requirement_type', 'General'),
                        "is_mandatory": getattr(r, 'is_mandatory', True),
                        "source_reference": getattr(r, 'source_reference', {}),
                        "details": getattr(r, 'details', {})
                    } for r in res.missing_requirements
                ],
                "partial_requirements": [
                    {
                        "id": getattr(r, 'requirement_id', ''),
                        "description": getattr(r, 'description', ''),
                        "type": getattr(r, 'requirement_type', 'General'),
                        "is_mandatory": getattr(r, 'is_mandatory', True),
                        "source_reference": getattr(r, 'source_reference', {}),
                        "details": getattr(r, 'details', {})
                    } for r in getattr(res, 'partial_requirements', [])
                ],
                "recommendations": res.recommendations,
                "sources_investigated": orch_res.sources_investigated,
                "pipeline": orch_res.pipeline_stats
            }
        else:
            return {
                "success": False,
                "message": orch_res.overall_assessment or "Could not verify applicable standards for document.",
                "sources_investigated": orch_res.sources_investigated
            }

    std = db.query(Standard).filter(Standard.id == payload.standard_id).first()
    if not std:
        raise HTTPException(status_code=404, detail=f"Standard ID {payload.standard_id} not found")

    try:
        agent = get_compliance_gap_agent()
        context = DocumentAnalysisContext(
            document_content=payload.document_text,
            document_metadata={
                "title": payload.document_title or "Product Documentation",
                "category": payload.product_category or "General"
            },
            target_standard_ids=[payload.standard_id]
        )

        results = await agent.analyze_compliance_gaps(context)
        if not results:
            return {
                "success": True,
                "standard_id": std.id,
                "standard_number": std.standard_number,
                "standard_title": std.title,
                "compliance_percentage": 50.0,
                "confidence": 0.6,
                "risk_level": "Medium",
                "fulfilled_requirements": [],
                "missing_requirements": [],
                "partial_requirements": [],
                "recommendations": ["Review product documentation against standard requirements."],
                "source_documents": []
            }

        result = results[0]

        return {
            "success": True,
            "standard_id": result.standard_id,
            "standard_number": result.standard_number,
            "standard_title": result.standard_title,
            "compliance_percentage": result.compliance_percentage,
            "confidence": result.confidence,
            "risk_level": result.risk_level,
            "fulfilled_requirements": [
                {
                    "id": r.requirement_id,
                    "description": r.description,
                    "type": r.requirement_type,
                    "is_mandatory": r.is_mandatory,
                    "source_reference": r.source_reference,
                    "details": r.details
                } for r in result.fulfilled_requirements
            ],
            "missing_requirements": [
                {
                    "id": r.requirement_id,
                    "description": r.description,
                    "type": r.requirement_type,
                    "is_mandatory": r.is_mandatory,
                    "source_reference": r.source_reference,
                    "details": r.details
                } for r in result.missing_requirements
            ],
            "partial_requirements": [
                {
                    "id": r.requirement_id,
                    "description": r.description,
                    "type": r.requirement_type,
                    "is_mandatory": r.is_mandatory,
                    "source_reference": r.source_reference,
                    "details": r.details
                } for r in result.partial_requirements
            ],
            "recommendations": result.recommendations,
            "source_documents": result.source_documents
        }
    except Exception as e:
        logger.error(f"Compliance gap analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
