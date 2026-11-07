#!/usr/bin/env python3
"""Step 2 — transform: raw EDGAR JSON -> clean fact table.

Transformation rules (also documented in manifest.toml):
  T1  flatten companyfacts JSON to one row per fact
  T2  keep only focus metrics (tag -> canonical metric map below)
  T3  drop rows that cannot carry lineage (missing val/accn/filed/end)
  T4  drop malformed periods (end <= start)
  T5  dedupe: for (entity, tag, unit, period) keep the latest-filed
      fact — amendments and comparatives supersede originals
Output: outputs/facts_clean.csv — deterministic row order.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.common import ROOT, RunRecord, write_csv

TAG_TO_METRIC = {
    "Revenues": "revenue",
    "SalesRevenueNet": "revenue",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
    "RevenueFromContractWithCustomerIncludingAssessedTax": "revenue",
    "NetIncomeLoss": "net_income",
    "OperatingIncomeLoss": "operating_income",
    "Assets": "assets",
    "CashAndCashEquivalentsAtCarryingValue": "cash",
    "EarningsPerShareDiluted": "eps_diluted",
}

FIELDS = ["entity", "ticker", "cik", "tag", "metric", "unit", "val",
          "start", "end", "fy", "fp", "form", "filed", "accn",
          "duration_days"]


def duration_days(start: str | None, end: str | None) -> int | None:
    if not start or not end:
        return None
    from datetime import date
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def transform(raw_dir: Path, out_path: Path) -> dict:
    rows, dropped = [], {"no_lineage": 0, "bad_period": 0}
    for path in sorted(raw_dir.glob("CIK*_*.json")):
        payload = json.loads(path.read_text())
        ticker = path.stem.split("_")[-1]
        for tax, tags in payload.get("facts", {}).items():
            for tag, meta in tags.items():
                if tag not in TAG_TO_METRIC:
                    continue
                for unit, unit_rows in meta.get("units", {}).items():
                    for r in unit_rows:
                        if (r.get("val") is None or not r.get("accn")
                                or not r.get("filed") or not r.get("end")):
                            dropped["no_lineage"] += 1
                            continue
                        dd = duration_days(r.get("start"), r.get("end"))
                        if dd is not None and dd <= 0:
                            dropped["bad_period"] += 1
                            continue
                        rows.append({
                            "entity": payload["entityName"],
                            "ticker": ticker, "cik": payload["cik"],
                            "tag": tag, "metric": TAG_TO_METRIC[tag],
                            "unit": unit, "val": r["val"],
                            "start": r.get("start") or "",
                            "end": r["end"], "fy": r.get("fy") or "",
                            "fp": r.get("fp") or "",
                            "form": r.get("form") or "",
                            "filed": r["filed"], "accn": r["accn"],
                            "duration_days": dd if dd is not None else "",
                        })

    # T5: latest-filed wins per (entity, tag, unit, period)
    best: dict[tuple, dict] = {}
    for r in rows:
        key = (r["entity"], r["tag"], r["unit"], r["start"], r["end"])
        if key not in best or (r["filed"], r["accn"]) > (
                best[key]["filed"], best[key]["accn"]):
            best[key] = r
    deduped = len(rows) - len(best)

    write_csv(out_path, FIELDS, list(best.values()),
              sort_keys=["entity", "metric", "end", "start", "tag"])
    return {"rows_in": len(rows), "rows_out": len(best),
            "deduped": deduped, "dropped": dropped}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    p.add_argument("--out", type=Path,
                   default=ROOT / "outputs" / "facts_clean.csv")
    args = p.parse_args()

    t0 = time.time()
    stats = transform(args.raw_dir, args.out)
    inputs = sorted(args.raw_dir.glob("CIK*_*.json"))
    RunRecord().record("transform", inputs, [args.out], time.time() - t0,
                       meta=stats)
    print(f"transform: {stats['rows_in']:,} -> {stats['rows_out']:,} rows "
          f"({stats['deduped']:,} superseded, {sum(stats['dropped'].values()):,} "
          f"dropped) -> {args.out}")


if __name__ == "__main__":
    main()
