#!/usr/bin/env python3
"""Step 1 — ingest: fetch companyfacts and record provenance.

Each raw file gets an entry in data/manifest.json: sha256, byte size,
source URL (or local origin), fetch timestamp. Re-running against an
existing cache records `cached: true` and never refetches, so builds are
offline-reproducible once inputs exist.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.common import ROOT, RunRecord, sha256, write_json

DEFAULT_TICKERS = ["AAPL", "MSFT", "TSLA"]
USER_AGENT = "reproducible-analysis contact@example.com"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _ticker_to_cik(ticker: str, raw_dir: Path) -> int:
    cache = raw_dir / "company_tickers.json"
    mapping = json.loads(cache.read_text()) if cache.exists() else None
    if mapping is None:
        mapping = _get(TICKERS_URL)
        cache.write_text(json.dumps(mapping))
    for row in mapping.values():
        if row["ticker"].upper() == ticker.upper():
            return int(row["cik_str"])
    raise KeyError(ticker)


def ingest(tickers: list[str], raw_dir: Path, copy_from: Path | None = None
           ) -> dict:
    raw_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for t in tickers:
        # find or fetch the payload
        candidates = list(raw_dir.glob(f"CIK*_{t.upper()}.json"))
        if candidates:
            path, cached, source = candidates[0], True, "cache"
        elif copy_from and (matches := list(copy_from.glob(f"CIK*_{t.upper()}.json"))):
            path = raw_dir / matches[0].name
            path.write_bytes(matches[0].read_bytes())
            cached, source = False, str(matches[0])
        else:
            cik = _ticker_to_cik(t, raw_dir)
            url = FACTS_URL.format(cik=cik)
            path = raw_dir / f"CIK{cik:010d}_{t.upper()}.json"
            time.sleep(0.2)
            path.write_text(json.dumps(_get(url)))
            cached, source = False, url
        entries.append({
            "file": path.name, "ticker": t.upper(), "sha256": sha256(path),
            "bytes": path.stat().st_size, "source": source, "cached": cached,
        })
        print(f"  {t}: {path.name} ({entries[-1]['sha256'][:12]}…, {source})")
    return {"inputs": entries}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    p.add_argument("--copy-from", type=Path, default=None,
                   help="reuse payloads from another repo's cache")
    args = p.parse_args()
    raw_dir = ROOT / "data" / "raw"

    t0 = time.time()
    manifest = ingest(args.tickers, raw_dir, args.copy_from)
    manifest_path = ROOT / "data" / "manifest.json"
    write_json(manifest_path, manifest)
    files = [raw_dir / e["file"] for e in manifest["inputs"]]
    RunRecord().record("ingest", files, [manifest_path], time.time() - t0)
    print(f"manifest -> {manifest_path}")


if __name__ == "__main__":
    main()
