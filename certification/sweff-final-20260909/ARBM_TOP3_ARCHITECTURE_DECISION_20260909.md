# ARBM SIST — Top 3 Architecture Decision

Date: 2026-09-09
Status: PROPOSED CONSTITUTION / FAIL-CLOSED
Target: 10,000+ tenants with near-zero mandatory ARBM variable cost

## Non-negotiable principles
1. No single-provider dependency.
2. Tenant context is first-class in identity, data, jobs, metering and telemetry.
3. Heavy compute never depends on the customer's local machine.
4. Free-first, but never free-only when quality or availability would regress.
5. Paid inference/compute requires an explicit payer, budget and hard limit.
6. No postpaid ARBM subsidy for tenant-variable AI usage.
7. Shared pool by default; dedicated cell/BYOC for enterprise or noisy-neighbor cases.
8. Every provider can be replaced without changing product semantics.
9. Fail closed on isolation, spend, capacity and evidence gates.
10. Claims of Top 3 require external benchmark evidence, not architecture alone.

## Winning architecture
Global Edge/API -> Tenant Control Plane -> Cell Router -> Cell Queue -> Universal Executor -> Intelligence Router -> Verification Gate -> Result.

Each tenant receives immutable tenant_id. Every job carries tenant_id, cell_id, payer_id, budget_id, priority, data_classification and trace_id.

## Cells
Cells are repeatable bounded failure domains. Each cell contains stateless APIs, queue consumers, cache, workers and a database shard/pool. New tenants are assigned to a healthy cell. Cells scale independently and can be drained/migrated.

The system never promises a fixed 'clients per server' ratio. Scaling uses queue depth, p95/p99 latency, CPU, memory, DB saturation, error rate and per-tenant consumption.

## Data isolation
PostgreSQL Row-Level Security is mandatory on shared tenant tables. Application filtering alone is forbidden. Tenant identity propagates through auth tokens and service context. Enterprise tenants may receive a siloed database/cell while remaining under the same control plane.

## Compute fabric
Priority order: verified free capacity -> ARBM shared anchor -> BYOC/dedicated capacity -> prepaid burst. Free providers are opportunistic capacity, not availability guarantees. Heavy jobs are asynchronous and queue-backed.

Initial operation may use simple container workers. Kubernetes is an upgrade path, not a day-one dependency. When event volume justifies it, Kubernetes + KEDA becomes the standard cell runtime for queue-driven horizontal scaling.

## Intelligence fabric
Model selection is task-based, not brand-based. Router classes: FAST, STANDARD, REASONING, FRONTIER, CRITIC. Route using capability, measured quality, latency, remaining quota, cost and health.

Free models handle tasks only when their measured quality threshold passes. Difficult/critical tasks escalate. Frontier calls use tenant BYOK, customer BYOC, prepaid ARBM Boost, or an explicitly approved ARBM budget. Never silently bill ARBM.

Critical decisions use independent verification: primary model -> critic model/provider -> deterministic/tool verification when available. Provider diversity is required for high-impact validation.

## Economic constitution
Core platform targets near-zero variable cost through shared infrastructure and free allowances. Variable AI/compute consumption must map to one of: free capacity, tenant BYOK, tenant BYOC, prepaid balance, or approved ARBM budget.

No provider may auto-upgrade from free to paid. No overage is allowed without an explicit budget gate. Usage is metered per tenant, provider, model, job class and cell.

## Observability and SRE
OpenTelemetry is the mandatory vendor-neutral telemetry contract for traces, metrics and logs. Every request and job carries trace_id + tenant_id + provider + model + cell.

SLOs are measured by workload class. Required platform gates include p95/p99 latency, availability, queue age, completion rate, provider fallback success, cross-tenant isolation tests and cost-per-successful-job.

## Security
Default-deny tenant data access, least privilege, encrypted secrets, secret rotation, zero secrets in repository, network isolation between cells/workloads and auditable provider calls. High-risk tenant data may opt out of third-party inference or require BYOC.

## 10-pass audit verdict
1. Scale: PASS only with cells + asynchronous queues.
2. Cost: PASS only with free-first/BYOK/BYOC/prepaid and hard spend gates.
3. Intelligence: PASS only with dynamic model routing plus escalation and critics.
4. Latency: PASS with edge control plane, regional cells and fast-route models.
5. Availability: PASS with multiple providers and multiple independent cells.
6. Isolation: PASS only after tenant-aware identity + RLS + network/resource policies.
7. Noisy neighbor: PASS with per-tenant quotas, concurrency limits and cell migration/silo option.
8. Vendor independence: PASS with adapter contracts and OpenTelemetry; no provider semantics in product core.
9. Operations: PASS with staged complexity; no mandatory Kubernetes until measured need.
10. Top-3 claim: BLOCKED until independent benchmark, load, security and failure-injection evidence exists.

## Forbidden architecture
- One server per normal customer.
- One central bare-metal server as the platform.
- One mandatory AI provider/model.
- Free-only routing that degrades quality.
- Paid fallback without payer/budget/hard limit.
- Application-only tenant filtering without DB isolation.
- Kubernetes introduced solely for prestige.
- Claims of capacity based only on customer count.

## Adoption sequence
P0: Tenant kernel + spend kernel + provider/model adapter contracts.
P1: Queue-backed execution + per-tenant metering + free/BYOK routing.
P2: Cell router + second independent cell + failure isolation.
P3: External quality router/critic benchmarks and load tests.
P4: Kubernetes/KEDA only after queue/load thresholds justify it.
P5: Dedicated cells/BYOC and multi-region for enterprise/global scale.

## Final decision
Adopt the ARBM Distributed Cell Fabric + Universal Intelligence Fabric as the product constitution. Providers, models, databases, queue vendors and compute vendors remain replaceable implementation details. This architecture is the recommended route to pursue Top-3-class scale/quality while structurally minimizing mandatory ARBM cost.
