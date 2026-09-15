from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import time
import json
import logging

from app.agents.orchestrator_agent import OrchestratorAgent, OrchestrationInput
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.standard import AuditLog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["Product Compliance Analysis"])

class AnalyzeRequest(BaseModel):
    product_description: str = Field(..., description="Natural language description of product", example="We manufacture stainless-steel drinking bottles for household use.")
    document_text: Optional[str] = Field(None, description="Technical specification or manual text for gap analysis")
    target_standard_ids: Optional[List[int]] = Field(None, description="Optional target standard IDs")
    location: Optional[str] = Field(None, description="City/State for laboratory proximity filtering", example="Delhi")
    include_web_search: bool = Field(True, description="Enable live official web retrieval (default: True)")

@router.post("", summary="Perform End-to-End Product Standards & Compliance Analysis")
async def analyze_product(
    payload: AnalyzeRequest,
    db: Session = Depends(get_db)
):
    """
    Flagship Analysis Endpoint:
    1. Extracts structured product understanding
    2. Retrieves candidate standards via hybrid search
    3. Performs clause-by-clause applicability matching ('Why does it apply?')
    4. Determines certification path (ISI Mark / CRS / etc.)
    5. Retrieves testing requirements and parameters
    6. Identifies accredited testing laboratories
    7. Performs compliance gap analysis if document text is provided
    8. Validates citations and generates actionable compliance roadmap
    """
    start_time = time.time()
    orchestrator = OrchestratorAgent()

    try:
        input_data = OrchestrationInput(
            product_description=payload.product_description,
            document_text=payload.document_text,
            target_standard_ids=payload.target_standard_ids,
            location=payload.location,
            include_web_search=payload.include_web_search
        )

        result = await orchestrator.run_full_certification_analysis(input_data)
        elapsed_ms = int((time.time() - start_time) * 1000)

        # Convert result objects to serialized dict
        standards_out = []
        for s in result.applicable_standards:
            meta = s.metadata or {}
            standards_out.append({
                "standard_id": s.standard_id,
                "standard_number": s.standard_number,
                "title": s.title,
                "applicability_score": s.applicability_score,
                "confidence": s.confidence,
                "reasoning": s.reasoning,
                "supporting_clauses": s.supporting_clauses,
                "status": getattr(s, 'status', meta.get('status', 'APPLICABLE')),
                "confirmed_attributes": getattr(s, 'confirmed_attributes', meta.get('confirmed_attributes', [])),
                "metadata": s.metadata
            })

        potential_out = []
        for s in getattr(result, 'potential_standards', []):
            meta = s.metadata or {}
            potential_out.append({
                "standard_id": s.standard_id,
                "standard_number": s.standard_number,
                "title": s.title,
                "applicability_score": s.applicability_score,
                "confidence": s.confidence,
                "reasoning": s.reasoning,
                "supporting_clauses": s.supporting_clauses,
                "status": getattr(s, 'status', meta.get('status', 'NEEDS_CLARIFICATION')),
                "confirmed_attributes": getattr(s, 'confirmed_attributes', meta.get('confirmed_attributes', [])),
                "missing_information": getattr(s, 'missing_information', meta.get('missing_information', [])),
                "clarification_questions": getattr(s, 'clarification_questions', meta.get('clarification_questions', [])),
                "metadata": s.metadata
            })

        cert_out = []
        for c in result.certification_info:
            cert_out.append({
                "standard_id": c.standard_id,
                "standard_number": c.standard_number,
                "certification_scheme": c.certification_scheme,
                "license_required": c.license_required,
                "marking_requirements": [
                    {
                        "requirement_type": m.requirement_type,
                        "description": m.description,
                        "is_mandatory": m.is_mandatory,
                        "source_reference": m.source_reference
                    } for m in c.marking_requirements
                ],
                "testing_requirements": [
                    {
                        "requirement_type": t.requirement_type,
                        "description": t.description,
                        "is_mandatory": t.is_mandatory,
                        "source_reference": t.source_reference
                    } for t in c.testing_requirements
                ],
                "factory_audit_required": c.factory_audit_required,
                "documentation_requirements": c.documentation_requirements,
                "certification_process": [
                    {
                        "step_number": p.step_number,
                        "step_name": p.step_name,
                        "description": p.description,
                        "estimated_time": p.estimated_time,
                        "required_documents": p.required_documents,
                        "responsible_party": p.responsible_party
                    } for p in c.certification_process
                ],
                "validity_period": c.validity_period,
                "sources": c.sources
            })

        testing_out = []
        for t in result.testing_information:
            testing_out.append({
                "standard_id": t.standard_id,
                "standard_number": t.standard_number,
                "testing_requirements": [
                    {
                        "test_type": tr.test_type,
                        "description": tr.description,
                        "is_mandatory": tr.is_mandatory,
                        "source_reference": tr.source_reference,
                        "test_method": tr.test_method,
                        "acceptable_standards": tr.acceptable_standards
                    } for tr in t.testing_requirements
                ],
                "laboratories": [
                    {
                        "lab_name": lab.lab_name,
                        "address": lab.address,
                        "contact_person": lab.contact_person,
                        "phone": lab.phone,
                        "email": lab.email,
                        "accreditation_body": lab.accreditation_body,
                        "is_bis_recognized": lab.is_bis_recognized,
                        "testing_facilities": lab.testing_facilities
                    } for lab in (t.recommended_laboratories or [])
                ],
                "turnaround_time": getattr(t, 'estimated_testing_time', '7-15 days'),
                "sample_requirements": t.sample_requirements,
                "confidence": getattr(t, 'confidence', 0.8)
            })

        labs_out = []
        for l in result.laboratory_recommendations:
            labs_out.append({
                "lab_id": l.lab_id,
                "lab_name": l.lab_name,
                "address": l.address,
                "location": l.location,
                "contact_person": l.contact_person,
                "phone": l.phone,
                "email": l.email,
                "website": l.website,
                "accreditation_body": l.accreditation_body,
                "accreditation_number": l.accreditation_number,
                "is_bis_recognized": l.is_bis_recognized,
                "bis_recognition_number": l.bis_recognition_number,
                "accredited_scopes": l.accredited_scopes,
                "testing_facilities": l.testing_facilities,
                "geographical_coverage": l.geographical_coverage,
                "sample_collection_facility": l.sample_collection_facility,
                "match_score": l.match_score,
                "match_reasons": l.match_reasons,
                "source": getattr(l, 'source', [])
            })

        comp_out = []
        for g in result.compliance_analysis:
            comp_out.append({
                "standard_id": g.standard_id,
                "standard_number": g.standard_number,
                "standard_title": g.standard_title,
                "compliance_percentage": g.compliance_percentage,
                "confidence": g.confidence,
                "risk_level": g.risk_level,
                "fulfilled_requirements": [
                    {
                        "id": getattr(r, 'requirement_id', ''),
                        "description": getattr(r, 'description', ''),
                        "type": getattr(r, 'requirement_type', 'General'),
                        "is_mandatory": getattr(r, 'is_mandatory', True),
                        "source_reference": getattr(r, 'source_reference', {}),
                        "details": getattr(r, 'details', {})
                    } for r in g.fulfilled_requirements
                ],
                "missing_requirements": [
                    {
                        "id": getattr(r, 'requirement_id', ''),
                        "description": getattr(r, 'description', ''),
                        "type": getattr(r, 'requirement_type', 'General'),
                        "is_mandatory": getattr(r, 'is_mandatory', True),
                        "source_reference": getattr(r, 'source_reference', {}),
                        "details": getattr(r, 'details', {})
                    } for r in g.missing_requirements
                ],
                "partial_requirements": [
                    {
                        "id": getattr(r, 'requirement_id', ''),
                        "description": getattr(r, 'description', ''),
                        "type": getattr(r, 'requirement_type', 'General'),
                        "is_mandatory": getattr(r, 'is_mandatory', True),
                        "source_reference": getattr(r, 'source_reference', {}),
                        "details": getattr(r, 'details', {})
                    } for r in getattr(g, 'partial_requirements', [])
                ],
                "recommendations": g.recommendations
            })

        # Save audit record
        try:
            import os
            audit = AuditLog(
                action="PRODUCT_ANALYSIS",
                query=payload.product_description,
                selected_model=os.getenv("NVIDIA_CHAT_MODEL", "meta/llama-3.2-11b-vision-instruct"),
                retrieval_sources=json.dumps([s["standard_number"] for s in standards_out]),
                citations=json.dumps([s["standard_number"] for s in standards_out]),
                execution_time_ms=elapsed_ms
            )
            db.add(audit)
            db.commit()
        except Exception as log_err:
            logger.warning(f"Failed to record audit log: {log_err}")

        return {
            "success": True,
            "execution_time_seconds": round(result.execution_time, 3),
            "product_understanding": result.product_understanding.dict() if result.product_understanding else None,
            "clarification_required": getattr(result, 'clarification_required', False),
            "clarification_questions": getattr(result, 'clarification_questions', []),
            "applicable_standards": standards_out,
            "potential_standards": potential_out,
            "related_standards": getattr(result, 'related_standards', []),
            "rejected_candidates": getattr(result, 'rejected_candidates', []),
            "research_trace": getattr(result, 'research_trace', {}),
            "certification_info": cert_out,
            "testing_information": testing_out,
            "laboratory_recommendations": labs_out,
            "compliance_analysis": comp_out,
            "web_search_results": [
                {
                    "title": w.title,
                    "url": w.url,
                    "snippet": w.snippet,
                    "domain": w.domain,
                    "authority_score": w.authority_score
                } for w in result.web_search_results
            ],
            "research_stages": getattr(result, 'research_stages', []),
            "sources_investigated": getattr(result, 'sources_investigated', []),
            "is_live_research": getattr(result, 'is_live_research', True),
            "session_id": getattr(result, 'session_id', None),
            "pipeline": getattr(result, 'pipeline_stats', {
                "sources_examined": len(getattr(result, 'sources_investigated', [])),
                "authoritative_sources_used": len([s for s in getattr(result, 'sources_investigated', []) if s.get('authority_tier', 5) <= 3]),
                "retrieved_candidates": len(standards_out),
                "scope_filtered": len(getattr(result, 'rejected_candidates', [])),
                "applicable": len(standards_out),
                "rejected": len(getattr(result, 'rejected_candidates', [])),
                "is_live_research": True,
                "web_search_used": payload.include_web_search
            }),
            "overall_assessment": result.overall_assessment,
            "recommendations": result.recommendations,
            "what_you_need_to_do": getattr(result, 'what_you_need_to_do', {}),
            "canonical_decision": getattr(result, 'canonical_decision', {}),
            "agent_execution_times": result.agent_execution_times
        }

    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Compliance analysis failed: {str(e)}")
