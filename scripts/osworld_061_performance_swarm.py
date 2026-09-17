"""Bounded-concurrency ZERO_SPEND fast path for the post-focal 061 specialist swarm.

This module is deliberately additive. It preserves the exact 10-role quorum and
fail-closed acceptance rules while avoiding heavyweight local model startup when
the already-admitted FREE remote routes can produce all ten valid reviews. The
existing evidence-aware swarm remains the authoritative full-failover path.
"""
import copy
import json
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import osworld_061_evidence_aware_swarm as evidence_aware
import osworld_061_specialist_swarm as swarm
from osworld_groq_free import GROQ_FREE_ROUTE, GroqFreeRoute
from osworld_openrouter_free import FREE_ROUTE, FreeRoute


def _bind_validated_official_evidence(root):
    """Apply the same post-focal evidence binding as the full-failover wrapper."""
    evidence_aware.OFFICIAL = evidence_aware.load_official(root)
    swarm.BASE_SYSTEM = swarm.BASE_SYSTEM.replace(
        'This is a pre-focal source audit: runtime proof belongs in required_proofs;\n'
        'absence of runtime proof alone is not a source-level veto.',
        'This is a post-focal audit. Validated approved official focal evidence is supplied. '
        'Do not request proof already present there; veto only for a concrete remaining causal gap or regression. '
        'A REJECT_FIX verdict must name that concrete gap in causal_chain; otherwise return PASS_FIX or INSUFFICIENT without veto.')
    swarm._text_messages = evidence_aware.txt
    swarm._vlm_messages = evidence_aware.vlm
    swarm._local_evidence = evidence_aware.loc
    swarm._local_binary_review = evidence_aware.binary


def _clone_free_route(source):
    """Create an isolated warmed OpenRouter route for one concurrent reviewer."""
    route = FreeRoute(transport=source.transport, clock=source.clock)
    route.models = copy.deepcopy(source.models)
    route.catalog_until = source.catalog_until
    route.catalog_hash = source.catalog_hash
    route.auth_until = source.auth_until
    route.states = copy.deepcopy(source.states)
    route.provider_until = source.provider_until
    return route


def _clone_groq_route(source):
    """Create an isolated Groq route so cooldown state is never shared by threads."""
    route = GroqFreeRoute(transport=source.transport, clock=source.clock)
    route.until = source.until
    return route


def _bounded_workers():
    try:
        requested = int(os.environ.get('ARBM_SWARM_REMOTE_WORKERS', '3'))
    except ValueError:
        requested = 3
    return max(1, min(4, requested))


def _remote_robot(index, name, brief, evidence, contract, image, probe_evidence,
                  free_route, groq_route):
    """Run one specialist through FREE remote routes only, preserving schema repair."""
    system = swarm.role_prompt(name, brief, contract)
    attempts = []
    raw_outputs = []
    for label, route, budget in (
        ('openrouter', free_route, 140),
        ('groq', groq_route, 120),
    ):
        result = swarm.ask(route, swarm._text_messages(system, evidence, probe_evidence), budget)
        attempts.extend(result.get('attempts') or [])
        raw_outputs.append({'provider': label, 'raw': str(result.get('raw') or '')[-1200:]})
        verdict = swarm.canonicalize_shape(result.get('verdict'))
        if swarm.valid_verdict(verdict, name):
            return {'role': name, 'specialty': brief, 'provider': label,
                    'verdict': verdict, 'attempts': attempts, 'raw_outputs': raw_outputs}
        raw = str(result.get('raw') or '')
        if raw:
            repaired = swarm.ask(route, swarm._repair_messages(name, raw), 100)
            attempts.extend(repaired.get('attempts') or [])
            raw_outputs.append({'provider': label + '-schema-repair',
                                'raw': str(repaired.get('raw') or '')[-1200:]})
            verdict = swarm.canonicalize_shape(repaired.get('verdict'))
            if swarm.valid_verdict(verdict, name):
                return {'role': name, 'specialty': brief, 'provider': label + '-schema-repair',
                        'verdict': verdict, 'attempts': attempts, 'raw_outputs': raw_outputs}
    return {'role': name, 'specialty': brief, 'provider': None, 'verdict': None,
            'attempts': attempts, 'raw_outputs': raw_outputs}


def _skipped_robot(name, brief):
    return {'role': name, 'specialty': brief, 'provider': None, 'verdict': None,
            'attempts': [{'route': 'remote-fast-path', 'mandatory_cost_usd': 0,
                          'paid_fallback_used': False,
                          'status': 'short_circuited_after_warmup_failure'}],
            'raw_outputs': []}


