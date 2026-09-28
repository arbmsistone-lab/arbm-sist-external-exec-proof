# ARBM SIST Global Route Fabric — Candidate v1

## Principle
ARBM SIST MUST NOT depend on any named provider, runner, host, operating system, shell, browser, relay, model vendor, state store, DNS vendor, or control interface.

"All routes" means an open capability fabric able to discover, qualify and add any legitimate compatible route without changing mission semantics. It does NOT mean bypassing provider authorization, platform controls, commercial terms, geographic/legal restrictions, or pretending unavailable routes exist.

## Provider-neutral contract
Missions request capabilities, never vendors:
- compute.execute
- browser.control
- api.call
- source.read/write
- artifact.store/read
- state.checkpoint/recover
- verify.independent
- message.publish
- application.control

Every adapter implements the same lifecycle:
DISCOVER -> AUTHENTICATE -> QUALIFY -> LEASE -> EXECUTE -> OBSERVE -> CHECKPOINT -> VERIFY -> RELEASE.

## Route classes
Native Runtime; customer device runtime; cloud runner; CI runner; container runtime; VM/bare metal; serverless/edge; browser automation node; official API connector; remote desktop node; state/evidence backend.

## Admission
A route is usable only with legitimate authority, compatible capability, health PASS, fresh witness, known direct/transitive dependencies, cost-policy compliance, security policy compliance and takeover witness where required.

## Dynamic registry
No hard-coded provider allowlist is constitutional. New adapters may be added dynamically. Provider names are implementation inventory only.

## Resilience
Routing optimizes for failure-domain diversity and spare capacity, not provider count. A shared identity provider, network, DNS, repository, artifact store, credential vault, orchestrator or physical host can collapse nominally different routes into one effective domain.

## Degradation
Loss of a provider removes it from eligible quorum; it must not block the system while sufficient qualified routes remain. Rejoin requires requalification. If safe quorum/capability is impossible, fail closed for that capability rather than forge success.

## Commercial policy
Free and paid routes are policy dimensions, not architecture dimensions. A customer-paid Runtime/connector may be enabled by entitlement. A paid external provider may be selected only when the active customer/organization policy explicitly permits it.
