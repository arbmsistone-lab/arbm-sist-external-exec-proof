# ARBM SIST — Top 3 Architecture Constitution V2

Date: 2026-09-09
Decision status: APPROVED ARCHITECTURE / IMPLEMENTATION AND EXTERNAL PROOF GATED
Target: 10,000+ tenants, Top-3-class quality, near-zero mandatory ARBM variable cost

## Final review board
Reviewer A — Principal Distributed Systems / SaaS Architecture
Reviewer B — Frontier AI Systems / Evals / Agent Reliability
Reviewer C — SRE / Security / FinOps / Multi-tenant Operations

The three reviews approve the same core direction with the mandatory hardening below.

## Final product constitution
ARBM Distributed Cell Fabric + Universal Intelligence Fabric.

Global Edge -> Tenant Router -> Assigned Cell Data Plane -> Queue -> Universal Executor -> Intelligence Router -> Verification Gate -> Result.

Control Plane manages identity, tenant placement, policy, budgets, provider registry, cell lifecycle and global observability. Established cell data planes must continue serving when control-plane operations are degraded.

## Mandatory job envelope
Every request/job carries: tenant_id, cell_id, trace_id, idempotency_key, workload_class, priority, payer_id, budget_id, data_classification, residency_policy, capability_policy and model_policy.

## Reviewer A — distributed systems amendments
1. Cells are bounded fixed-size failure domains, not infinitely autoscaled clusters.
2. Each cell has a measured safe operating envelope and reserved failover headroom.
3. Admission control/load shedding is mandatory before overload.
4. Cell router remains minimal, horizontally scalable and free of business logic.
5. Tenant-to-cell mappings are cacheable; established traffic should not require a heavy control-plane roundtrip.
6. Cell drain, migration, rebalancing and rollback are first-class protocols.
7. At least two independent failure domains are required before a high-availability production claim.
8. Multi-region is required before a global Top-3 availability claim, but not as a day-one dependency.

## Reviewer B — frontier intelligence amendments
1. Provider/model ranking is empirical, never static or fame-based.
2. Every workload class has an eval suite with quality, latency, cost and tool-success metrics.
3. Routing uses champion/challenger, shadow evaluation and rollback.
4. A model/provider is promoted only after statistically sufficient evidence on relevant workloads.
5. Critical outputs require independent critic/provider diversity when practical.
6. Deterministic/tool verification outranks LLM self-confidence whenever available.
7. Free models are eligible only while they meet the same minimum quality floor for the workload.
8. Frontier escalation is allowed only through BYOK, BYOC, prepaid balance or an explicit ARBM budget.

## Reviewer C — SRE, security and FinOps amendments
1. Shared PostgreSQL tables require RLS plus FORCE ROW LEVEL SECURITY where appropriate; application service roles must not own protected tables or hold BYPASSRLS.
2. Cross-tenant negative tests are mandatory in CI and production canaries.
3. Queue consumers are idempotent; at-least-once delivery must not duplicate side effects.
4. Per-tenant quotas cover requests, concurrency, CPU, memory, storage, tokens, queue age and external spend.
5. No paid call can execute without payer_id + budget_id + hard_limit + remaining balance/authorization.
6. Free capacity is opportunistic and never counted toward a contractual availability SLO.
7. Secrets stay out of repositories and are scoped, rotated and auditable.
8. OpenTelemetry is the telemetry contract; provider-specific observability is optional, not canonical.
9. Backup restore tests, cell evacuation drills and provider-failure drills are mandatory before Top-3 availability claims.
10. Single-provider or single-region operation may be used only as an early-stage mode, never marketed as globally resilient.

## Final 10-pass audit
1. Scale to 10,000+ tenants: PASS architecturally with cells, queues, admission control and migration.
2. Near-zero mandatory ARBM variable cost: PASS architecturally with free-first + BYOK/BYOC + prepaid + hard spend gates.
3. Frontier-quality intelligence: PASS architecturally with eval-driven routing, escalation, critics and deterministic verification.
4. Latency: PASS architecturally with fast-path models, regional cells and bounded queues; requires measured SLO evidence.
5. Availability: PASS architecturally with independent cells/providers; production Top-3 claim requires multi-failure-domain evidence.
6. Tenant isolation: PASS design, IMPLEMENTATION-GATED until FORCE RLS/roles/network controls and leakage tests are proven.
7. Noisy-neighbor resistance: PASS design with per-tenant quotas, workload classes, admission control and silo escape hatch.
8. Vendor independence: PASS design through adapters, neutral telemetry and provider-agnostic product semantics.
9. Operability/cost safety: PASS design with staged complexity, idempotency, FinOps hard gates, restore/failure drills and no silent overage.
10. Top-3 worldwide claim: BLOCKED until external benchmarks, load tests, security tests, chaos/failure injection, SWEfficiency/OSWorld and real production SLOs pass.

## Final economic order
FREE VERIFIED CAPACITY -> TENANT BYOK -> TENANT BYOC -> ARBM SHARED FIXED-COST ANCHOR -> PREPAID BOOST -> EXPLICIT ARBM BUDGET.
No postpaid tenant-variable subsidy. No silent paid fallback.

## Final implementation order
P0: tenant/spend kernel + immutable job envelope + adapter contracts + idempotency.
P1: queue-backed executor + metering + eval harness + free/BYOK routing.
P2: cell router + two independent cells + FORCE-RLS tenant isolation + cell migration/drain.
P3: champion/challenger intelligence router + critic/deterministic verification + load/security/failure testing.
P4: fixed-cost shared compute anchor and free/OSS burst providers; Kubernetes/KEDA only when measured thresholds justify it.
P5: multi-region, BYOC/dedicated cells and independent external Top-3 certification campaign.

## Closure decision
APPROVE this architecture as the ARBM SIST constitutional target. Do not reopen the provider-level architectural decision unless a future measured finding invalidates a constitutional assumption. Providers, models and runtimes may change continuously; the product contracts above remain stable.

This approval is an architecture decision, not a claim that implementation or Top-3 certification is already complete.
