import urllib.request
import json

payload = json.dumps({
    'product_description': "100% Combed Cotton T-Shirt (Men's knitted sports shirt/T-shirt)",
    'location': 'Delhi',
    'include_web_search': True
}).encode('utf-8')

req = urllib.request.Request(
    'http://127.0.0.1:8002/api/analyze',
    data=payload,
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req, timeout=45) as r:
        res = json.loads(r.read().decode('utf-8'))
        print("=== CLARIFIED PRODUCT VERIFICATION ===")
        print(f"Directly Applicable Standards: {len(res.get('applicable_standards', []))}")
        for s in res.get('applicable_standards', []):
            print(f"  [APPLICABLE] {s.get('standard_number')}: {s.get('title')} (Match: {s.get('applicability_score')}/100)")
        print(f"Potential Standards: {len(res.get('potential_standards', []))}")
        print(f"Clarification Required: {res.get('clarification_required')}")
        print("========================================")
except Exception as e:
    print(f"Error: {e}")
