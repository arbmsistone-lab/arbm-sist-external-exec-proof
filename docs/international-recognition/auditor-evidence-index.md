# Auditor Evidence Index

Purpose: provide a concise, reproducible entry point for an independent auditor without treating configuration or self-authored documentation as proof.

Technical anchor: `73772dbe40650d2e4561693db00ade48e3134ac1`

## Evidence handling principles

1. A repository document is an index, not proof by itself.
2. Primary technical evidence is the immutable commit/run/artifact/hash chain.
3. Historical evidence remains bound to the release/SHA under which it was produced.
4. Later documentation must not retroactively change an earlier evaluator result.
5. External certification, attestation, appraisal and ranking remain pending until issued by the responsible independent body.

## Primary OSWorld technical evidence

### Current-head supreme/world audit

- Run ID: `35205586391`
- Candidate SHA: `73772dbe40650d2e4561693db00ade48e3134ac1`
- Workflow conclusion: SUCCESS
- Approved focal evidence binding: PASS
- Diagnostic execution parity: PASS
- Champion/core checks: 26/26
- Deterministic adversarial construction lenses: 500/500
- Final master lenses: 100/100
- Specialist swarm: `SWARM_ACCEPTED`
- Valid specialist reviews: 10/10
- Specialist vetoes: 0
- Final 20x3D checks: 60/60
- World-audit artifact ID: `10490275855`
- World-audit artifact SHA256: `583c748f2d8aef3695f9703dda63304e0c2b0c9a08b32cef18aecc1a7dc9ac93`

### Current-head official focal evidence

- Run ID: `35208530488`
- Candidate SHA: `73772dbe40650d2e4561693db00ade48e3134ac1`
- Preflight: SUCCESS
- Shard B / task 061: SUCCESS
- Aggregate: SUCCESS
- Official status: `FOCAL_061_PASS`
- Official task count in focal: 1
- Binary successes: 1
- Task 061 score: 1.0
- Evaluator: `OSWorld V2 official`
- Judge input/response integrity: PASS
- Spend mode: HARD
- Heavy local: 0
- Evidence manifest SHA256: `23abb395b8edd753b592ecb282f992571427f9f745bb26e7710c9734b091da7b`
- Shard artifact ID: `10491173565`
- Shard artifact SHA256: `ec0713a01c460edc4cd59c619714326b65a629a19cad046ec2e75e651619086d`
- Summary artifact ID: `10491761181`
- Summary artifact SHA256: `18a66378fb5c5195b94de7e6700ebfb01153e4cbce5527986a7d4113cad542ba`

### Approved historical focal bound into world audit

- Run ID: `35148173044`
- SHA: `71146c8239467af9efbe11572f40a433bd4009d6`
- Approved evidence manifest SHA256: `e67e3fa9680bc8fa46a76e16251ed2fbfc07b04518bb6c6e6c090256e3e535e9`
- Purpose: immutable evidence consumed and verified by the later world-audit chain.

## Technical control evidence categories

### Provenance and chain of custody

Evidence examples:
- candidate SHA written into task evidence;
- SHA256 evidence manifests;
- approved-focal SHA verification before audit;
- fail-closed equality checks;
- stale evidence purge before evidence download;
- artifact digests emitted by GitHub Actions.

### Evaluator integrity

Evidence examples:
- official release/task/evaluator pins;
- evaluator integrity snapshot before execution;
- post-execution integrity verification;
- official raw evaluator evidence preserved;
- aggregate gate audits official scores, exact task set, provenance and hashes.

### Execution environment

Evidence examples:
- GitHub-hosted runner requirement;
- KVM device verification in remote execution;
- heavy local = 0 in official aggregate;
- zero-spend HARD checks;
- provider admission and isolated local/free fallback logic.

### Reliability / regression / incident learning

Evidence examples:
- RCA files under `reports/`;
- historical replay/checksum records;
- incident-specific specialist/world audit;
- 20x3D final audit;
- deterministic adversarial lenses;
- D19 correction preserved by newer successful audit.

## Organizational evidence still required

An auditor should treat the following as OPEN until genuine organizational records exist and are reviewed:

- approved certification scope and organizational boundaries;
- management-approved quality/security/AI/privacy/service policies;
- asset and information inventories;
- unified risk register and treatment decisions;
- formal control owners and responsibilities;
- supplier inventory and supplier reviews;
- privacy data-flow/processing inventory;
- business continuity plan, RTO/RPO and exercise records;
- formal incident-management process and retained operating records;
- access-review records;
- internal-audit records;
- management-review records;
- corrective-action/nonconformity records where applicable;
- evidence-retention schedule;
- service catalogue and SLA/SLO ownership where applicable.

Historical organizational records must never be fabricated to accelerate certification. Where operating-period evidence is required, the period begins when the actual control is implemented and recorded.

## External-only closures

The following cannot be closed internally:

- OSWorld V2.1 Verified leaderboard status;
- any worldwide Top-3 placement;
- ISO accredited certificate issuance;
- SOC 2 report issuance;
- CMMI appraisal result;
- independent ISO/IEC 25010 product-quality assessment or market benchmark claim.

## Auditor starting sequence

1. Verify the anchor commit exists and is immutable in Git history.
2. Verify the named workflow runs and candidate SHA bindings.
3. Verify artifact IDs/digests and evidence manifests.
4. Review official evaluator/task integrity evidence.
5. Review RCA and regression evidence.
6. Review current organizational scope and control documentation.
7. Sample operating evidence; do not infer implementation from policy text alone.
8. Record gaps and distinguish technical control gaps from missing operating-period evidence.

## Status

`AUDITOR_ENTRY_PACKAGE = READY_FOR_READ_ONLY_REVIEW`

`EXTERNAL_ATTESTATIONS = NOT_YET_ISSUED`
