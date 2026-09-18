# STANDARDS & REGULATORY APPLICABILITY MATRIX

This matrix records stable reference versions identified from official or project-maintainer sources. Drafts/RCs are non-normative unless explicitly listed as supplemental.

| Standard / framework | Stable reference | Applicability to ARBM SIST | Certification semantics |
|---|---|---|---|
| ISO/IEC 25010 | 2023 | APPLICABLE | Internal quality model mapping only |
| ISO/IEC 27001 | 2022 | PARTIALLY APPLICABLE | Controls/process guidance; formal certification requires accredited external body |
| ISO/IEC 27701 | 2025 | PARTIALLY APPLICABLE where PII exists | Formal certification/external legal interpretation may be required |
| ISO 22301 | 2019 | PARTIALLY APPLICABLE | Continuity/DR reference; formal certification external |
| ISO/IEC 42001 | 2023 | APPLICABLE to AI management aspects | Internal technical mapping; formal certification external |
| NIST Cybersecurity Framework | CSF 2.0 (2024) | APPLICABLE | Governance/risk outcome mapping |
| NIST SSDF | SP 800-218 v1.1 | APPLICABLE | Secure SDLC / software supply chain practices |
| OWASP ASVS | 5.0.0 | APPLICABLE to web/API security controls where present | Verification baseline |
| OWASP SAMM | 2.2.0 | PARTIALLY APPLICABLE | Software assurance maturity assessment |
| OWASP Top 10 | 2025 | APPLICABLE where web application attack surface exists | Awareness/risk coverage; not a certification |
| CWE / CVE | Current catalogs | APPLICABLE | Weakness/vulnerability classification |
| CIS Controls / Benchmarks | Component-specific current stable | PARTIALLY APPLICABLE | Baseline hardening; exact benchmark must match deployed component |
| SLSA | 1.2 | APPLICABLE | Source/build provenance and supply-chain assurance |
| SPDX | 3.0.1 | APPLICABLE | SBOM/provenance interchange candidate |
| CycloneDX | 1.7 | APPLICABLE | SBOM interchange candidate |
| WCAG | 2.2 / ISO/IEC 40500:2025 | PARTIALLY APPLICABLE to user-facing interfaces | Target level must be declared per surface; no blanket AAA |
| LGPD (Brazil) | Lei 13.709/2018, compiled current text | PARTIALLY APPLICABLE if personal data is processed | Legal compliance requires factual data-flow mapping and may require specialist legal review |

## Official reference locations

- ISO/IEC 25010:2023 — https://www.iso.org/standard/78176.html
- ISO/IEC 27001:2022 — https://www.iso.org/standard/27001
- ISO/IEC 27701:2025 — https://www.iso.org/standard/27701
- ISO 22301:2019 — https://www.iso.org/standard/75106.html
- ISO/IEC 42001:2023 — https://www.iso.org/standard/42001
- NIST CSF 2.0 — https://csrc.nist.gov/pubs/cswp/29/the-nist-cybersecurity-framework-csf-20/final
- NIST SSDF 1.1 — https://csrc.nist.gov/pubs/sp/800/218/final
- OWASP ASVS — https://owasp.org/projects/asvs
- OWASP SAMM releases — https://github.com/owaspsamm/core/releases
- OWASP Top 10:2025 — https://top10.owasp.org/2025/
- SLSA 1.2 — https://slsa.dev/spec/v1.2/
- SPDX 3.0.1 — https://spdx.github.io/spdx-spec/v3.0.1/
- CycloneDX 1.7 — https://cyclonedx.org/docs/1.7/json/
- WCAG 2.2 — https://www.w3.org/WAI/standards-guidelines/wcag/
- LGPD compiled text — https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm

## Draft handling

Draft, DIS, FDIS, preview, release-candidate, or working-draft documents may be used only as supplemental forward-looking guidance. They cannot silently replace the stable normative baseline.
