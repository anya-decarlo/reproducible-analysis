# Contributing & review workflow

## The loop

1. Branch off `main` — name it `feat/<what>` or `fix/<what>`.
2. Make the change. If it alters how data is produced, update
   `manifest.toml` in the same commit — documentation travels with code.
3. Run `make test && make validate && make verify`. All must pass.
4. Commit regenerated `outputs/` — output diffs are part of the review.
5. Open the PR; the template walks you through the checklist.
6. Wait for CI + owner review. Squash-merge.

## What a reviewer checks

- **Understandability**: could they reproduce the change's intent from
  `manifest.toml` and the diff, without asking you?
- **Output diffs**: regenerated CSVs are committed — do the number
  changes match what the code change claims to do?
- **Quality gates**: CI green; if `baselines/` grew, every new entry has
  a `reason` that would satisfy an auditor.
- **Determinism**: `verify` passed in CI, not just on your machine.
- **Tests**: new logic covered, or an explicit note on why not.

## Adding a known violation to the baseline

Only after investigating. The entry needs every violation key plus a
`reason` that answers "why is this OK to ship" — see
`baselines/known_violations.json` for examples.

## Data sources

Raw EDGAR payloads are cached under `data/raw/` and gitignored (large,
re-fetchable); their sha256s live in `data/manifest.json` which **is**
committed — provenance without the payload.
