# AUTHORITATIVE SYSTEM INVENTORY — ARBM SIST

Evidence source: repository tree at RC SHA `f114c9b1833d5ae5a07af923dae548033078485d`.

## Identity

- Repository: `arbmsistone-lab/arbm-sist-external-exec-proof`
- Release-candidate proof branch: `chatgpt/arbm-top3-consolidated-20260917`
- Frozen RC SHA: `f114c9b1833d5ae5a07af923dae548033078485d`
- Default branch observed: `master`
- Master SHA observed during baseline: `cf008c04e9bf01e87fca80799dfc25b1de68d888`
- Branch relation at baseline: **DIVERGED** — candidate ahead 310 commits and behind 265 commits relative to master.

## Principal runtime components

| Component | Path / identity | Function | Assurance status |
|---|---|---|---|
| Remote agent endpoint | `endpoint/index.ts` | GitHub OIDC-authenticated FREE provider control plane | INVENTORIED; auth/branch parity risk open |
| Compatibility endpoint | `endpoint-v12.ts` | earlier/alternate endpoint implementation | INVENTORIED; final deployed usage UNVERIFIED |
| Mesh shim | `scripts/osworld_free_mesh_shim.py` | local OpenAI-compatible bridge, routing, policy, recovery, evidence | ACTIVE RC component |
| Deterministic control | `scripts/osworld_control.py` | canonical GUI actions, grounding, verifier | ACTIVE RC component |
| Elite controller | `scripts/osworld_elite_controller.py` | progress/tabu/latency controller | ACTIVE RC component |
| OpenRouter FREE route | `scripts/osworld_openrouter_free.py` | zero-price multimodal/text route with cost proof | ACTIVE RC component |
| Groq FREE route | `scripts/osworld_groq_free.py` | FREE-plan route with header/rate-limit proof | ACTIVE RC component |
| Local VLM | `scripts/osworld_local_vlm.py` | quota-independent cloud-runner VLM fallback | ACTIVE RC component |
| Free judge | `scripts/osworld_free_judge.py` | evaluator/judge proxy | ACTIVE RC component |
| Evidence sealing | `scripts/osworld_evidence.py` | checksums and evidence coverage | ACTIVE RC component |
| v32 audit gate | `scripts/osworld_v32_gate.py` | exact score, pins, cost, provenance, evaluator integrity | ACTIVE RC component |
| Historical gate | `scripts/osworld_v32_historical_gate.py` | replay of prior evidence through current policy | ACTIVE RC component |
| Integrity verifier | `scripts/osworld_v32_integrity.py` | before/after evaluator integrity | ACTIVE RC component |

## Pinned dependencies and external assets

- Python closure requirements: `Pillow==12.1.1`, `ijson==3.4.0`.
- Workflow runtime additionally pins torch/transformers/safetensors for local VLM.
- OSWorld release: `osworld-v2-2026.08.08`.
- OSWorld upstream SHA: `d578d2d4e0dc82b43e270fdaa7fa89d9708cd154`.
- Task manifest SHA-256: `42f8f6f8939b8712997d5891456a575f8a2a5f53465e9e3e6747af5d6efd0915`.
- Official VM revision: `8213366932c553e5fe758d0f2c8c8b81ffc3be8c`.
- Official VM archive SHA-256: `eb737ae70b49849e24af407de6a518439a23de05a8497096a948334ce0a909aa`.
- Docker digest: `sha256:0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9`.
- Local VLM model: `HuggingFaceTB/SmolVLM-256M-Instruct`, revision `7e3e67edbbed1bf9888184d9df282b700a323964`.

## Secret / credential providers observed in workflows

- GitHub Actions OIDC token.
- `HF_TOKEN`.
- `OPENROUTER_API_KEY`.
- Groq FREE credential secret.
- Local loopback shim credential is synthetic and restricted to local process communication.

No claim is made that repository absence of plaintext secrets proves global secret hygiene. Dedicated secret scanning remains a required gate.

## CI/CD and benchmark workflows on RC

Active RC workflows include:
- `osworld-v32-policy-gate.yml`
- `osworld-v32-focal-091-free.yml`
- `osworld-v32-official-18.yml`
- `osworld-v32-cloud-matrix.yml`
- 091 contract replay/materialization workflows
- historical/incident/audit workflows

## Environment and infrastructure observed

- GitHub-hosted Ubuntu 24.04 runners.
- `/dev/kvm` required for official VM execution.
- Docker provider with a pinned OSWorld image.
- Official QCOW2 VM downloaded and hash-verified remotely.
- Heavy execution is remote; closure lane policy requires `heavy_local=0`.

## Production/deployment state

**UNVERIFIED / BLOCKED.** The repository evidence currently establishes benchmark/test runtime state, not complete served-production parity. Production identity must later prove:

`SOURCE SHA = CERTIFIED BUILD = ARTIFACT DIGEST = DEPLOYED VERSION = SERVED VERSION`.
