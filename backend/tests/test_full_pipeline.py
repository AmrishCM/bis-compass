import asyncio
import os
import sys
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, r"e:\SIH2026\project\BIS-Compass\backend")
load_dotenv(r"e:\SIH2026\project\BIS-Compass\backend\.env", override=True)

from app.services.llm.provider_factory import LLMProviderFactory, get_llm_provider
from app.services.retrieval.hybrid_retriever import HybridRetriever
from app.db.session import SessionLocal
from app.services.research.search_providers import DDGSSearchProvider
from app.services.products.open_world_analyzer import OpenWorldProductAnalyzer
from app.agents.orchestrator_agent import OrchestratorAgent, OrchestrationInput
from app.api.routes.analyze import _build_analysis_response

async def run_diagnostics():
    print("==========================================================")
    print("   BIS-COMPASS FULL SYSTEM & PIPELINE VERIFICATION")
    print("==========================================================")

    # 1. Test LLM 1: NVIDIA
    print("\n[1/6] Testing LLM 1: NVIDIA NIM...")
    try:
        nvidia = LLMProviderFactory.create_provider(provider_type="nvidia")
        res_nv = await nvidia.chat([{"role": "user", "content": "Respond 'OK' and nothing else."}])
        print(f"  [PASS] NVIDIA Chat: {res_nv.content.strip()[:60]} (model: {res_nv.model})")
    except Exception as e:
        print(f"  [FAIL] NVIDIA Chat Error: {e}")

    # 2. Test LLM 2: Groq
    print("\n[2/6] Testing LLM 2: Groq...")
    try:
        groq = LLMProviderFactory.create_provider(provider_type="groq")
        res_gr = await groq.chat([{"role": "user", "content": "Respond 'OK' and nothing else."}])
        print(f"  [PASS] Groq Chat: {res_gr.content.strip()[:60]} (model: {res_gr.model})")
    except Exception as e:
        print(f"  [FAIL] Groq Chat Error: {e}")

    # 3. Test NVIDIA Live Embeddings
    print("\n[3/6] Testing NVIDIA Live Vector Embeddings...")
    try:
        if hasattr(nvidia, "embed"):
            embs = await nvidia.embed(["Stainless steel water bottle", "Electrical cable"])
            print(f"  [PASS] NVIDIA Embeddings generated: {len(embs)} vectors, dim={len(embs[0])}")
    except Exception as e:
        print(f"  [FAIL] NVIDIA Embeddings Error: {e}")

    # 4. Test Hybrid RAG (Lexical + Vector search on SQLite)
    print("\n[4/6] Testing Hybrid RAG Retriever...")
    db = SessionLocal()
    try:
        retriever = HybridRetriever(db)
        rag_hits = await retriever.hybrid_search("stainless steel water bottle", limit=3)
        print(f"  [PASS] Hybrid Search returned {len(rag_hits)} clauses:")
        for h in rag_hits:
            print(f"    - {h.get('standard_number')} (Clause {h.get('clause_number')}): {h.get('heading')}")
    except Exception as e:
        print(f"  [FAIL] Hybrid Search Error: {e}")
    finally:
        db.close()

    # 5. Test Live Web Retrieval (DDGS)
    print("\n[5/6] Testing Live Web Retrieval...")
    try:
        search_prov = DDGSSearchProvider()
        web_hits = await search_prov.search("BIS standard stainless steel water bottle IS", max_results=3)
        print(f"  [PASS] Web Retrieval returned {len(web_hits)} authoritative hits:")
        for w in web_hits:
            print(f"    - [{w.domain}] {w.title[:65]}")
    except Exception as e:
        print(f"  [FAIL] Web Retrieval Error: {e}")

    # 6. Test End-to-End Orchestrator Pipeline & Answer Generation
    print("\n[6/6] Testing End-to-End Orchestration & Answer Generation...")
    queries = [
        ("I manufacture stainless steel water bottles.", "Tiruppur, Tamil Nadu"),
        ("PVC insulated copper cables for household domestic wiring.", "Delhi")
    ]

    for q_text, loc in queries:
        print(f"\n--- Query: '{q_text}' (Location: {loc}) ---")
        orchestrator = OrchestratorAgent()
        inp = OrchestrationInput(
            product_description=q_text,
            location=loc,
            include_web_search=True
        )
        res = await orchestrator.run_full_certification_analysis(inp)

        print(f"  Final Status: {res.final_status}")
        print(f"  Clarification Required: {res.clarification_required}")
        print(f"  Applicable Standards: {[s.standard_number for s in res.applicable_standards]}")
        for s in res.applicable_standards:
            print(f"    -> Standard: {s.standard_number} - {s.title}")
            print(f"       Reasoning: {s.reasoning[0] if s.reasoning else 'N/A'}")
        print(f"  Certification Info count: {len(res.certification_info)}")
        for c in res.certification_info:
            print(f"    -> Scheme: {c.certification_scheme} (License required: {c.license_required})")
        print(f"  Testing Info count: {len(res.testing_information)}")
        for t in res.testing_information:
            print(f"    -> {len(t.testing_requirements)} test requirements (e.g. {t.testing_requirements[0].test_type if t.testing_requirements else 'N/A'})")
        print(f"  Laboratories count: {len(res.laboratory_recommendations)}")
        for lab in res.laboratory_recommendations[:2]:
            print(f"    -> Lab: {lab.lab_name} ({lab.location})")

        # Test formatting for API response
        with SessionLocal() as db_session:
            response_payload = _build_analysis_response(
                result=res,
                payload_dict={"product_description": q_text, "location": loc, "include_web_search": True},
                db=db_session,
                session_id="TEST-SESSION-001"
            )
            print(f"  API Response State: {response_payload.get('state')}")
            print(f"  Has Standard Block: {response_payload.get('standard') is not None}")
            if response_payload.get('standard'):
                print(f"    Standard: {response_payload['standard'].get('standard_number')} - {response_payload['standard'].get('title')}")
            print(f"  Has Certification Block: {response_payload.get('certification') is not None}")
            print(f"  Tests Block Count: {len(response_payload.get('tests', []))}")
            print(f"  Labs Block Count: {len(response_payload.get('laboratories', []))}")
            print(f"  Application Steps Count: {len(response_payload.get('application_steps', []))}")
            next_act = response_payload.get('next_action') or {}
            print(f"  Next Action: {next_act.get('action')}")

    print("\n==========================================================")
    print("   DIAGNOSTICS COMPLETE")
    print("==========================================================")

if __name__ == "__main__":
    asyncio.run(run_diagnostics())
