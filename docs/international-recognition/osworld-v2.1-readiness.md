# OSWorld V2.1 Verified Readiness

Date: 2026-09-17
Technical anchor SHA: `73772dbe40650d2e4561693db00ade48e3134ac1`

## Upstream release pin

Official tag: `osworld-v2.1`
Tag commit: `3d778a3c9a34a079316f70df023b166700445792`
Release status: active / recommended
Task count: 108

Release manifest pins:
- OSWorld code base commit: `325ab352e2ff7410854bf8e3324c391bc60e7526`
- Website repository: `Task-Web/OSWorld-web`
- Website commit: `60c89fe6a8ed934668619d8d26132848239eb8ee`
- Task dataset commit: `0a1aadad95aa79b00b3783e717d865089ab06e26`
- Gated assets commit: `384b3834faba5700a7b589e6cc181490c9808949`
- Public assets commit: `3a140a3df8f351b22bb5b9526846f078e738777f`
- Task hash manifest SHA256: `c54d428329be5ca72742a6becd49ee83cf739df5dea429bba182e1f3f21badfb`
- Docker runtime digest: `sha256:0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9`
- Docker VM archive SHA256: `14b08aa7ba6c023ecb91d46de8df5de32af4d1d6bd75ea925519caf9677fc8b3`
- Docker VM artifact revision: `6e16459a2feb5a8f1ed65babcfe7a2a6205d049d`
- AWS us-east-1 1920x1080 AMI: `ami-01017272139e01feb`

## Why the current certified workflow must not be relabeled

The current ARBM official focal workflow is pinned to the earlier `osworld-v2-2026.08.08` release and contains release-specific assumptions. It must remain historically reproducible.

The current workflow includes, among other things:
- clone/tag `v2026.08.08`;
- task/assets revision `v2026.08.08`;
- prior VM archive revision and SHA256;
- hosted website suffix `site.hku.icu`;
- release-specific task manifest SHA256.

OSWorld V2.1 changes these release inputs and explicitly requires the `osworld-v2.1` website source to be self-hosted with its host suffix configured. Therefore V2.1 needs a new, separately pinned evaluation lane rather than mutation of the already-certified 2026.08.08 evidence.

## Public Verified requirements

For a result to be shown in the Verified leaderboard, the public evaluation guidance requires maintainer-side verification: schedule with the OSWorld team so they can run the submitted agent implementation and report the result. The implementation must be available under the OSWorld framework with a report explaining the system; model/API credentials may be kept non-public. A trusted-institution alternative may use monitoring data and trajectories.

Current state:
- Maintainer contact request: SENT on 2026-09-17.
- Full V2.1 result: NOT RUN.
- Verified leaderboard result: NOT YET ISSUED.
- Worldwide ranking claim: BLOCKED.

## V2.1 migration gates

No full benchmark execution should begin until all preparation gates below pass.

### Gate V21-1 - Immutable upstream pins

- [x] Official tag identified.
- [x] Tag commit recorded.
- [x] Release manifest located.
- [x] Task count and task hash manifest recorded.
- [x] Website/task/assets/provider-image pins recorded.
- [ ] Mirror all selected upstream pins into a machine-readable ARBM manifest.
- [ ] Add a fail-closed verifier that aborts if any upstream pin differs.

### Gate V21-2 - Website self-hosting readiness

- [x] Self-hosting requirement identified.
- [x] Website source commit recorded.
- [ ] Define ZERO_SPEND-compatible remote hosting route.
- [ ] Prove the deployed host suffix resolves to the pinned website source.
- [ ] Seal source commit, deployment evidence and host-suffix mapping.
- [ ] Confirm no mutation of official task semantics.

### Gate V21-3 - Agent interface migration

- [ ] Compare ARBM agent entrypoint against current V2.1 runner interface.
- [ ] Port only interface/integration code required for V2.1 compatibility.
- [ ] Preserve action-space and observation semantics required by the official benchmark.
- [ ] Preserve provider/evaluator isolation.
- [ ] Preserve fail-closed provenance and zero-spend policy.

### Gate V21-4 - Official evaluator integrity

- [ ] Snapshot evaluator/task source before execution.
- [ ] Verify official task files against the V2.1 hash manifest.
- [ ] Verify assets and provider-image pins.
- [ ] Prove evaluator source remains unmodified after execution.
- [ ] Preserve raw evaluator output and trajectories.

### Gate V21-5 - Non-scoring smoke readiness

- [ ] Run only maintainer-compatible smoke/preflight checks after explicit execution authorization.
- [ ] Do not interpret smoke results as benchmark score.
- [ ] Do not duplicate historical focal evidence merely to create a new artifact.

### Gate V21-6 - Full benchmark authorization

- [ ] Maintainer verification route confirmed.
- [ ] Agent disclosure/report package accepted for evaluation.
- [ ] Execution infrastructure approved under preserved spend policy or separately authorized external terms.
- [ ] Full 108-task run explicitly authorized.

### Gate V21-7 - Verified publication

- [ ] Full comparable score produced.
- [ ] Result reported/accepted by OSWorld maintainers.
- [ ] Verified leaderboard publication captured with date/version.
- [ ] Any ranking language derived only from that comparable published snapshot.

## Known upstream release limitations to preserve in risk analysis

The official V2.1 release manifest itself records limitations, including no full 108-task agent evaluation by the release verification process, no established AWS/Docker guest equivalence, no hosted website deployment verification, and an observed unmodified Task029 setup timeout. These are upstream release limitations and must not be concealed or misrepresented as ARBM-specific failures.

## Verdict

`OSWORLD_V2_1_MIGRATION_READINESS = DOCUMENTED`

`OSWORLD_V2_1_FULL_RUN = NOT_STARTED`

`OSWORLD_VERIFIED_STATUS = PENDING_MAINTAINER_PROCESS`

`TOP3_WORLDWIDE = BLOCKED_PENDING_COMPARABLE_VERIFIED_RESULT`
