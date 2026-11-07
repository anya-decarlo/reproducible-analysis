"""Shared helpers: hashing, run records, deterministic writers.

Every pipeline step records what it read and wrote (sha256) into
build/run.json. That record is the answer to "what exactly produced
this number?" and it is what verify.py replays.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, timeout=5,
        ).stdout.strip() or "nogit"
    except Exception:
        return "nogit"


def python_version() -> str:
    import platform
    return f"{platform.python_implementation()} {platform.python_version()}"


class RunRecord:
    """Appends a step entry to build/run.json."""

    def __init__(self, build_dir: Path = BUILD):
        self.path = build_dir / "run.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.data = json.loads(self.path.read_text())
        else:
            self.data = {"git_sha": git_sha(),
                         "python": python_version(), "steps": []}

    def record(self, step: str, inputs: list[Path], outputs: list[Path],
               elapsed: float, meta: dict | None = None) -> None:
        self.data["steps"].append({
            "step": step,
            "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                         time.gmtime()),
            "elapsed_s": round(elapsed, 3),
            "inputs": {p.name: sha256(p) for p in inputs if p.exists()},
            "outputs": {p.name: sha256(p) for p in outputs if p.exists()},
            "meta": meta or {},
        })
        self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict],
              sort_keys: list[str]) -> None:
    """Deterministic CSV: fixed column order, sorted rows, LF endings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: tuple(str(r[k]) for k in sort_keys))
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
