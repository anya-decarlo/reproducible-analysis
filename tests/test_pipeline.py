"""Pipeline tests: determinism, transform rules, validation gates."""

import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import analyze, transform, validate


def write_payload(raw: Path, cik=9999999, ticker="ACME", extra_rev=None):
    f = lambda s, e, v, fy, fp, form, filed, accn: {
        "start": s, "end": e, "val": v, "fy": fy, "fp": fp,
        "form": form, "filed": filed, "accn": accn,
    }
    rev = [
        f("2023-01-01", "2023-03-31", 240, 2023, "Q1", "10-Q", "2023-04-28", "q1"),
        f("2023-04-01", "2023-06-30", 250, 2023, "Q2", "10-Q", "2023-07-28", "q2"),
        f("2023-07-01", "2023-09-30", 260, 2023, "Q3", "10-Q", "2023-10-27", "q3"),
        f("2023-10-01", "2023-12-31", 250, 2023, "Q4", "10-K", "2024-02-16", "k23"),
        f("2023-01-01", "2023-12-31", 1000, 2023, "FY", "10-K", "2024-02-16", "k23"),
    ] + (extra_rev or [])
    payload = {"cik": cik, "entityName": "Acme",
               "facts": {"us-gaap": {
                   "Revenues": {"label": "Rev", "units": {"USD": rev}}}}}
    path = raw / f"CIK{cik:010d}_{ticker}.json"
    path.write_text(json.dumps(payload))
    return path


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raw = Path(self.tmp.name) / "raw"
        self.raw.mkdir()
        write_payload(self.raw)
        self.clean = Path(self.tmp.name) / "facts_clean.csv"

    def test_transform_rules(self):
        transform.transform(self.raw, self.clean)
        rows = list(__import__("csv").DictReader(self.clean.open()))
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(r["metric"] == "revenue" for r in rows))

    def test_determinism(self):
        a, b = (Path(self.tmp.name) / x for x in ("a.csv", "b.csv"))
        transform.transform(self.raw, a)
        transform.transform(self.raw, b)
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_validation_passes_clean_data(self):
        transform.transform(self.raw, self.clean)
        report, n = validate.validate(
            self.clean, Path(self.tmp.name) / "report.json")
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(n, 0)

    def test_validation_catches_planted_defect(self):
        # Q4 changed so quarters no longer tie to the annual figure
        write_payload(self.raw, extra_rev=[{
            "start": "2024-01-01", "end": "2024-12-31", "val": -5,
            "fy": 2024, "fp": "FY", "form": "10-K",
            "filed": "2025-02-01", "accn": "k24"}])
        transform.transform(self.raw, self.clean)
        report, n = validate.validate(
            self.clean, Path(self.tmp.name) / "report.json")
        self.assertEqual(report["status"], "FAIL")
        self.assertGreater(
            report["checks"]["impossible_negatives"]["violations_new"], 0)

    def test_baseline_suppresses_known_violation(self):
        write_payload(self.raw, extra_rev=[{
            "start": "2024-01-01", "end": "2024-12-31", "val": -5,
            "fy": 2024, "fp": "FY", "form": "10-K",
            "filed": "2025-02-01", "accn": "k24"}])
        transform.transform(self.raw, self.clean)
        # violation dicts carry entity/metric/end/val — baseline entries
        # must mirror exactly those keys (plus a 'reason')
        baseline = Path(self.tmp.name) / "baseline.json"
        baseline.write_text(json.dumps({"impossible_negatives": [{
            "entity": "Acme", "metric": "revenue", "end": "2024-12-31",
            "val": "-5", "reason": "documented"}]}))
        report, n = validate.validate(
            self.clean, Path(self.tmp.name) / "r.json", baseline)
        self.assertEqual(report["status"], "PASS")

    def test_analyze_outputs(self):
        transform.transform(self.raw, self.clean)
        annual = Path(self.tmp.name) / "annual.csv"
        yoy = Path(self.tmp.name) / "yoy.csv"
        analyze.analyze(self.clean, annual, yoy)
        rows = list(__import__("csv").DictReader(annual.open()))
        self.assertEqual(len(rows), 1)
        self.assertEqual(float(rows[0]["val"]), 1000)


if __name__ == "__main__":
    unittest.main()
