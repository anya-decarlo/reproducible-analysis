## What & why
<!-- One paragraph: what changed, and why it was needed. -->

## Transformations touched
<!-- Did you change how data is produced? If so, manifest.toml MUST be updated in this PR. -->
- [ ] No transformation changes
- [ ] Transformation changes — `manifest.toml` updated

## Quality checks
- [ ] `make test` passes locally
- [ ] `make validate` — no NEW violations (known ones are in `baselines/`)
- [ ] `make verify` — outputs byte-identical on recompute
- [ ] If validation newly fails: investigated & added to `baselines/` WITH a reason, or fixed

## Reviewer notes
<!-- Anything you want the reviewer to look at specifically: assumptions,
     thresholds, a number that surprised you. -->

## For the reviewer
- [ ] Changes are understandable from manifest.toml + code alone
- [ ] Output diffs in `outputs/` make sense given the code change
- [ ] New logic has a test, or a reason it doesn't need one
- [ ] No silent data drops — every filter is declared in the manifest
