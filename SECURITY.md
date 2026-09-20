# Security Policy

## Supported code

Security review applies to the current default branch and to release candidates explicitly identified by an immutable commit SHA.

## Vulnerability disclosure

Report a **Vulnerability** privately through GitHub Security Advisories for this repository:

https://github.com/arbmsistone-lab/arbm-sist-external-exec-proof/security/advisories/new

This is the preferred disclosure channel. Do not publish exploit details, credentials, tokens, private keys, or reproducible attack material in a public issue.

A vulnerability disclosure should include the affected commit SHA, component, security impact, minimal reproduction, and any known mitigations. Reports are triaged fail-closed: a credible unresolved security issue blocks release promotion until disposition is evidenced.

## Response and engineering requirements

- No credentials or long-lived secrets in source control.
- GitHub Actions dependencies must be pinned to immutable commit SHAs.
- Critical execution paths require deterministic policy gates and reproducible evidence.
- Known HIGH or CRITICAL dependency vulnerabilities block release.
- Unknown-severity findings in the World-Free Assurance gate block release until classified.
- Secret-scanner findings block release.
- Security bypasses, waivers, and silent suppressions are not accepted in the release gate.
- Security evidence must be bound to the exact candidate commit SHA.
- Remediation is verified by independent regression and security scanners before promotion.
