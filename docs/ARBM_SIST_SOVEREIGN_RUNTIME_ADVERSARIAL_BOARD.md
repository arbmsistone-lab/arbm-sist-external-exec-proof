# Sovereign Runtime Adversarial Board

Status: REQUIRED BEFORE CONSTITUTIONAL PROMOTION.

The board does not approve architecture by design intent. It approves only exact-candidate evidence.

## Panels
1. Distributed systems: leases, fencing, partitions, durable state, takeover.
2. Security/zero trust: identity, secret isolation, capability scope, revocation.
3. Reliability/SRE: failure domains, correlated outages, recovery objectives, observability.
4. Agentic systems: planner/executor/verifier separation, tool contracts, semantic failure.
5. Transaction safety: idempotency, reconciliation, compensation, irreversible effects.
6. Adversarial/chaos: simultaneous failures, stale nodes, partial success, poisoned evidence.
7. Product/runtime: installation, upgrades, compatibility, customer isolation and operability.

## Mandatory vetoes
VETO if any critical capability has an unmitigated SPOF; if route independence is only declarative; if a stale executor can commit; if an uncertain external effect can be blindly repeated; if raw secret exposure is unnecessarily delegated to a model; if executor self-certification can produce GREEN; if evidence is stale/mismatched; or if target failure tolerance is not demonstrated.

## Promotion evidence
Formal spec PASS; threat model PASS; dependency graph complete; all mandatory chaos scenarios PASS; exactly-once/reconciliation tests PASS; verifier independence PASS; tenant/security isolation PASS; rollback/recovery PASS; protected regression suite PASS; exact candidate hashes bound to evidence.

Board terminal states: APPROVE_FOR_CONSTITUTION, REPLAN, REJECT, NOT_PROVEN.
