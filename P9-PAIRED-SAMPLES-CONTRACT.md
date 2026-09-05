# P9 paired-samples contract

The P9 release gate accepts only independently produced, same-task paired evidence.

Input file: `p9-paired-samples.json`
Schema: `arbm-p9-paired-samples-v1`

Required top-level fields:
- `independentAuditor: true`
- `sameTaskContract: true`
- `samples: []`

Each sample must contain `dimension`, unique `taskId`, `arbm`, and `codex` scores in [0,1].
Every required dimension must contain at least 30 paired tasks. Duplicate task IDs, missing dimensions, invalid scores, or non-independent input fail closed.

The auditor computes the mean ARBM/Codex score, paired 95% lower confidence bound, sample count, and SHA-256 of the raw dimension samples. Only the generated audited evidence is accepted by the release gate.
