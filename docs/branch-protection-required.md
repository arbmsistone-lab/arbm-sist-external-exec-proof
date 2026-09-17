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

The current ChatGPT GitHub managed connection does not expose administrative branch-protection writes. Protection must therefore be applied through an authenticated GitHub administrative surface or a connector with repository administration permission, then re-read and verified before the branch is marked protected.
