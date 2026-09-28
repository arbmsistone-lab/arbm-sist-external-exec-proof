# Sovereign Runtime Threat Model v1

Candidate scope: control plane, runtime nodes, connection/authority fabric, mission state, evidence, verifiers and provider adapters.

| Threat | Failure / attack | Required control | Required witness |
|---|---|---|---|
| T01 | executor disappears mid-mission | durable checkpoint + lease | takeover completes |
| T02 | stale executor returns | fencing token | stale commit rejected |
| T03 | duplicate external effect | idempotency + reconciliation | exactly-once logical outcome |
| T04 | provider outage | independent route | mission continues |
| T05 | two provider domains lost | resilience budget | mission continues where target=2 |
| T06 | shared hidden dependency | dependency graph | routes collapse to one domain |
| T07 | stolen runtime credential | scoped capability + revocation | unauthorized action denied |
| T08 | agent requests excessive scope | policy authorization | least privilege enforced |
| T09 | verifier correlated with executor | independent verification route | disagreement blocks GREEN |
| T10 | evidence tampering | content hashes + provenance | mismatch blocks promotion |
| T11 | state replica stale/corrupt | quorum/version/reconciliation | correct state recovered |
| T12 | network partition | leases + fencing | no split-brain commit |
| T13 | malicious/buggy adapter | sandbox + contract tests | blast radius contained |
| T14 | replayed command | nonce/idempotency/version | replay rejected |
| T15 | paid fallback silently selected | resource policy | fail closed |
| T16 | qualification evidence expires | TTL | route stops counting |
| T17 | runtime software compromised | isolation + scoped authority | lateral movement denied |
| T18 | control plane unavailable | redundant recovery path | mission truth remains recoverable |

Trust boundaries: agent/model; control plane; runtime; authority vault; external provider; state/evidence store; verifier. Crossing a boundary requires authenticated, authorized and auditable capability use.
