# ARBM SIST Technical Constitution

Status: CANONICAL ARCHITECTURAL POLICY
Version: 1.0
Scope: ARBM SIST agentic platform and all critical execution paths

## Mission

ARBM SIST is engineered toward world-class agentic capability under a ZERO_SPEND constraint. Quality claims require reproducible evidence. No component, model, provider, executor, tool, or agent may self-declare success.

## Non-negotiable invariants

1. NO SPOF
   - No critical capability may have an unmitigated single point of failure.
   - Shared credentials, gateways, state stores, hosts, control planes, or network paths count as dependencies and must be included in dependency analysis.

2. MULTI-PROVIDER BY CAPABILITY
   - Critical capabilities must be expressed as provider-independent contracts.
   - Providers are replaceable implementations, not architectural authorities.
   - Failover must preserve mission state and must be tested, not merely configured.
   - Provider health, permissions, latency, reliability, and availability are inputs to routing.

3. ZERO_SPEND
   - Prefer legitimate zero-cost routes that satisfy the same protected quality gates.
   - The system must not silently incur paid usage.
   - If no zero-cost route can satisfy a protected requirement, remain fail-closed and record the gap unless explicit authorization changes the constraint.
   - ZERO_SPEND never authorizes lowering a protected quality gate.

4. CONTINUOUS EVOLUTION
   - Models, tools, skills, prompts, policies, providers, evaluators, and strategies may evolve continuously.
   - New candidates enter through evaluation and staged promotion, never by silently replacing the proven baseline.

5. ZERO UNDETECTED REGRESSION ON PROTECTED INVARIANTS
   - Every promoted change must be compared with the last proven baseline.
   - Promotion path: baseline -> contract tests -> regression suite -> benchmark -> adversarial evaluation -> shadow/canary where applicable -> evidence -> promotion.
   - Any known regression in a protected invariant blocks promotion.
   - Unknown behavior must never be represented as proven behavior.

6. EVIDENCE BEFORE GREEN
   - ACTION != SUCCESS.
   - HTTP 2xx, exit code 0, tool success, model assertion, UI click, or save command alone is not proof of goal completion.
   - Required lifecycle: INTENT -> PLAN -> AUTHORIZE -> ACT -> OBSERVE -> VERIFY -> COMPARE -> COMMIT.
   - GREEN requires reproducible postcondition evidence tied to the exact version and execution.

7. INDEPENDENT VERIFICATION
   - Executors cannot be sole judges of their own work.
   - Prefer deterministic verification for deterministic claims.
   - Critical semantic claims require an independent verification path where practical.
   - Correlated verifier/executor failure must be considered explicitly.

8. DURABLE, PORTABLE MISSION STATE
   - Checkpoints, idempotency keys, leases/fencing, artifacts, event history, and evidence must support safe resume and takeover.
   - Loss of an executor must not imply loss of mission truth.
   - Repeated actions with external effects require idempotency or explicit compensation.

9. TRANSACTIONAL EFFECTS
   - External effects follow PREPARE -> EXECUTE -> OBSERVE -> VERIFY -> COMMIT, with COMPENSATE/ROLLBACK when supported.
   - Irreversible or high-blast-radius effects require stronger authorization gates.
   - A failed verification must never be converted into success merely because rollback is unavailable.

10. VERSIONED ROLLBACK
    - Code, model selection, prompts, policies, tool contracts, skills, configuration, benchmarks, and release evidence are versioned.
    - Promotions preserve a known-good rollback target whenever the underlying system supports rollback.

11. QUALITY IS MEASURED
    - Quality targets are established through reproducible benchmarks and real task evidence.
    - Parity or superiority to external reference systems may be claimed only for measured task populations and versions.
    - Unmeasured capability remains NOT_PROVEN.

12. FAIL-CLOSED RELEASE AUTHORITY
    - Release states are PASS / RETRY / REPLAN / FAILOVER / ROLLBACK / ESCALATE / NOT_PROVEN.
    - RELEASE/GREEN is permitted only when Definition of Done and required evidence are satisfied for the exact candidate.
    - Missing, stale, mismatched, or unverifiable evidence blocks GREEN.

## North-star control architecture

Intent/Contract Compiler
  -> Durable Distributed Control Plane
  -> Planner/Critic/Strategist
  -> Specialized Agent and Workflow Fabric
  -> Model Fabric
  -> Tool/Skill/Connection Fabric
  -> Authorization and Effect Transaction Plane
  -> Multi-Provider Execution Mesh
  -> Observation/World-State Plane
  -> Independent Verification
  -> Evidence/Provenance Ledger
  -> Decision and Release Authority

Cross-cutting planes:
- Identity / Zero Trust
- Secrets and scoped authorization
- Mission State and Event Log
- Memory and Context
- Artifact Store
- Observability and Forensics
- Evaluation and Regression
- Recovery and Disaster Recovery
- Resource and ZERO_SPEND Governance

## Promotion law

No update is canonical merely because it is newer.

A candidate may replace a proven baseline only when:
- protected contracts pass;
- protected regression corpus does not regress;
- required adversarial evaluations pass;
- evidence belongs to the exact candidate;
- rollback/recovery requirements are satisfied;
- ZERO_SPEND policy is satisfied unless explicitly superseded;
- no unresolved critical dependency violates NO SPOF or provider-independence requirements.

Otherwise the proven baseline remains canonical.

## Provider-independence law

For every critical capability C:
- define C independently of provider implementation;
- enumerate direct and transitive dependencies;
- identify shared failure domains;
- maintain qualified alternative routes where feasible under ZERO_SPEND;
- periodically exercise takeover/failover;
- preserve state/evidence across provider transition;
- never call a route independent when it shares an unmitigated critical dependency with the primary route.

## Evidence law

Every terminal claim must answer:
- What exact goal was requested?
- What exact version executed?
- What actions occurred?
- What world state was observed afterward?
- Which verifier established the postcondition?
- Which artifacts/hashes/logs support it?
- Were protected regressions evaluated?
- Can the result be reproduced or independently inspected?

If any mandatory answer is absent, terminal state is NOT_PROVEN.

## Constitutional shorthand

NO SPOF + MULTI-PROVIDER + ZERO_SPEND + CONTINUOUS EVOLUTION + ZERO UNDETECTED REGRESSION + EVIDENCE BEFORE GREEN.

These requirements are cumulative. One invariant may not be sacrificed to satisfy another without an explicit, versioned policy change and appropriate authorization.
