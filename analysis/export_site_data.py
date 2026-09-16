"""Export the reviewed facility snapshot and compact model results for the site."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"


def number(value: str) -> float | None:
    return float(value) if value else None


def export_facilities() -> None:
    facilities = json.loads((ANALYSIS / "audited_facilities.json").read_text())
    payload = json.dumps(facilities, ensure_ascii=False, separators=(",", ":"))
    (ROOT / "data.js").write_text(f"window.FACILITIES_DATA = {payload};\n")


def export_model() -> None:
    with (ANALYSIS / "pipeline_scenarios.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    base_rows = [
        row
        for row in rows
        if row["missing_multiplier"] == "1.0"
        and row["time_multiplier"] == "1.0"
        and row["target_multiplier"] == "1.0"
        and row["county_shared"] == "False"
        and row["exclude_flagged"] == "False"
        and row["measure"]
        in {
            "operating_gw",
            "mw_per_1000_fixed_host_population",
            "operating_project_count",
            "intensity_ratio",
        }
    ]

    scenarios: dict[str, dict[str, dict[str, dict[str, float | None]]]] = {}
    for row in base_rows:
        scenario = scenarios.setdefault(row["political"], {})
        year = scenario.setdefault(row["year"], {})
        winner = year.setdefault(row["winner"], {})
        winner[row["measure"]] = {
            "p05": number(row["p05"]),
            "median": number(row["median"]),
            "p95": number(row["p95"]),
        }

    summary = json.loads((ANALYSIS / "model_summary.json").read_text())
    diagnostics = json.loads((ANALYSIS / "model_diagnostics.json").read_text())
    payload = {
        "as_of": summary["as_of"],
        "years": summary["years"],
        "reported_projects": summary["reported_projects"],
        "imputed_projects": summary["imputed_projects"],
        "unknown_total_gw": summary["unknown_total_gw_p05_median_p95"],
        "proposed_target_gw_per_location": summary[
            "proposed_target_gw_per_location_p05_median_p95"
        ],
        "scenarios": scenarios,
        "diagnostics": diagnostics,
        "assumptions": summary["assumptions"],
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    (ROOT / "model_data.js").write_text(f"window.PIPELINE_MODEL = {encoded};\n")


if __name__ == "__main__":
    export_facilities()
    export_model()
    print("Exported reviewed facilities and pipeline model data.")
