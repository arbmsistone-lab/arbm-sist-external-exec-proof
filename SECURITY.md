# Security Policy

## Supported code

Security fixes are developed against the current default branch and must preserve
the repository's fail-closed, exact-SHA, ZERO_SPEND and provenance gates.

## Reporting a vulnerability

Do not disclose exploit details, credentials, tokens, personal data, or
production-sensitive information in a public issue.

Prefer GitHub's private security-advisory reporting channel for this repository
when it is available. If private reporting is unavailable, open a minimal public
issue that requests a private contact channel without including vulnerability
details.

A useful report includes the affected commit, affected component, impact,
reproduction prerequisites, minimal proof of concept, and any proposed
mitigation.

## Handling requirements

Security changes must:

- remain fail-closed;
- include regression coverage for the reported weakness;
- avoid secret or policy bypasses;
- preserve immutable evidence and exact-SHA provenance;
- pass the repository's security, dependency, SAST and regression gates before
  promotion;
- avoid paid fallbacks or hidden external dependencies.

Public disclosure should occur only after a fix is available and the disclosure
does not expose credentials, private data, or an active unmitigated production
weakness.
