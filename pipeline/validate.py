#!/usr/bin/env python3
"""Step 4 — validate: data tests that gate the build.

Each check returns violations; the build FAILS (nonzero exit) if any
check is non-empty. Violations are written to
outputs/validation_report.json so a reviewer can see exactly what was
checked and what failed — the report is a deliverable, not a log line.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.common import ROOT, RunRecord, write_json

NON_NEGATIVE = {"revenue", "assets", "cash"}
FY_DAYS = (350, 400)
Q_DAYS = (75, 105)


def read(path: Path) -> list[dict]:
    with path.open() as fh:
        return list(csv.DictReader(fh))


def check_dupes(rows):
    seen, out = {}, []
    for r in rows:
        k = (r["entity"], r["tag"], r["unit"], r["start"], r["end"])
        seen[k] = seen.get(k, 0) + 1
    for k, n in seen.items():
        if n > 1:
            out.append({"key": list(k), "count": n})
    return out


def check_negatives(rows):
    return [{"entity": r["entity"], "metric": r["metric"], "end": r["end"],
             "val": r["val"]}
            for r in rows
            if r["metric"] in NON_NEGATIVE and float(r["val"]) < 0]


def check_durations(rows):
    return [{"entity": r["entity"], "tag": r["tag"], "end": r["end"],
             "duration_days": r["duration_days"]}
            for r in rows
            if r["duration_days"]
            and not (20 <= int(r["duration_days"]) <= 400)]


def check_quarters_tie(rows):
    """Four quarter-length facts must sum to the annual figure ±0.5%.

    Facts are deduped to one per period at the canonical metric level —
    the same quarter reported under two tag variants (Revenues vs
    RevenueFromContractWithCustomer…) must not count twice.
    """
    def per_period(rows_):
        best = {}
        for r in rows_:
            k = (r["entity"], r["metric"], r["unit"], r["start"], r["end"])
            if k not in best or (r["filed"], r["accn"]) > (
                    best[k]["filed"], best[k]["accn"]):
                best[k] = r
        return best

    ann = per_period(r for r in rows if r["duration_days"]
                     and FY_DAYS[0] <= int(r["duration_days"]) <= FY_DAYS[1])
    qtr = per_period(r for r in rows if r["duration_days"]
                     and Q_DAYS[0] <= int(r["duration_days"]) <= Q_DAYS[1])
    out = []
    for a in ann.values():
        if a["metric"] not in ("revenue", "net_income", "operating_income"):
            continue
        qs = [q for q in qtr.values()
              if q["entity"] == a["entity"] and q["metric"] == a["metric"]
              and q["unit"] == a["unit"]
              and a["start"] <= q["start"] and q["end"] <= a["end"]]
        if len(qs) != 4:
            continue
        gap = (float(a["val"]) - sum(float(q["val"]) for q in qs)) \
            / float(a["val"]) * 100
        if abs(gap) > 0.5:
            out.append({"entity": a["entity"], "metric": a["metric"],
                        "fy_end": a["end"], "gap_pct": round(gap, 3)})
    return out


CHECKS = {
    "duplicate_keys": check_dupes,
    "impossible_negatives": check_negatives,
    "implausible_durations": check_durations,
    "quarters_vs_annual": check_quarters_tie,
}


def _matches_baseline(violation: dict, baseline_entries: list[dict]) -> bool:
    """A violation is 'known' if every non-meta field of a baseline entry
    matches it (reason/first_seen are documentation, not match keys)."""
    for entry in baseline_entries:
        keys = {k for k in entry if k not in ("reason", "first_seen")}
        if all(violation.get(k) == entry[k] for k in keys):
            return True
    return False


def validate(facts_path: Path, report_path: Path,
             baseline_path: Path | None = None) -> tuple[dict, int]:
    rows = read(facts_path)
    baseline = {}
    if baseline_path and baseline_path.exists():
        import json
        baseline = json.loads(baseline_path.read_text())

    report = {"input": str(facts_path), "rows": len(rows),
              "baseline": baseline_path.name if baseline else None,
              "checks": {}}
    new_violations = 0
    for name, fn in CHECKS.items():
        found = fn(rows)
        known = [v for v in found
                 if _matches_baseline(v, baseline.get(name, []))]
        new = [v for v in found if v not in known]
        report["checks"][name] = {
            "violations_new": len(new), "violations_known": len(known),
            "sample_new": new[:10],
        }
        new_violations += len(new)
    report["status"] = "PASS" if new_violations == 0 else "FAIL"
    write_json(report_path, report)
    return report, new_violations


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--facts", type=Path,
                   default=ROOT / "outputs" / "facts_clean.csv")
    p.add_argument("--report", type=Path,
                   default=ROOT / "outputs" / "validation_report.json")
    p.add_argument("--baseline", type=Path,
                   default=ROOT / "baselines" / "known_violations.json",
                   help="documented violations to suppress")
    args = p.parse_args()

    t0 = time.time()
    report, new_violations = validate(args.facts, args.report,
                                      args.baseline)
    RunRecord().record("validate", [args.facts], [args.report],
                       time.time() - t0)
    for name, c in report["checks"].items():
        parts = []
        if c["violations_new"]:
            parts.append(f"{c['violations_new']} NEW")
        if c["violations_known"]:
            parts.append(f"{c['violations_known']} known")
        status = "+".join(parts) if parts else "PASS"
        print(f"  {name}: {status}")
    print(f"validation {report['status']} -> {args.report}")
    return 1 if new_violations else 0


if __name__ == "__main__":
    sys.exit(main())
