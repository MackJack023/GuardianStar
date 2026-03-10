# Security Policy

## Supported Versions

GuardianStar is currently in active prototype stage. Security fixes are applied on the latest `main` branch and newest release tag.

## Reporting a Vulnerability

Please do not open public issues for sensitive vulnerabilities.

Report privately with:

- vulnerability summary
- impact assessment
- reproduction steps
- optional proof-of-concept

Contact:

- GitHub security advisory (preferred) on this repository
- or open a private maintainer contact request

## Response Expectations

- Initial acknowledgement: within 3 business days
- Status update: within 7 business days
- Fix timeline: depends on severity and reproducibility

## Security Scope Notes

Current project limitations to be aware of:

- prototype-level authentication model
- local JSON persistence for backend state
- no production secret rotation pipeline

Do not use this project as-is for high-risk or regulated production workloads.

