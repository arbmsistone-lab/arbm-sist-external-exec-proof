# OSWorld V2.1 Self-Hosted Website Plan

Status: PREPARED - NOT DEPLOYED
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
3. Pinned `Task-Web/OSWorld-web` checkout at the exact V2.1 commit with all pinned submodules.
4. No uncommitted website changes.
5. Generated upstream `docker-compose.yml` present.
6. Caddy reverse proxy exposed on the required HTTP/HTTPS ports.
7. A wildcard-capable DNS suffix reachable by the OSWorld guest/browser.
8. `HOST_SUFFIX=<verified-suffix>` and matching OSWorld runtime website suffix.
9. Source commit, submodule state, host suffix and deployment evidence sealed before task execution.
10. No benchmark task begins until the website/control-plane validation passes.

## DNS strategy

Preferred preparation order:

### Route 1 - Existing controlled wildcard domain

Use a wildcard subdomain under a domain already controlled by ARBM, pointing to the qualified remote host. This provides the strongest control over DNS and avoids dependence on a third-party wildcard resolver. No DNS mutation is authorized by this document alone.

### Route 2 - Upstream-documented free wildcard resolver

The upstream README documents `nip.io` for public or private IP wildcard resolution. This is acceptable only after the exact evaluation network proves resolution from the guest/browser. Resolver/rebinding protections may block private-IP use, so failure must be fail-closed rather than bypassed silently.

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

It does not:
- start containers;
- alter DNS;
- deploy a website;
- run OSWorld tasks;
- authorize a full benchmark.

## Deployment evidence required before V2.1 execution

- remote host identifier and execution environment;
- website repository SHA;
- full submodule status;
- generated Compose file digest;
- host suffix used;
- DNS resolution evidence from host and guest/browser;
- Caddy routing evidence for required applications;
- upstream control-plane verification output where applicable;
- timestamped health evidence;
- zero-spend declaration/evidence for the selected hosting route;
- proof that no official task/evaluator source was modified.

## Execution gate

The current machine-readable pins intentionally contain:

`"full_run_authorized": false`

Therefore:

`OSWORLD_V2_1_SELFHOST_PLAN = PREPARED`

`OSWORLD_V2_1_WEBSITE_DEPLOYED = FALSE`

`OSWORLD_V2_1_FULL_BENCHMARK = BLOCKED`
