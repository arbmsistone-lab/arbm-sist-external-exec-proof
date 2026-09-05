# P8: numbered source starved by context compaction

Baseline: ae5597ecf687fefb5f543562c0137740a61bd7bd; original worktree clean.
Original branch: p8/new-objective-20260904. Original run: 33939225279.
Job: 101233184090. Artifact: 9961394272.
The original checkout and parallel worktrees were not modified. Candidate is an
independent local clone; rollback is discarding this candidate or reverting its
commits, with V10 and the original baseline untouched.

The full job log and four artifact files were obtained from GitHub. The artifact
file hashes are checked against its SHA256SUMS.txt in local-verification.json.
The generation gate failed before official evaluation. Two successful local
model requests produced an edit of lines 188–189 that did not touch the causal
conversion. The invariant guard correctly rejected the candidate. Evidence says
timedOut=false and NO_PASSING_PUBLIC_CANDIDATE; exitCode 124 is not proof of timeout.

Root cause reproduced without model calls: _compact_public_context reserves the
entire precision preamble before source, then slices by characters. With the
actual 900-character runtime limit, it truncates the numbered source before the
causal expression and even cuts a line number. The previous test used 1100
characters and asserted only that the file header survived.

The new test fails on baseline and checks complete guard, causal and fallback
lines under the runtime budget. The fix reserves source capacity, strips ranking
metadata from prompt excerpts, and emits complete lines. Existing invariant and
public validation gates remain required; no target-repository patch or evaluator
answer was added. Numeric observations are still derived from public source.

Constitution correction: HARD mode rejects overrides at startup and excludes the
paid quality and paid judge endpoints. No billing activation, credential changes,
paid inference, model changes, evaluator changes or quality threshold reductions.
Historical P9 cost policy conflicts remain a disclosed NO-GO pending phase 2.

Research checked 2026-09-05:
- https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- https://github.com/ggml-org/llama.cpp/blob/master/tools/server/bench/README.md
- https://docs.python.org/3/library/stdtypes.html
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- https://docs.github.com/en/billing/concepts/product-billing/github-actions

The bounded prompt fix retains the existing context size/model; inference memory
and latency improvements are not claimed. Standard public runners are free;
storage quotas require separate verification. Local unit checks do not prove P8
official PASS, P9, independent review, product completion or certification.
