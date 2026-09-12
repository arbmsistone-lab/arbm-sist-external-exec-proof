# Run 34698877150: structural failure and candidate correction

Official result: tasks001/002 rc124 with no numeric evaluator result; task003 rc0, score0.0. NOT APPROVED. No positive smoke or full108 score is claimed.

The dominant structural class was840 SHIM_ERROR events caused by INPUT_PAYLOAD_GATE. Twenty raw observations exceeded32MB. HTTP500 triggered identical retries until the50-minute timeout. Ingress now uses incremental JSON parsing and retains system instructions plus the latest observation. Independent256MB wire and28M-character message bounds remain. Permanent errors explicitly terminate with FAIL so the unchanged evaluator can run; aggregate rejects infrastructure failures.

Regression:34,002,723-byte parser and loopback HTTP tests pass, with approximately7.66MB peak parser allocations and0.31s local parsing. Forty Python tests and endpoint contract/failover/payload tests passed. These measurements are local, not production latency percentiles.

The40-minute agent deadline leaves time before the external50-minute timeout for evaluation. A30-second heartbeat reports real task, step, provider, request state, elapsed time and last verified milestone. The trajectory returns to8 observations; bounded plan/action memory remains separate. Semantic predicates are checked against the next foreground observation; screen changes, background labels and duplicate milestones cannot alone prove new progress. The official evaluator remains authoritative.

A foreground-filter defect removed real archive filename titles. Desktop suppression is now limited to the observed Desktop icon area; the foreground archive section is retained. Recorded regression cases are fetched from existing run artifacts at test time. No screenshots or raw observation fixtures are included in this commit.

Three approaches: (1) existing multimodal Qwen/Mistral agent, limited by observed quota exhaustion and small-model planning errors; (2) implemented text-only GPT-OSS120B/20B accessibility planner with local compiler and independent semantic checks, requiring remote FREE header proof; (3) separate vision grounder per planner action, not promoted because it adds requests and another scarce free inference dependency without demonstrated improvement. The new text route explicitly lacks screenshot access and has no provider built-in tools.

Primary sources: https://console.groq.com/docs/model/openai/gpt-oss-120b ; https://console.groq.com/docs/rate-limits ; https://osworld-v2.xlang.ai/ . Full108 and Top3 remain NOT BENCHMARKED until positive smoke and representative subsets pass.

Candidate: arbm-osworld-elite-pro-v31q-20260912, endpoint version17, bundle ef0183f209567722b83f984124ffbf9ffc64ed4b29d31cef77d4b2da5241d8e5. Remote source retrieved and compared equal after line-ending normalization. Manifest canonical hash is cross-platform. Only ARBM SIST isolated clone and dedicated endpoint changed; no paid fallback or evaluator modifications.

## Gate34707731309 follow-up

Local contracts/replay passed remotely. GPT-OSS120B and20B returned HTTP200 with matching FREE plan limits. The fourth diagnostic consumed both text models in one token window; the next source-reading case fell back to Ministral8B and tried Calendar before reading the spreadsheet attachment. The PREMATURE_CALENDAR regression blocked the smoke. No long VM run started.

Candidate v31r/version18 removes the two unqualified small fallback models, waits for an eligible text token window during diagnostic replay, and accepts durable source facts only when the exact quote appears in the current foreground observation. Model future-tense completion claims never enter memory.43 Python tests plus endpoint failure-injection tests pass. Current bundle336f37567f34d47be14a52741d0a9ef10afa92b48c6c15ed0c2a62226958b8dd; remote source comparison passed. Benchmark remains NOT APPROVED pending remote gates and official positive smoke.

## Gate34708001563: planning failure persisted

The stronger text-only20B model also selected the premature Calendar shortcut. The regression rejected it before any VM run. Quota telemetry separately shows Qwen models near200K daily tokens; capacity and planning are distinct failure classes. Removing small fallback models alone did not resolve ordering.

Candidate v31s/version19 introduces a separate transition review call for proposed app changes, replans and finish. It checks the proposed action against task prerequisites and verified facts, returning either the approved action or a corrected action. Missing reviewer capacity or review verdict blocks execution with503, never bypasses the review. The local next-observation verifier remains independent of both inference calls. A deterministic integration test reproduces the bad Calendar proposal, verifies source-reading correction, and injects reviewer429 to prove fail-closed behavior.43 Python tests and four endpoint test groups pass. Bundle773ea28652bd69ce1b43e7e56774a4c877460231b8a958976991670aebf0ce63 was retrieved and compared with local source before push. These tests do not claim functional benchmark success.
