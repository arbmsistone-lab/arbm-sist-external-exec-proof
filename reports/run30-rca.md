# Run 30 engineering record (closure pending official positive smoke)

Repository: arbmsistone-lab/arbm-sist-external-exec-proof. Baseline commit: 70e18bc3f5c044c81c188051c9ffaac0e486f331. Run: 34665245131.

## Findings from recorded evidence

All 227 files listed in the three original checksum manifests match their hashes. Each task's task-rc.txt was written after sealing and is absent from its manifest. All three official evaluator summaries report numeric score 0.0; all task return-code files contain 97. A summary status of `success` means evaluator execution succeeded, not that the task was solved.

The initial grounding failure is distinct from the historical action-name bug. Accessibility observations contain controls in background windows. The model treated their coordinates as clickable foreground targets. The screenshots contradict that assumption.

* 001: Thunderbird was opened, but Chrome's Thunderbird support page came to the foreground. The step-2 screenshot already shows Chrome while the agent continued issuing the mail-list coordinate `(380,238)`. It never completed the requested calendar edits. The trajectory contains 78 steps, including 36 WAITs and 29 instances of that click. Four malformed Python commands reached the guest. Provider attempts include 75 HTTP 413s and 152 HTTP 429s.
* 002: the initial foreground is the maximized Course Planner browser. Desktop PDF labels nevertheless appear in the accessibility tree. Steps 1-3 move/click at those covered labels instead of revealing the desktop. Later actions remain in failed file-opening/scrolling loops; no enrolment/export deliverable is established. The trajectory contains 70 steps. The replay rejects malformed statements and unbounded scrolls. Provider attempts include 26 HTTP 413s and 145 HTTP 429s.
* 003: Impress covers the desktop, but the first action clicks the background `city.zip` label's coordinates. Subsequent actions repeat covered coordinates and fail to produce the required composites and slide backgrounds. The trajectory contains 43 steps, five malformed commands rejected by the new replay, 42 HTTP 413s and 84 HTTP 429s.

The official artifacts contain no evaluator subcriterion breakdown and no complete original model JSON, provider error messages or planner memory. Those absent facts cannot be reconstructed honestly. The report uses the actual emitted response, executed action, runtime accessibility tree, screenshot, provider/model/status telemetry and official result. The new pack records full normalized actions, model response text, payload measurements, requests and observed before/after verification.

## Corrections and regression mapping

| Cause | Changed files | Behavioral regression |
|---|---|---|
| Regex validated only a command prefix; arrays became comma-separated strings and object placeholders | endpoint/index.ts; scripts/osworld_control.py | test_endpoint.mjs fails against endpoint-v12.ts; malformed recorded commands rejected in replay |
| Occluded controls treated as foreground, single clicks treated as file opening | endpoint/index.ts | recorded screenshot inference preflight rejects historical occluded targets before any VM run |
| Changing commands and cyclic observations evade no-progress detection | scripts/osworld_control.py; scripts/osworld_free_mesh_shim.py | repeated/different commands on unchanged observations, cyclic screens, terminal recovery budget |
| Character truncation and uncompressed PNGs; route cooldown lost across endpoint isolates | controller, shim, endpoint | UTF-8 byte gate, full recorded-image replay, HTTP 413/429 and persistent route cooldown tests |
| Provider errors/invalid actions can end routing too early | endpoint/index.ts; shim | 413/422/429/5xx failover tests with both FREE routes; no paid route exists |
| Finish based solely on model assertion | controller and shim | premature finish rejected; observed change and visible evidence required |
| task rc outside seal; aggregate checked only float count/max | scripts/osworld_evidence.py; smoke workflow | exact checksum coverage, changed files, task rc, NaN, evaluator mismatch, missing FREE proof, zero scores |

25 Python tests plus endpoint contract/routing cases pass locally. Recorded observation replay covers all 191 steps without executing guest actions or consuming an OSWorld run. See run30-replay.json for per-task rejection hashes and payload measurements.

## Execution discipline

Pushes run only local regression and remote inference replay. The official three-task smoke requires explicit workflow_dispatch with run_smoke=true. A concurrency group serializes this entire front. The endpoint build and deployment digest are pinned in the manifest. No endpoint mutation is permitted while a smoke runs. Controlled recovery exhaustion emits the official FAIL action; the official evaluator still runs and records the actual zero/partial score. Infrastructure/contract/cost failures remain fatal. The aggregate requires three official numeric scores, at least one positive, valid evaluator summaries, successful runner return codes and sealed evidence.

No ARBM One or ZEVANORY files, project settings, credentials or deployments are changed. No full-108 run is authorized by this change.

## Additional defect caught by remote replay 34691892976

The initial remote grounding gate was too narrow: it rejected only the historical coordinates, so it accepted a different background control (Home at 1833,1037, and Calendar at 77,124). Manual screenshot review prevented a VM smoke. Regression now requires foreground recovery for 001 and excludes the entire occluded desktop label region for 002/003. The controller derives the active application from Ubuntu's panel menu, removes covered desktop coordinates, and removes preceding non-Chrome window sections when Chrome is active.

Provider error text also proved that Groq's 413 was an input-token limit (7000 ITPM, request 7591), not a raw byte cap. The image is now bounded to 1280x720 with original-coordinate metadata; Groq receives a smaller operational prompt. Successful Groq calls establish a client-side cooldown proportional to measured prompt tokens. Both byte and token-related regressions are now gated. Local regression is 26 Python tests plus endpoint cases; all 191 recorded steps pass payload/recovery replay again. No official smoke was run for the permissive gate.

## Additional quality fixes after replay 34692140906

No recurring 413 remained in this gate. All three model outputs stopped clicking the occluded files/mail target. Review caught an explicit desktop-activation plan paired with Alt+Tab, and nested memory objects converted to `[object Object]`. The action compiler now maps that exact desktop-activation intent to Ubuntu Ctrl+Alt+D; other Alt+Tab actions remain intact. Structured memory is serialized as JSON instead of discarded by JavaScript coercion.

The Groq response reported an output-token quota of 1000/minute while each request reserved 900. Current official Groq documentation confirms Qwen supports `reasoning_effort: none`; the direct action request now disables hidden reasoning and reserves 600 output tokens, with regressions checking the actual provider payload. This also avoids spending the JSON output budget on reasoning and the resulting 400 JSON validation failure. Source: https://console.groq.com/docs/reasoning . Total local regression: 27 Python tests plus endpoint routing/contract/output-budget cases.
