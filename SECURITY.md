# Security Policy

## Supported code

Security review applies to the current default branch and to release candidates explicitly identified by an immutable commit SHA.

## Reporting a vulnerability

Use GitHub Security Advisories / private vulnerability reporting for this repository when available. Do not publish exploit details, credentials, tokens, private keys, or reproducible attack material in a public issue.

A report should include the affected commit SHA, component, impact, minimal reproduction, and any known mitigations. Reports are triaged fail-closed: a credible unresolved security issue blocks release promotion until disposition is evidenced.

## Engineering requirements

- No credentials or long-lived secrets in source control.
- GitHub Actions dependencies must be pinned to immutable commit SHAs.
- Critical execution paths require deterministic policy gates and reproducible evidence.
- Known HIGH or CRITICAL dependency vulnerabilities block release.
- Secret-scanner findings block release.
- Security bypasses, waivers, and silent suppressions are not accepted in the release gate.
- Security evidence must be bound to the candidate commit SHA.
