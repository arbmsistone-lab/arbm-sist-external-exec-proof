# Security Policy

## Supported code

Security fixes target the current default branch and active release candidates.
Every security change must preserve the repository's fail-closed, exact-SHA,
ZERO_SPEND and provenance gates.

## Private vulnerability reporting

Report vulnerabilities privately through GitHub Security Advisories:

https://github.com/arbmsistone-lab/arbm-sist-external-exec-proof/security/advisories/new

Do not disclose exploit details, credentials, tokens, personal data, production
configuration, or active unmitigated weaknesses in public issues.

A useful report includes the affected commit, component, impact, prerequisites,
minimal proof of concept, and any proposed mitigation.

## Response targets

- acknowledgement: within 2 business days;
- initial severity/triage decision: within 7 calendar days;
- critical actively exploitable issue: mitigation or containment targeted within
  72 hours after confirmation;
- high severity issue: remediation targeted within 14 calendar days;
- lower severity issues: scheduled according to verified impact and regression
  risk.

These are engineering response targets, not a promise that every report is a
valid vulnerability or that every remediation can be publicly disclosed on the
same schedule.

## Handling requirements

Security changes must:

- remain fail-closed;
- include regression coverage for the reported weakness;
- avoid secret, policy, provenance, or authorization bypasses;
- preserve immutable evidence and exact-SHA provenance;
- pass security, dependency, SAST, fuzz/regression, and release gates before
  promotion;
- avoid paid fallbacks or hidden external dependencies;
- use coordinated disclosure after mitigation, without exposing credentials,
  personal data, or an active unmitigated production weakness.
