"""Reconcile the dashboard against fresh retained inputs without rewriting it.

Run from the repository root: python3 analysis/audit_numbers.py
Downloads are retained separately; --refresh fetches all three sources again.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import unicodedata
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis"
SOURCES = OUT / "sources"
URLS = {
    "projects.json": "https://www.brockovichdatacenter.com/data-centers-map.json",
    "election.html": "https://www.ballotwire.com/electiondatavisualizations/2024-presidential-election-county-level-results-map",
    "population.csv": "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/totals/co-est2024-alldata.csv",
    "independent_election.csv": "https://raw.githubusercontent.com/tonmcg/US_County_Level_Election_Results_08-24/master/2024_US_County_Level_Presidential_Results.csv",
    "mit_mirror.csv": "https://raw.githubusercontent.com/dlb8685/us_county_election_results/main/data/raw_data/mit_election_labs__countypres_2000-2024.csv",
}
STAGES = ["operational", "under_construction", "permitted", "proposed", "cancelled"]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def normal(value):
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().lower()
    value = re.sub(r" (city and borough|county|parish|borough|census area|municipality)$", "", value)
    return re.sub("[^a-z0-9]", "", value)


def fips(value):
    return str(value).zfill(5)


def total(rows, key):
    return sum(r.get(key) or 0 for r in rows)


def unique_counties(rows):
    return list({fips(r["matched_county_fips"]): r for r in rows}.values())


def weighted(rows, key, weight):
    denominator = sum(weight(r) for r in rows)
    return sum(weight(r) * r[key] for r in rows) / denominator if denominator else None


def summary(rows):
    counties = unique_counties(rows)
    pop = [r for r in counties if r.get("population_2024") is not None]
    known = [r for r in rows if r.get("mw") is not None]
    covered = [r for r in known if r.get("population_2024") is not None]
    groups = {}
    for winner in ["Trump", "Harris"]:
        projects = [r for r in rows if r["county_winner"] == winner]
        matched = [r for r in covered if r["county_winner"] == winner]
        capacity_counties = unique_counties(matched)
        denominator = total(capacity_counties, "population_2024")
        groups[winner] = {
            "projects": len(projects), "mw_known": sum(r.get("mw") is not None for r in projects),
            "reported_mw": total(projects, "mw"), "reported_investment": total(projects, "investment"),
            "investment_known": sum(r.get("investment") is not None for r in projects),
            "host_counties": len(unique_counties(projects)),
            "host_population": total(unique_counties(projects), "population_2024"),
            "capacity_counties": len(capacity_counties), "capacity_population": denominator,
            "population_matched_mw": total(matched, "mw"),
            "mw_per_1000": total(matched, "mw") / denominator * 1000 if denominator else None,
        }
    votes = total(counties, "total_votes")
    metrics = {
        "capacity_weighted": {k: weighted(known, k, lambda r: r["mw"]) for k in ["trump_pct", "harris_pct"]},
        "host_votes": {k: total(counties, v) / votes * 100 for k, v in [("trump_pct", "trump_votes"), ("harris_pct", "harris_votes")]},
        "population_weighted": {k: weighted(pop, k, lambda r: r["population_2024"]) for k in ["trump_pct", "harris_pct"]},
        "capacity_times_population": {k: weighted(covered, k, lambda r: r["mw"] * r["population_2024"]) for k in ["trump_pct", "harris_pct"]},
    }
    return {"projects": len(rows), "reported_mw": total(rows, "mw"), "reported_investment": total(rows, "investment"),
            "counties": len(counties), "population_counties": len(pop), "population": total(pop, "population_2024"),
            "votes": votes, "groups": groups, "weighting_cards": metrics}


def acquire(refresh=False):
    SOURCES.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for filename, url in URLS.items():
        path = SOURCES / filename
        if refresh or not path.exists():
            subprocess.run(["curl", "-L", "--fail", "--silent", "--show-error", "--max-time", "60",
                            url, "-o", str(path)], check=True)
            manifest[filename] = {"url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                                  "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    previous = SOURCES / "manifest.json"
    existing = json.loads(previous.read_text()) if previous.exists() else {}
    existing.update(manifest)
    write_json(previous, existing)


def audit():
    data = json.loads((ROOT / "facilities_data.json").read_text())
    source = json.loads((SOURCES / "projects.json").read_text())
    src = {r["id"]: r for r in source["fac"]}
    text = (SOURCES / "election.html").read_text()
    start = text.index("var RAW = ") + len("var RAW = ")
    # Embedded JSON in the page's escaped script. raw_decode bounds the actual object.
    election, _ = json.JSONDecoder().raw_decode(text[start:].replace(r'\"', '"').replace(r"\\", "\\"))
    elections = {}
    for r in election["counties"]:
        rep, dem, oth = r[3:6]
        elections[fips(r[0])] = {"rep": rep, "dem": dem, "total": r[6] if len(r) > 6 else rep + dem + oth,
                                 "name": r[1], "state": election["states"][r[2]][1]}
    with (SOURCES / "population.csv").open(encoding="latin1", newline="") as handle:
        population = {r["STATE"] + r["COUNTY"]: int(r["POPESTIMATE2024"]) for r in csv.DictReader(handle) if r["SUMLEV"] == "050"}
    raw_elections = {k: dict(v) for k, v in elections.items()}
    corrections = json.loads((OUT / "election_corrections.json").read_text())
    # Richmond City/County are reversed in the source. Neither is a selected host;
    # exclude both from alternative-location reassignment until independently fixed.
    names = {(r["state"], normal(r["name"])): (k, r) for k, r in elections.items() if k not in ("51159", "51760")}
    failures, disagreements = [], []
    source_fields = {"name": "n", "operator": "op", "status": "s", "state": "st", "county_raw": "co",
                     "county_geocoded": "jc", "city": "city", "lat": "lat", "lon": "lon", "mw": "mw",
                     "acres": "ac", "investment": "inv", "announced": "ann", "jurisdiction": "j"}
    for r in data:
        if r["id"] not in src:
            failures.append({"id": r["id"], "check": "missing_live_project"})
            continue
        for key, upstream in source_fields.items():
            if r.get(key) != src[r["id"]].get(upstream):
                failures.append({"id": r["id"], "check": "project_source", "field": key, "old": r.get(key), "fresh": src[r["id"]].get(upstream)})
        co = fips(r["matched_county_fips"])
        if r.get("population_2024") != population.get(co):
            failures.append({"id": r["id"], "check": "census_join"})
        if co in elections:
            for key, upstream in [("trump_votes", "rep"), ("harris_votes", "dem"), ("total_votes", "total")]:
                if r[key] != elections[co][upstream]:
                    failures.append({"id": r["id"], "check": "election_source", "field": key})
        for key, value in [("trump_pct", 100 * r["trump_votes"] / r["total_votes"]),
                           ("harris_pct", 100 * r["harris_votes"] / r["total_votes"]),
                           ("margin_pct", 100 * (r["trump_votes"] - r["harris_votes"]) / r["total_votes"])]:
            if not math.isclose(r[key], value, abs_tol=1e-9):
                failures.append({"id": r["id"], "check": key})
        winner = "Trump" if r["trump_votes"] >= r["harris_votes"] else "Harris"
        if r["county_winner"] != winner:
            failures.append({"id": r["id"], "check": "winner"})
        for key in ["mw", "investment", "population_2024", "acres"]:
            value = r.get(key)
            if value is not None and (not math.isfinite(value) or value <= 0):
                failures.append({"id": r["id"], "check": "nonpositive_or_nonfinite", "field": key})
        if r.get("county_geocoded") and normal(r["county_geocoded"]) != normal(r["matched_county_name"]):
            alt = names.get((r["state"], normal(r["county_geocoded"])))
            disagreements.append({"id": r["id"], "state": r["state"], "selected": r["matched_county_name"],
                "alternate": r["county_geocoded"], "mw": r["mw"], "winner": r["county_winner"],
                "alternate_fips": alt[0] if alt else None,
                "alternate_winner": ("Trump" if alt[1]["rep"] >= alt[1]["dem"] else "Harris") if alt else None})
    for key in ["population_2024", "county_winner", "trump_votes", "harris_votes", "total_votes"]:
        by_county = defaultdict(set)
        for r in data:
            by_county[fips(r["matched_county_fips"])].add(r[key])
        for co, values in by_county.items():
            if len(values) > 1:
                failures.append({"county": co, "check": "inconsistent_county", "field": key})
    ids = Counter(r["id"] for r in data)
    duplicates = {k: v for k, v in ids.items() if v > 1}
    served = (ROOT / "data.js").read_text().removeprefix("window.FACILITIES_DATA = ").strip().removesuffix(";")
    if json.loads(served) != data:
        failures.append({"check": "served_json_differs"})
    with (ROOT / "data_centres_with_2024_election_results.csv").open(newline="") as handle:
        exported = {r["id"]: r for r in csv.DictReader(handle)}
    csv_mismatches = []
    for r in data:
        for key, value in r.items():
            if key in ("population_2024", "population_source"):
                continue
            cell = exported.get(r["id"], {}).get(key)
            same = cell == "" if value is None else (math.isclose(float(cell), value, abs_tol=1e-9) if isinstance(value, (int, float)) else cell == value)
            if not same:
                csv_mismatches.append({"id": r["id"], "field": key})
    scopes = {"all": summary(data)}
    scopes.update({stage: summary([r for r in data if r["status"] == stage]) for stage in STAGES})
    scopes["active"] = summary([r for r in data if r["status"] != "cancelled"])
    scopes["pipeline"] = summary([r for r in data if r["status"] in ("proposed", "permitted", "under_construction")])
    flags = []
    for r in data:
        s = src[r["id"]]
        reasons = []
        if s["cf"] == "rumored": reasons.append("rumored")
        if re.search(r"full.build|ultimate|phase|target|up to|generation|power plant", s.get("nt", ""), re.I):
            reasons.append("capacity_or_phase_language_requires_review")
        if r["mw"] is not None and r["mw"] >= 2000: reasons.append("at_least_2_GW")
        if reasons:
            flags.append({"id": r["id"], "name": r["name"], "mw": r["mw"], "status": r["status"], "winner": r["county_winner"],
                          "flags": reasons, "notes": s.get("nt"), "sources": s["src"]})
    # An alternate geography is a sensitivity experiment, never an automatic correction.
    alternate_data = [dict(r) for r in data]
    alt_map = {r["id"]: r["alternate_fips"] for r in disagreements if r["alternate_fips"]}
    for r in alternate_data:
        if r["id"] in alt_map:
            co = alt_map[r["id"]]; e = elections[co]
            r.update(matched_county_fips=co, matched_county_name=e["name"], population_2024=population.get(co),
                     trump_votes=e["rep"], harris_votes=e["dem"], total_votes=e["total"],
                     trump_pct=100*e["rep"]/e["total"], harris_pct=100*e["dem"]/e["total"],
                     county_winner="Trump" if e["rep"] >= e["dem"] else "Harris")
    report = {"executed_at": datetime.now(timezone.utc).isoformat(), "source_meta": source["meta"],
              "added_ids": sorted(src.keys() - ids.keys()), "removed_ids": sorted(ids.keys() - src.keys()),
              "failures": failures, "duplicate_ids": duplicates, "csv_mismatches": csv_mismatches,
              "election_not_independently_matched": [r["id"] for r in data if fips(r["matched_county_fips"]) not in elections],
              "population_unmatched": [r["id"] for r in data if r["population_2024"] is None],
              "geography_disagreements": disagreements,
              "geography_alternative_sensitivity": summary(alternate_data), "scopes": scopes,
              "source_confidence": dict(Counter(r["cf"] for r in source["fac"])),
              "source_actual_jurisdictions": dict(Counter(r["j"] for r in source["fac"])),
              "capacity_review_queue": sorted(flags, key=lambda r: r["mw"] or 0, reverse=True)}
    with (SOURCES / "independent_election.csv").open(newline="") as handle:
        independent = {r["county_fips"]: r for r in csv.DictReader(handle)}
    differences = []
    for r in unique_counties(data):
        independent_row = independent.get(fips(r["matched_county_fips"]))
        if independent_row:
            rep, dem, votes = (int(independent_row[k]) for k in ["votes_gop", "votes_dem", "total_votes"])
            differences.append({"fips": fips(r["matched_county_fips"]), "county": r["matched_county_name"],
                "state": r["state"], "old_trump_pct": r["trump_pct"], "independent_trump_pct": 100*rep/votes,
                "old_votes": r["total_votes"], "independent_votes": votes,
                "winner_agrees": (rep >= dem) == (r["county_winner"] == "Trump")})
    report["independent_election_comparison"] = differences
    report["independent_election_limit"] = "McGovern/Fox compilation checks 302/304 hosts; it is an independent cross-check, not certified final returns. North Slope and old New London geography are absent."
    # Check every election-source county against population, not just the host sample.
    report["election_population_anomalies"] = [{"fips": co, "county": r["name"], "state": r["state"],
            "votes": r["total"], "population": population[co]} for co,r in raw_elections.items()
            if co in population and (r["total"] > population[co] or r["total"] < .07*population[co])]
    corrected = [dict(r) for r in data]
    for r in corrected:
        c = corrections.get(fips(r["matched_county_fips"]))
        if c:
            for key in ["trump_votes", "harris_votes", "total_votes"]:
                r[key] = c[key]
            r["trump_pct"] = 100*r["trump_votes"]/r["total_votes"]
            r["harris_pct"] = 100*r["harris_votes"]/r["total_votes"]
            r["margin_pct"] = r["trump_pct"]-r["harris_pct"]
            r["county_winner"] = "Trump" if r["trump_votes"] >= r["harris_votes"] else "Harris"
            r["election_correction_source"] = c["source"]
    report["confirmed_election_corrections"] = corrections
    report["corrected_scopes"] = {"all": summary(corrected), **{s: summary([r for r in corrected if r["status"] == s]) for s in STAGES}}
    report["corrected_scopes"]["active"] = summary([r for r in corrected if r["status"] != "cancelled"])
    report["corrected_scopes"]["pipeline"] = summary([r for r in corrected if r["status"] in ("proposed", "permitted", "under_construction")])
    report["corrected_projects"] = [r["id"] for r in corrected if "election_correction_source" in r]
    report["source_issues"] = ["Three host-county election records corrected from official returns; four projects affected.",
        "Twenty project location fields disagree, including old Connecticut geography; no automatic geographic correction.",
        "Manual North Slope election tallies remain unverified.",
        "MW mixes phases, full-buildout targets and generation capacities; 214 values are missing.",
        "The older MIT mirror has its own FIPS, jurisdiction, and tally issues and was not substituted wholesale."]
    write_json(OUT / "audited_facilities.json", corrected)
    write_json(OUT / "audit_results.json", report)
    write_json(OUT / "geography_review.json", disagreements)
    print(json.dumps({k: report[k] for k in ["failures", "duplicate_ids", "csv_mismatches", "source_meta"]}, indent=2))
    print(json.dumps(scopes["all"], indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    acquire(args.refresh)
    audit()
