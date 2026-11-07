# reproducible-analysis

A small EDGAR pipeline built to demonstrate *reproducibility habits* —
the pipeline is deliberately simple; the practices around it are the
deliverable. Fourth in a series with
[sec-data-quality](https://github.com/anya-decarlo/sec-data-quality),
[sec-financial-analytics](https://github.com/anya-decarlo/sec-financial-analytics),
and [sec-stats-dashboard](https://github.com/anya-decarlo/sec-stats-dashboard).

## Run it

```bash
make all      # ingest -> transform -> analyze -> validate -> verify
make test     # unit tests
make clean    # drop generated outputs
```

Stdlib-only Python; inputs are SEC EDGAR companyfacts payloads (fetched
live, or `--copy-from` a sibling repo's cache).

## Where each habit lives

| Habit | Artifact |
|---|---|
| **Version control** | git history + `CHANGELOG.md`; every run records `git_sha` in `build/run.json` |
| **Documented transformations** | `manifest.toml` — every step's script, inputs, outputs, and rules (T1–T5) in one place; the PR template requires updating it in the same commit as the code |
| **Quality checks** | `make validate` gates the build (nonzero on new violations); `baselines/known_violations.json` suppresses only *investigated, documented* findings; unit tests in `tests/` |
| **Peer review** | `.github/pull_request_template.md` checklist, `CODEOWNERS`, `CONTRIBUTING.md` review protocol; CI runs the whole pipeline + verify on every PR |
| **Reproducibility proof** | `make verify` recomputes all outputs from recorded inputs and compares sha256 — byte-identical or it fails |
| **Provenance** | `data/manifest.json`: per-input sha256, source URL, cache status; `build/run.json`: per-step input/output hashes, timing, git sha, Python version |

## Design decisions worth noting

- **Outputs are committed.** Generated CSVs stay in git so a PR's data
  impact is reviewable as a diff — the most important review signal in a
  data repo.
- **Known violations are baselined, not hidden.** MSFT FY2016 (Nokia
  impairment-era gap between quarterly and annual filings) is documented
  with a reason in `baselines/` — new, un-investigated violations still
  fail the build.
- **Inputs are hashed, not vendored.** Raw payloads are ~4MB each and
  re-fetchable; the committed manifest proves exactly which bytes were
  analyzed.
- **No stochastic steps**, so determinism is achievable and therefore
  enforced (`verify` exists because *achievable* ≠ *guaranteed*).

## Layout

```
manifest.toml            the documented list of transformations
Makefile                 one command per pipeline stage + gates
pipeline/
  common.py              sha256, run record, deterministic writers
  ingest.py              fetch + provenance manifest
  transform.py           flatten/clean/supersede (rules T1–T5)
  analyze.py             annual metrics + YoY
  validate.py            gated checks + baseline suppression
  verify.py              recompute-and-compare proof
tests/                   unittest suite
baselines/               documented known violations
data/manifest.json       input hashes + provenance (committed)
build/run.json           per-run record: git sha, env, step hashes
outputs/                 committed generated tables
.github/workflows/ci.yml CI: test + pipeline + verify on every PR
.github/pull_request_template.md, CODEOWNERS, CONTRIBUTING.md
```
