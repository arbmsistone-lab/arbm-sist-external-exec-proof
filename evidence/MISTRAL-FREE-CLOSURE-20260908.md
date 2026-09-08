# ARBM SIST — Mistral FREE evidence pack

Date: 2026-09-08 UTC. Repository: arbmsistone-lab/arbm-sist-external-exec-proof.
Branch: codex/free-capacity-v3-20260908.
Project: pvkpkqwdnnpkgvllwqbc. Function: arbm-terminal-agent-v7.
Status: Mistral integration and normal-mesh live proof PASS; 3M tokens/day gate FAIL (insufficient quantitative evidence). ZERO_SPEND_HARD remains mandatory.

## Root cause and correction

The previous diagnostic omitted model_hint, while unproven Mistral required an explicit diagnostic model. Worse, its exit condition treated HTTP 503/not_configured as the expected success. Run 34288158413 was green with no actual Mistral call. Mistral also existed only in forceMistral diagnostic routing.

The probe now makes the real authenticated request with provider_hint=mistral and model_hint=ministral-3b-latest. It only tries ministral-8b-latest then mistral-small-latest after a model-specific unavailable/not-found error. Auth failures, quota exhaustion, transport failures, HTTP 503 and invalid JSON never promote or trigger model rotation. The final verifier requires HTTP 200, ok=true, status=PASS, provider=mistral-free and a parsed Mistral HTTP 200 attempt with explicit mandatory_cost_usd=0 and paid_fallback_used=false. Root cost flags must also match. Generated commands are never executed by the probe.

Mistral participates in normal FREE routing, including deterministic provider diversity and fallback before Cloudflare. All original providers remain present. Missing credentials, missing zero-spend confirmation or an unproven normal route fail closed. Diagnostic hints remain restricted by the existing GitHub OIDC repository/ref/event policy.

429 stops model rotation and immediately cools the whole Mistral provider; Retry-After seconds or HTTP dates are honored. 5xx and transport failures also cool it. The cooldown follows the existing in-memory architecture: it is scoped to a warm Edge isolate, not a distributed/global rate limiter. No cross-isolate guarantee is claimed and no bypass, parallel-key rotation or quota increase was introduced.

Telemetry contains HTTP status, model, actual usage.total_tokens, Retry-After and available rate-limit headers. Missing usage is null, never fabricated zero. Header capture excludes authentication/cookies. Error messages remove any occurrence of the actual Mistral key before returning sanitized diagnostic text.

## Proof chronology

| Evidence | SHA | Run | Result |
|---|---|---|---|
| Old diagnostic | 55c13254230165713efc09edfd5d8f58887493b5 | 34288158413 | HTTP 503, not_configured; NOT live proof |
| First actual Mistral proof | 38c87de0a538a419b01c2fc2165b0e4e274f87cc | 34290628304 | HTTP 200, PASS, ministral-3b-latest, 146 tokens |
| Integration tests and diagnostic | abe1bc07f0dd2d83d3b6ce411edc20891b7131bf | 34291048991 | Tests PASS and real diagnostic HTTP 200 |
| First post-deploy normal mesh | abe1bc07f0dd2d83d3b6ce411edc20891b7131bf | 34291140698 | Lightning then Mistral, HTTP 200 without hints |
| Final strict diagnostic | f27783ff8e9be245bcdee3a6383faf4e8b7ea3d8 | 34291365140 | HTTP 200, all explicit cost and parsing gates PASS |
| Final strict normal mesh | f27783ff8e9be245bcdee3a6383faf4e8b7ea3d8 | 34291383489 | HTTP 200, all explicit gates PASS without provider/model hints |

Each run is available at https://github.com/arbmsistone-lab/arbm-sist-external-exec-proof/actions/runs/RUN_ID (replace RUN_ID with the table value). Full logs were downloaded and inspected locally; sanitized response records and log hashes are committed in mistral-free-provider-proofs-20260908.json.

ARBM_MISTRAL_LIVE_PROVEN=1 was set only AFTER the first actual HTTP 200 in run 34290628304. Existing MISTRAL_API_KEY and ARBM_MISTRAL_ZERO_SPEND_CONFIRMED were reused without reading/exporting or replacing their values. No Pay-As-You-Go, paid provider, account upgrade or quota increase was enabled. Cost flags describe the hard-free application route under the user-confirmed free account configuration; no billing statement was fetched.

## Production deployment and tests

