# OSWorld V2.1 Self-Hosted Website Plan

Status: REMOTE CANARY PROVEN - FULL WEBSITE NOT YET DEPLOYED
Date: 2026-09-17

## Objective

Prepare a reproducible, remote-only, ZERO_SPEND-compatible self-hosted website environment required by OSWorld V2.1 without altering benchmark task semantics and without starting the full benchmark.

## Official website pin

Repository: `Task-Web/OSWorld-web`
Tag: `osworld-v2.1`
Pinned commit: `60c89fe6a8ed934668619d8d26132848239eb8ee`

The upstream architecture uses Docker Compose plus a Caddy reverse proxy. Each application is routed under its own hostname and the domain suffix is controlled by `HOST_SUFFIX`/`OSWORLD_HOST_SUFFIX`. Default local operation uses `localhost`; remote evaluation requires a suffix resolvable from the benchmark browser/VM.

## Required remote architecture

1. Qualified remote Linux host only; heavy local execution remains prohibited.
2. Docker Engine + Compose plugin.
3. Pinned `Task-Web/OSWorld-web` checkout at the exact V2.1 commit with pinned submodules.
4. No uncommitted website changes.
5. Generated upstream `docker-compose.yml` present.
6. Caddy reverse proxy exposed on the required HTTP/HTTPS ports.
7. A wildcard-capable DNS suffix reachable by the OSWorld guest/browser.
8. `HOST_SUFFIX=<verified-suffix>` and matching OSWorld runtime website suffix.
9. Source commit, submodule state, host suffix and deployment evidence sealed before task execution.
10. No benchmark task begins until the website/control-plane validation passes.

## Proven remote canary - 2026-09-17

Preparation-only run:
- GitHub Actions run: `35225428524`
- Branch SHA: `25dee2bda9dde66dfb56b86bce3cd5831a2974f4`
- Runner: GitHub-hosted Ubuntu 24.04
- ZERO_SPEND_MODE: `HARD`
- heavy local: `0`
- paid fallback: `false`
- full run authorized: `false`
- benchmark tasks started: `0`

Pinned runtime evidence:
- OSWorld website SHA: `60c89fe6a8ed934668619d8d26132848239eb8ee`
- `dinogame_web` submodule SHA: `a822adbe4ea23b48e06ae051dc14ddf5aea0b69e`
- wildcard canary: `dinogame.127.0.0.1.nip.io -> 127.0.0.1`
- Caddy image digest observed: `sha256:33081120c6df8613cebbdbdd4c3b8aef641e9e56c1cd3d86d04ea9651cb3cc68`

Functional verdict:
- `SELFHOST_CANARY=PASS`
- `CADDY_ROUTING=PASS`
- `CONTROL_PLANE_DEEP_MERGE=PASS`
- state PUT/PATCH/GET preserved `left=1`, `right=2` and unrelated sibling state
- containers and volumes were removed after evidence capture

Evidence artifact:
- Name: `osworld-v21-selfhost-canary`
- Artifact ID: `10498659507`
- Artifact ZIP SHA256: `5a50811d97303632dc527cdf1cc7bf16ede9773def0d3f7d6bcf856130545871`
- Files preserved: 19
- Retention expiry: 2026-10-17

## Security observation from official canary

The unmodified official `dinogame_web` dependency installation reported 24 npm audit findings: 2 low, 7 moderate, 13 high and 2 critical. This is recorded as upstream benchmark-environment risk R21.

Treatment:
- do not inject ARBM production secrets into this benchmark website runtime;
- keep runtime ephemeral/isolated;
- do not silently patch official source because that may invalidate benchmark comparability;
- track maintainer/upstream remediation and disclose the finding during external verification if still applicable.

## DNS strategy

### Route 1 - Existing controlled wildcard domain

Use a wildcard subdomain under a domain already controlled by ARBM, pointing to the qualified remote host. This provides the strongest control over DNS and avoids dependence on a third-party wildcard resolver. No DNS mutation is authorized by this document alone.

### Route 2 - Upstream-documented free wildcard resolver

The upstream README documents `nip.io` for public or private IP wildcard resolution. The 2026-09-17 canary proved loopback wildcard resolution inside the GitHub-hosted runner. This does not yet prove reachability from an OSWorld guest VM on a separate network; that remains a later gate.

## Preflight

Preparation script:

`scripts/osworld_v21_selfhost_preflight.py`

It verifies:
- ZERO_SPEND HARD;
- paid fallback false;
- heavy local = 0;
- self-host deployment mode;
- non-localhost DNS suffix;
- exact website SHA;
- clean website checkout;
- presence of upstream Compose and submodule metadata;
- Docker/Compose availability;
- full benchmark remains blocked unless the machine-readable manifest explicitly authorizes it.

The preflight itself does not:
- start containers;
- alter DNS;
- deploy a website;
- run OSWorld tasks;
- authorize a full benchmark.

## Next runtime gate

The next technical gate is broader runtime-site coverage under the same remote-only policy:

1. validate the official runtime submodules in controlled shards rather than loading all services locally;
2. prove Caddy routing and control-plane semantics for the runtime-site set;
3. preserve per-shard source SHAs, DNS/routing results and state-isolation evidence;
4. verify no benchmark task/evaluator source was touched;
5. only after runtime-site coverage passes, prove guest/VM reachability to the chosen self-host suffix.

## Execution gate

The current machine-readable pins intentionally contain:

`"full_run_authorized": false`

Therefore:

`OSWORLD_V2_1_SELFHOST_CANARY = PASS`

`OSWORLD_V2_1_FULL_WEBSITE_COVERAGE = PENDING`

`OSWORLD_V2_1_PERSISTENT_WEBSITE_DEPLOYMENT = FALSE`

`OSWORLD_V2_1_FULL_BENCHMARK = BLOCKED`
