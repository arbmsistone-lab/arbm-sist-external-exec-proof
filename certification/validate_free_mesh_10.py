import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'governance' / 'multi-provider-runtime-v1.json'

def main():
    data = json.loads(POLICY.read_text(encoding='utf-8'))
    routes = data.get('supported_ai_free_routes') or []
    assert data.get('minimum_independent_providers') == 10
    assert data.get('minimum_qualified_free_routes') == 10
    assert data.get('zero_spend_hard') is True
    assert data.get('quota_exhaustion_must_failover') is True
    assert data.get('quota_exhaustion_action') == 'immediate-rotate-with-cooldown'
    assert len(set(routes)) >= 10
    required = {'configured','healthy','zero-cost','quota-available','independent-domain'}
    assert required.issubset(set(data.get('qualification_requires') or []))
    print('ARBM_SIST_FREE_MESH_10=PASS')

if __name__ == '__main__':
    main()
