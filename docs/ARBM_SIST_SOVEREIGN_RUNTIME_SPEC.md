# ARBM SIST Sovereign Runtime — Formal Architecture Candidate v1

Status: CANDIDATE — NOT CONSTITUTIONAL UNTIL ADVERSARIAL EVIDENCE PASSES.

## Objective
Make mission continuity independent of any single executor, provider, host, relay, browser, credential gateway, state store, verifier, network path, or control-plane instance.

## Safety properties
S1 Mission truth survives executor loss.
S2 No route counts unless independently qualified by fresh witness evidence.
S3 External effects are logically exactly-once through idempotency, reconciliation, fencing, or compensation.
S4 Executor never self-certifies terminal success.
S5 Secrets are capability-scoped; agents receive authority handles, not raw secrets where avoidable.
S6 Shared transitive dependencies collapse apparently distinct routes into one failure domain.
S7 Missing/stale evidence is NOT_PROVEN.
S8 Paid fallback is forbidden unless an explicit versioned policy authorizes it.

## Liveness properties
L1 A mission continues after loss of any one qualified failure domain.
L2 Critical capabilities target two-failure-domain survivability.
L3 Takeover resumes from durable checkpoint under a new fencing token.
L4 Recovered stale executors cannot commit after lease/fence loss.
L5 Route reintegration requires a new qualification witness.

## Logical planes
Intent/Contract Compiler -> Durable Mission Kernel -> Planner/Critic/Strategist -> Capability Router -> Authorization/Effect Plane -> Execution Mesh -> Observation -> Independent Verification -> Evidence Ledger -> Release Authority.

## Native Runtime
ARBM SIST Runtime is a provider-independent executor implementing capability contracts for browser, API, applications, files, OS automation and isolated compute. It is preferred where appropriate but never architecturally privileged: losing every native Runtime must not corrupt mission truth.

## Mission record
mission_id, intent_hash, plan_version, authorization_ref, current_step, checkpoint_hash, lease_owner, lease_expiry, fencing_token, idempotency_key, prepared_effects, observed_effects, evidence_refs, verifier_result, commit_state.

## Effect protocol
PREPARE -> AUTHORIZE -> EXECUTE -> OBSERVE -> RECONCILE -> VERIFY -> COMMIT.
On uncertainty, RECONCILE before RETRY. Irreversible effects require stronger authorization and postcondition evidence.

## Route qualification
States: QUALIFIED, DEGRADED, QUARANTINED, UNAVAILABLE, STALE_EVIDENCE.
A route counts toward resilience only when its witness is fresh, authority is usable, health is acceptable, transitive dependencies are known, and takeover has been exercised within policy TTL.

## Resilience budget
Critical capability certification is based on tolerated independent failure domains, not provider count. Target: tolerate two simultaneous independent failure domains for mission-critical execution paths. Route diversity that shares a critical transitive dependency does not increase the budget.

## Promotion rule
This specification becomes constitutional only after threat-model, failure-domain, chaos, security, recovery, exactly-once, independent-verifier and regression gates pass on the exact candidate.
