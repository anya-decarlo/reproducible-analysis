#!/usr/bin/env python3
"""Step 5 — verify: prove the build is reproducible.

Re-runs transform + analyze into a scratch directory from the *same*
recorded inputs, hashes every regenerated output, and compares against
the outputs in outputs/. Byte-identical => REPRODUCIBLE. This catches
nondeterminism (dict ordering, timestamps, floating-point drift) that
code review alone won't.

The run record (build/run.json) and data manifest are provenance, not
outputs, so they're excluded from comparison — timestamps inside them
are metadata, not results.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.common import ROOT, sha256
from pipeline import analyze, transform

COMPARE = ["facts_clean.csv", "annual_metrics.csv", "yoy_growth.csv"]


def verify(raw_dir: Path, out_dir: Path) -> tuple[bool, list[str]]:
    messages = []
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        clean = tmp / "facts_clean.csv"
        transform.transform(raw_dir, clean)
        analyze.analyze(clean, tmp / "annual_metrics.csv",
                        tmp / "yoy_growth.csv")
        for name in COMPARE:
            orig, new = out_dir / name, tmp / name
            if not orig.exists():
                ok, msg = False, f"MISSING  {name}"
            else:
                same = sha256(orig) == sha256(new)
                ok &= same
                msg = f"{'IDENTICAL' if same else 'DIFFERS'}  {name}  {sha256(orig)[:12]}"
            messages.append(msg)
    return ok, messages


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    p.add_argument("--out-dir", type=Path, default=ROOT / "outputs")
    args = p.parse_args()

    ok, messages = verify(args.raw_dir, args.out_dir)
    print("reproducibility check (recompute from recorded inputs):")
    for m in messages:
        print(f"  {m}")
    print("REPRODUCIBLE" if ok else "NOT REPRODUCIBLE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
