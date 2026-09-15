import urllib.request
import json
import sys

payload = json.dumps({
    'product_description': '100% Combed Cotton T-Shirt',
    'location': 'Delhi',
    'include_web_search': True
}).encode('utf-8')

req = urllib.request.Request(
    'http://127.0.0.1:8002/api/analyze',
    data=payload,
    headers={'Content-Type': 'application/json'}
)

try:
    print("Calling POST /api/analyze with '100% Combed Cotton T-Shirt'...")
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.loads(r.read().decode('utf-8'))
        print("\n=== END-TO-END ANALYSIS VERIFICATION RESULTS ===")
        print(f"Success: {res.get('success')}")
        print(f"Runtime: {res.get('execution_time_seconds')}s")
        print(f"Is Live Research: {res.get('is_live_research')}")
        
        pipeline = res.get('pipeline', {})
        sources_examined = pipeline.get('sources_examined', 0)
        official_sources = pipeline.get('authoritative_sources_used', 0)
        print(f"Sources Examined: {sources_examined}")
        print(f"Official BIS/Gov Used: {official_sources}")
        
        app_stds = res.get('applicable_standards', [])
        pot_stds = res.get('potential_standards', [])
        rej_stds = res.get('rejected_candidates', [])
        
        print(f"\nDirectly Applicable Standards: {len(app_stds)}")
        for s in app_stds:
            print(f"  [APPLICABLE] {s.get('standard_number')}: {s.get('title')}")
            
        print(f"\nPotentially Relevant Standards (Needs Clarification): {len(pot_stds)}")
        for p in pot_stds:
            print(f"  [POTENTIAL] {p.get('standard_number')}: {p.get('title')}")
            print(f"    - Confirmed: {p.get('confirmed_attributes')}")
            print(f"    - Missing: {p.get('missing_information')}")
            print(f"    - Questions: {p.get('clarification_questions')}")
            
        print(f"\nRejected Candidates: {len(rej_stds)}")
        for rj in rej_stds[:5]:
            print(f"  [REJECTED] {rj.get('standard_number')}: {rj.get('reason')}")
            
        # Seed standard check
        seed_numbers = ['IS 17526', 'IS 694', 'IS 302-2-15', 'IS 16046']
        seed_leak = [r for r in rej_stds if any(sn in r.get('standard_number', '') for sn in seed_numbers)]
        print(f"\nSeed Standards Leaked: {len(seed_leak)}")
        
        trace = res.get('research_trace', {})
        queries = trace.get('queries_executed', [])
        print(f"\nResearch Execution Trace Queries ({len(queries)}):")
        for q in queries:
            print(f"  - [{q.get('provider')}] '{q.get('query')}' -> {q.get('results_count')} results")
            
        print(f"\nClarification Required: {res.get('clarification_required')}")
        print(f"Clarification Questions: {res.get('clarification_questions')}")
        
        # Assertions
        assert official_sources > 0, "FAILED: Official BIS/Gov sources used should be > 0"
        assert len(seed_leak) == 0, "FAILED: Seed standards leaked into evaluation"
        has_4375 = any("4375" in (p.get('standard_number') or '') for p in pot_stds)
        print(f"\nIS 4375 in potential standards: {has_4375}")
        assert has_4375, "FAILED: IS 4375 should be discovered as a potential standard"
        print("\n>>> ALL ARCHITECTURAL ASSERTIONS PASSED! <<<")
        
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