- Deployment uses source from abe1bc07f0dd2d83d3b6ce411edc20891b7131bf. Final probe commit f27783ff8e9be245bcdee3a6383faf4e8b7ea3d8 did not change the deployed source.
- Supabase function version 15, ACTIVE, function id 4ba17bd0-de94-418e-89a3-fa9e8bfb0ebf.
- Provider bundle SHA256: 41de2e9d067228bdc359c472ee05e8f74f962a901e8bd6823e3ab942046a33c0.
- Normalized source SHA256: 9fef2d1b023730374e93b8241ff793be75c8d2b35fa7e28ade9a76c83b9d6e3b. Downloaded deployed source matched local source exactly after newline normalization.
- Deno 2.7.4 type check PASS. A pre-existing possibly-undefined quota-metric expression was corrected without changing provider behavior; runtime type dependency pinned to 2.116.0.
- Python proof tests: 5 PASS. Node mesh tests: 9 PASS. Remote CI repeats both.
- Covered: zero-spend and live gates, unsupported model rejection, HTTP 200/usage/header handling, immediate 429 cooldown, HTTP-date retry, 401/403/503/transport/malformed output rejection, model-only fallback, normal mesh, forced-route isolation, existing Lightning fallback and missing/paid cost-evidence rejection.
- Post-deploy smoke: GET 405; unauthenticated POST 401/OIDC_MISSING; authenticated normal-mesh request 200. Existing verify_jwt=false preserved because the function verifies GitHub OIDC internally; auth was not relaxed.
- Final normal run independently observed working Lightning and Mistral. No regression found in the executed tests and smoke checks; this does not assert exhaustive behavior under every provider/outage/concurrent-isolate scenario.

## Observed capacity and conservative gate

Final Mistral normal request: provider=mistral-free, model=ministral-3b-latest, HTTP 200, usage.total_tokens=153, mandatory_cost_usd=0, paid_fallback_used=false, Retry-After absent.

| Header | Observed value |
|---|---:|
| x-ratelimit-limit-req-minute | 750 |
| x-ratelimit-limit-tokens-minute | 1300000 |
| x-ratelimit-remaining-req-minute | 748 |
| x-ratelimit-remaining-tokens-minute | 1299702 |
| x-ratelimit-tokens-query-cost | 153 |

No daily or monthly free token allowance was returned. The generic X-RateLimit-Remaining was absent; the actual request/token-specific remaining headers above are retained. TPM/RPM are throughput ceilings, not recurring free daily capacity. Do not multiply TPM by 1440 or add per-model limits without proof of independence.

| Provider | Existing evidence and limitation | Certified recurring daily contribution |
|---|---|---:|
| Mistral | Actual HTTP 200 and minute headers; daily/monthly included free allowance UNKNOWN | 0 counted / UNKNOWN actual |
| Lightning | Actual normal HTTP 200; inherited manifest claims 30M/month, whose 1M/day arithmetic average is not a daily guarantee | 0 counted / UNKNOWN actual |
| Groq | Inherited per-model table 200k/day; no current account-wide independent allowance verified in this audit | 0 counted / UNKNOWN actual |
| Gemini | Dynamic free limits; no independently quantified recurring daily allowance in evidence | 0 counted / UNKNOWN actual |

Conservative certified daily sum for this audit: 0 tokens/day counted. Actual total mesh capacity: UNKNOWN, not zero. Target: 3,000,000/day. Gate: FAIL_INSUFFICIENT_QUANTITATIVE_EVIDENCE. This deliberately excludes unverified quantities instead of inventing capacity.

Remaining external evidence: Mistral Admin > API > Limits showing the actual account's included free allowance and relevant time windows; equivalent current independent quota evidence for other providers before summing them. Browser access was blocked by automatic review due to workspace credits and was not bypassed. HTTP operation is already proven and no API key is needed again.

Primary guidance: https://docs.mistral.ai/admin/billing-usage/usage-limits distinguishes included monthly usage, API rate limits and Pay-As-You-Go. Supabase secret/deploy behavior was checked against https://supabase.com/docs/guides/functions/secrets and https://supabase.com/docs/guides/functions/deploy.

## Files and rollback

Changed: arbm_provider_probe.py; test_provider_probe.py; test_mistral_mesh.mjs; .github/workflows/arbm-provider-probe.yml; supabase/functions/arbm-terminal-agent-v7/index.ts; .gitignore; free-capacity-manifest.json; this evidence report and its sanitized JSON companion.

Rollback source: git object 55c13254230165713efc09edfd5d8f58887493b5:supabase/functions/arbm-terminal-agent-v7/index.ts, matching pre-change provider function version 13. A local ignored copy is preserved at .local-evidence/rollback-v13-index.ts. Restore that source in this isolated repo and deploy only arbm-terminal-agent-v7 to pvkpkqwdnnpkgvllwqbc with its existing OIDC configuration. Optionally set ARBM_MISTRAL_LIVE_PROVEN=0 to disable its normal eligibility immediately. Preserve all keys and unrelated settings; do not force-push history. Evidence-only commits require no redeploy.
