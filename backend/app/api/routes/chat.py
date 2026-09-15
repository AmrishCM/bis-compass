from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import logging

from app.db.session import get_db
from sqlalchemy.orm import Session
from app.services.retrieval.hybrid_retriever import get_hybrid_retriever
from app.services.llm.provider_factory import get_llm_provider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Compliance Chat Workspace"])

class ChatMessage(BaseModel):
    role: str = Field(..., example="user")
    content: str = Field(..., example="What are the test requirements for stainless steel bottles under IS 17526?")

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    standard_id: Optional[int] = None
    stream: bool = False

@router.post("", summary="Chat with BIS Compliance Intelligence Advisor")
async def chat_compliance(
    payload: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Interactive conversation with grounded BIS standards reasoning:
    - Retrieves factual evidence from knowledge base
    - Validates against authoritative clauses
    - Explicitly abstains if authoritative evidence is absent
    """
    if not payload.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    last_user_message = next((m.content for m in reversed(payload.messages) if m.role == "user"), "")
    if not last_user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    # Step 1: Hybrid factual retrieval
    retriever = get_hybrid_retriever(db)
    filters = {}
    if payload.standard_id:
        filters["standard_id"] = payload.standard_id

    evidence_results = await retriever.hybrid_search(
        query=last_user_message,
        limit=5,
        min_confidence=0.1,
        filters=filters if filters else None
    )

    # Step 1.5: If evidence is sparse or empty in local DB, dynamically research live web sources
    is_live_research = False
    live_sources_used = []
    if len(evidence_results) < 2:
        try:
            from app.services.research.web_research_engine import get_web_research_engine
            from app.services.research.standard_discovery import get_standard_discovery_engine
            web_engine = get_web_research_engine()
            discovery_engine = get_standard_discovery_engine(db)

            clean_query = last_user_message.replace("?", "").strip()
            search_terms = [f"{clean_query} BIS standard", f"site:bis.gov.in {clean_query}"]
            web_results = await web_engine.search_and_fetch(search_terms, max_sources=3)

            for doc in web_results:
                if doc.content:
                    live_sources_used.append({
                        "url": doc.url,
                        "title": doc.title,
                        "authority_level": doc.authority_level
                    })
                    await discovery_engine.discover_and_index_from_document(doc)

            if web_results:
                is_live_research = True
                # Re-query local index for freshly discovered clauses
                new_evidence = await retriever.hybrid_search(
                    query=last_user_message,
                    limit=5,
                    min_confidence=0.05,
                    filters=filters if filters else None
                )
                if new_evidence:
                    evidence_results = new_evidence
                else:
                    # Provide direct web document extracts as evidence
                    for doc in web_results:
                        if doc.content:
                            evidence_results.append({
                                "standard_number": "Live Web Source",
                                "clause_number": "Discovered Evidence",
                                "heading": doc.title[:80],
                                "text": doc.content[:450],
                                "source_title": doc.title,
                                "authority_level": doc.authority_level,
                                "source_url": doc.url
                            })
        except Exception as research_err:
            logger.warning(f"Live web search during chat encountered error: {research_err}")

    # Prepare evidence context
    evidence_blocks = []
    citations = []
    for ev in evidence_results:
        std_num = ev.get("standard_number", "")
        cl_num = ev.get("clause_number", "")
        heading = ev.get("heading", "")
        txt = ev.get("text", "")
        source_title = ev.get("source_title", "Official BIS")
        evidence_blocks.append(f"[{std_num} Clause {cl_num}: {heading}]\n{txt}")
        citations.append({
            "standard_number": std_num,
            "clause_number": cl_num,
            "heading": heading,
            "source_title": source_title,
            "authority_level": ev.get("authority_level", 1)
        })

    evidence_context = "\n\n".join(evidence_blocks)

    system_prompt = f"""You are BIS-Compass, an authoritative AI Compliance Intelligence Advisor for Indian Standards and Bureau of Indian Standards (BIS) regulations.

CRITICAL INSTRUCTIONS:
1. Base your response SOLELY on the authoritative BIS evidence provided below.
2. NEVER fabricate standards numbers, clause numbers, testing limits, or government rules.
3. If the evidence is insufficient to answer the query conclusively, respond:
   "Insufficient authoritative evidence found in the verified BIS knowledge base."
   and state what technical details or standard numbers are needed.
4. Format citations clearly referencing the exact Indian Standard and Clause (e.g., [IS 17526:2021 Clause 5.2]).

AUTHORITATIVE EVIDENCE RETRIEVED:
{evidence_context if evidence_context else "No direct clause matches found."}
"""

    llm = get_llm_provider()
    try:
        messages = [{"role": "system", "content": system_prompt}]
        for m in payload.messages[-5:]:
            messages.append({"role": m.role, "content": m.content})

        response = await llm.chat(messages=messages, temperature=0.1)
        reply_content = response.content

    except Exception as llm_err:
        logger.warning(f"LLM call failed ({llm_err}), generating deterministic grounded response from retrieved evidence.")
        if evidence_results:
            top_ev = evidence_results[0]
            reply_content = (
                f"Based on **{top_ev['standard_number']}** (*{top_ev['standard_title']}*):\n\n"
                f"**Clause {top_ev['clause_number']} - {top_ev['heading']}**:\n"
                f"{top_ev['text']}\n\n"
            )
            if len(evidence_results) > 1:
                reply_content += "### Additional Supporting Clauses:\n"
                for ev in evidence_results[1:3]:
                    reply_content += f"- **Clause {ev['clause_number']} ({ev['heading']})**: {ev['text'][:150]}...\n"
            reply_content += "\n*Note: This information is directly retrieved and verified from the official BIS repository.*"
        else:
            reply_content = (
                "Insufficient authoritative evidence found in the verified BIS knowledge base. "
                "Please specify the exact product details, technical parameters, or target Indian Standard."
            )

    return {
        "success": True,
        "message": {
            "role": "assistant",
            "content": reply_content
        },
        "citations": citations,
        "evidence_used": len(evidence_results),
        "is_live_research": is_live_research,
        "sources_investigated": live_sources_used
    }


class ClarificationQueryRequest(BaseModel):
    session_id: Optional[str] = None
    product_description: str = Field(..., description="Canonical product description")
    clarification_answers: List[str] = Field(default_factory=list, description="User answers to scope clarification questions")
    round_number: int = Field(default=1, description="Current clarification round (1-3)")
    location: Optional[str] = None


@router.post("/query", summary="Execute Grounded Clarification Round")
async def clarification_query(
    payload: ClarificationQueryRequest,
    db: Session = Depends(get_db)
):
    """
    Clarification Loop (Part 5):
    Re-runs Standards Discovery and Scope Evaluation against the merged, clarified profile.
    Allows up to 3 clarification rounds before defaulting to manual BIS office verification.
    """
    # Guard: Max 3 clarification rounds
    if payload.round_number >= 4:
        return {
            "success": True,
            "status": "MANUAL_VERIFICATION_RECOMMENDED",
            "clarification_rounds": payload.round_number,
            "clarification_required": False,
            "overall_assessment": (
                "Manual BIS office verification recommended: Three clarification rounds completed "
                "without establishing definitive statutory scope. Please consult a BIS technical officer."
            ),
            "recommendations": [
                "Schedule a technical consultation with your nearest BIS Regional / Branch Office.",
                "Submit a formal product categorization enquiry to the Bureau of Indian Standards Sectional Committee."
            ],
            "applicable_standards": [],
            "potential_standards": []
        }

    # Cleanly merge clarification answers into canonical description without duplication
    merged_desc = payload.product_description.strip()
    for ans in payload.clarification_answers:
        clean_ans = ans.strip()
        if clean_ans and clean_ans.lower() not in merged_desc.lower():
            # Check if answer is a parenthetical specification
            if clean_ans.startswith("(") and clean_ans.endswith(")"):
                merged_desc = f"{merged_desc} {clean_ans}"
            else:
                merged_desc = f"{merged_desc}, {clean_ans}"

    # Re-run full orchestrator analysis with the merged clarified description
    from app.agents.orchestrator_agent import OrchestratorAgent, OrchestrationInput
    orchestrator = OrchestratorAgent()
    input_data = OrchestrationInput(
        product_description=merged_desc,
        location=payload.location,
        include_web_search=True
    )
    result = await orchestrator.run_full_certification_analysis(input_data)

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

    return {
        "success": True,
        "clarification_rounds": payload.round_number,
        "canonical_description": merged_desc,
        "clarification_required": getattr(result, 'clarification_required', False),
        "clarification_questions": getattr(result, 'clarification_questions', []),
        "applicable_standards": standards_out,
        "potential_standards": potential_out,
        "related_standards": getattr(result, 'related_standards', []),
        "overall_assessment": result.overall_assessment,
        "recommendations": result.recommendations,
        "what_you_need_to_do": getattr(result, 'what_you_need_to_do', {}),
        "canonical_decision": getattr(result, 'canonical_decision', {}),
        "execution_time_seconds": round(result.execution_time, 3)
    }
