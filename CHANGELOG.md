# Changelog

## 0.1.0 — 2026-11-06

- Initial pipeline: ingest (EDGAR companyfacts + provenance manifest) →
  transform (clean + supersede + metric mapping) → analyze (annual +
  YoY) → validate (4 gated checks + known-violation baseline) →
  verify (byte-identical recompute proof).
- CI: unit tests, full pipeline run, reproducibility check on every PR.
- Review scaffolding: PR template, CODEOWNERS, CONTRIBUTING workflow.