def _run_remote_robots(evidence, contract, image, probe_evidence):
    """Warm one route serially, then review the remaining roles with bounded concurrency."""
    first_name, first_brief = swarm.ROLES[0]
    first = _remote_robot(0, first_name, first_brief, evidence, contract, image,
                          probe_evidence, FREE_ROUTE, GROQ_FREE_ROUTE)
    if not swarm.valid_verdict(first.get('verdict'), first_name):
        return [first] + [_skipped_robot(name, brief) for name, brief in swarm.ROLES[1:]]

    workers = _bounded_workers()
    by_index = {0: first}
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='arbm061-review') as pool:
        futures = {}
        for index, (name, brief) in enumerate(swarm.ROLES[1:], start=1):
            future = pool.submit(
                _remote_robot, index, name, brief, evidence, contract, image, probe_evidence,
                _clone_free_route(FREE_ROUTE), _clone_groq_route(GROQ_FREE_ROUTE))
            futures[future] = index
        for future in as_completed(futures):
            index = futures[future]
            try:
                by_index[index] = future.result()
            except Exception as exc:
                name, brief = swarm.ROLES[index]
                by_index[index] = {
                    'role': name, 'specialty': brief, 'provider': None, 'verdict': None,
                    'attempts': [{'route': 'remote-fast-path', 'mandatory_cost_usd': 0,
                                  'paid_fallback_used': False, 'status': 'worker_exception',
                                  'error_type': type(exc).__name__}],
                    'raw_outputs': []}
    return [by_index[index] for index in range(len(swarm.ROLES))]


def main(root):
    if os.environ.get('ZERO_SPEND_MODE') != 'HARD':
        raise RuntimeError('ZERO_SPEND_HARD_REQUIRED')
    started = time.monotonic()
    root = Path(root)
    _bind_validated_official_evidence(root)

    evidence = swarm.load_evidence(root)
    if not evidence:
        raise RuntimeError('INCIDENT_EVIDENCE_REQUIRED')
    contract = swarm.current_contract()
    if not contract:
        raise RuntimeError('CURRENT_CANDIDATE_CONTRACT_REQUIRED')
    image = swarm.evidence_image(root)
    probe_evidence = swarm.load_probe_evidence(
        Path(os.environ.get('CURRENT_PROBE_EVIDENCE', 'current-probe-evidence')))
    if not probe_evidence:
        raise RuntimeError('CURRENT_DIAGNOSTIC_PROBE_EVIDENCE_REQUIRED')

    robots = _run_remote_robots(evidence, contract, image, probe_evidence)
    valid = [r for r in robots if swarm.valid_verdict(r.get('verdict'), r['role'])]
    vetoes = [r['role'] for r in valid
              if r['verdict']['veto'] or r['verdict']['verdict'] != 'PASS_FIX']
    classes = Counter(r['verdict']['root_cause_class'] for r in valid)
    required = {name for name, _ in swarm.ROLES}
    covered = {r['role'] for r in valid}
    accepted = (len(valid) == 10 and covered == required and not vetoes
                and classes.get('UNKNOWN', 0) == 0)
    out = {
        'status': 'SWARM_ACCEPTED' if accepted else 'SWARM_BLOCKED',
        'candidate_sha': os.environ.get('GITHUB_SHA'),
        'historical_evidence': True,
        'robots_total': 10,
        'valid_reviews': len(valid),
        'covered_roles': sorted(covered),
        'root_cause_votes': dict(classes),
        'vetoes': vetoes,
        'reviews': robots,
        'diagnostic_probe': json.loads(probe_evidence),
        'execution': {
            'mode': 'remote_fast_path',
            'remote_workers': _bounded_workers(),
            'elapsed_seconds': round(time.monotonic() - started, 3),
            'full_failover_required': not accepted,
        },
        'zero_spend_mode': 'HARD',
        'paid_fallback_used': False,
        'heavy_local': 0,
    }
    Path('osworld-061-specialist-swarm.json').write_text(
        json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps({k: out[k] for k in (
        'status', 'candidate_sha', 'robots_total', 'valid_reviews',
        'root_cause_votes', 'vetoes', 'execution')}))
    if not accepted:
        raise RuntimeError('SPECIALIST_REMOTE_FAST_PATH_BLOCKED')


if __name__ == '__main__':
    main(sys.argv[1])
