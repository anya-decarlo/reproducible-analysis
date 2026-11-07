#!/usr/bin/env python3
"""Step 3 — analyze: clean facts -> annual metrics + YoY growth tables.

Annual = duration 350-400 days; quarterly = 75-105 days. YoY computed
on consecutive annual periods. Values rounded to fixed precision so
outputs are byte-stable across platforms.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.common import ROOT, RunRecord, write_csv

FY_DAYS = (350, 400)


def read_facts(path: Path) -> list[dict]:
    with path.open() as fh:
        return list(csv.DictReader(fh))


def analyze(facts_path: Path, annual_out: Path, yoy_out: Path) -> dict:
    rows = read_facts(facts_path)
    annual = [
        r for r in rows
        if r["duration_days"] and FY_DAYS[0] <= int(r["duration_days"]) <= FY_DAYS[1]
    ]
    # latest-filed already applied in transform; group per period
    annual_rows = [
        {"entity": r["entity"], "metric": r["metric"], "unit": r["unit"],
         "fy_end": r["end"], "val": float(r["val"]),
         "form": r["form"], "filed": r["filed"], "accn": r["accn"]}
        for r in annual
    ]
    write_csv(annual_out, ["entity", "metric", "unit", "fy_end", "val",
                           "form", "filed", "accn"],
              annual_rows, ["entity", "metric", "fy_end"])

    by_key: dict[tuple, list[dict]] = {}
    for r in annual_rows:
        by_key.setdefault((r["entity"], r["metric"], r["unit"]), []).append(r)
    yoy_rows = []
    for (entity, metric, unit), rs in by_key.items():
        rs.sort(key=lambda r: r["fy_end"])
        for prev, cur in zip(rs, rs[1:]):
            if prev["val"]:
                yoy_rows.append({
                    "entity": entity, "metric": metric,
                    "fy_end": cur["fy_end"],
                    "prev_val": round(prev["val"], 2),
                    "val": round(cur["val"], 2),
                    "yoy_pct": round((cur["val"] - prev["val"])
                                     / abs(prev["val"]) * 100, 2),
                })
    write_csv(yoy_out, ["entity", "metric", "fy_end",
                        "prev_val", "val", "yoy_pct"],
              yoy_rows, ["entity", "metric", "fy_end"])
    return {"annual_rows": len(annual_rows), "yoy_rows": len(yoy_rows)}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--facts", type=Path,
                   default=ROOT / "outputs" / "facts_clean.csv")
    p.add_argument("--annual", type=Path,
                   default=ROOT / "outputs" / "annual_metrics.csv")
    p.add_argument("--yoy", type=Path,
                   default=ROOT / "outputs" / "yoy_growth.csv")
    args = p.parse_args()

    t0 = time.time()
    stats = analyze(args.facts, args.annual, args.yoy)
    RunRecord().record("analyze", [args.facts], [args.annual, args.yoy],
                       time.time() - t0, meta=stats)
    print(f"analyze: {stats['annual_rows']:,} annual + "
          f"{stats['yoy_rows']:,} yoy rows")


def main_cli() -> int:
    main()
    return 0


if __name__ == "__main__":
    main()
