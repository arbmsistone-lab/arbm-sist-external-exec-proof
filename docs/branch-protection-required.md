# Required protection for official ARBM SIST operational branch

Target branch: `chatgpt/arbm-agent-elite-v2-20260914`

This document records the minimum administrative protection policy required before the branch can be treated as governance-closed:

- Require a pull request before merging.
- Block force pushes.
- Block branch deletion.
- Require conversation resolution when supported.
- Require existing repository status checks only after their exact names are verified from successful runs; do not invent check names.
- Do not weaken any repository-level ruleset or existing protection.
- Do not change the repository default branch or visibility as part of this protection change.

Administrative closure is fail-closed: do not mark the branch protected until GitHub itself re-reports the branch or applicable ruleset as enforcing the requested policy.

Current tool constraint: the managed GitHub connection available in this chat does not expose administrative branch-protection writes. The first browser automation attempt was rejected before session creation because strict-agent mode is not enabled for the account. This is a tooling/permission blocker, not evidence that protection was applied.
