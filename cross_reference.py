import urllib.request
import json
import pandas as pd
import numpy as np

def run_cross_reference():
    # 1. Fetch Brockovich data
    print("Fetching Brockovich data...")
    req = urllib.request.Request("https://www.brockovichdatacenter.com/data-centers-map.json", headers={"User-Agent": "Mozilla/5.0"})
    dc_data = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
    facs = dc_data["fac"]

    # 2. Fetch Ballotwire data
    print("Fetching Ballotwire 2024 presidential county data...")
    html = urllib.request.urlopen("https://www.ballotwire.com/electiondatavisualizations/2024-presidential-election-county-level-results-map").read().decode("utf-8")
    target = "var RAW = "
    idx = html.find(target)
    start = idx + len(target)
    end = html.find(";\\n", start)
    s = html[start:end].replace(r"\"", "\"").replace(r"\\", "\\")
    bw_data = json.loads(s)

    states = {i: {"name": s[0], "ab": s[1]} for i, s in enumerate(bw_data["states"])}
    counties = []
    for r in bw_data["counties"]:
        rep = r[3]
        dem = r[4]
        oth = r[5]
        total = r[6] if len(r) > 6 else (rep + dem + oth)
        st_ab = states[r[2]]["ab"]
        st_name = states[r[2]]["name"]
        counties.append({
            "fips": r[0],
            "name": r[1],
            "state_ab": st_ab,
            "state_name": st_name,
            "rep": rep,
            "dem": dem,
            "oth": oth,
            "total": total,
            "trump_pct": (rep / total * 100) if total else 0,
            "harris_pct": (dem / total * 100) if total else 0,
            "margin_pct": ((rep - dem) / total * 100) if total else 0,
            "winner": "Trump" if rep >= dem else "Harris"
        })

    # Add North Slope Borough, AK from official 2024 election certification
    counties.append({
        "fips": "02185",
        "name": "North Slope Borough",
        "state_ab": "AK",
        "state_name": "Alaska",
        "rep": 939,
        "dem": 690,
        "oth": 101,
        "total": 1730,
        "trump_pct": 939 / 1730 * 100,
        "harris_pct": 690 / 1730 * 100,
        "margin_pct": (939 - 690) / 1730 * 100,
        "winner": "Trump"
    })

    def norm(name):
        if not name: return ""
        name = name.lower()
        for suffix in [" county", " parish", " borough", " census area", " municipality", " city and borough"]:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        name = "".join(c for c in name if c.isalnum() or c.isspace()).strip()
        return name

    county_map = {}
    for c in counties:
        st = c["state_ab"]
        county_map[(st, norm(c["name"]))] = c
        county_map[(st, c["name"].lower().strip())] = c

    matched_records = []
    for f in facs:
        st = f.get("st")
        co = f.get("co")
        jc = f.get("jc")
        city = f.get("city")
        
        match = None
        for cand in [co, jc, city]:
            if not cand: continue
            k = (st, norm(cand))
            if k in county_map:
                match = county_map[k]
                break
            k_full = (st, cand.lower().strip())
            if k_full in county_map:
                match = county_map[k_full]
                break
                
        rec = {
            "id": f.get("id"),
            "name": f.get("n"),
            "operator": f.get("op"),
            "status": f.get("s"),
            "state": st,
            "county_raw": co,
            "county_geocoded": jc,
            "city": city,
            "lat": f.get("lat"),
            "lon": f.get("lon"),
            "mw": f.get("mw"),
            "acres": f.get("ac"),
            "investment": f.get("inv"),
            "announced": f.get("ann"),
            "jurisdiction": f.get("j"),
            "matched_county_fips": match["fips"] if match else None,
            "matched_county_name": match["name"] if match else None,
            "matched_state": match["state_ab"] if match else None,
            "trump_votes": match["rep"] if match else None,
            "harris_votes": match["dem"] if match else None,
            "total_votes": match["total"] if match else None,
            "trump_pct": match["trump_pct"] if match else None,
            "harris_pct": match["harris_pct"] if match else None,
            "margin_pct": match["margin_pct"] if match else None,
            "county_winner": match["winner"] if match else None
        }
        matched_records.append(rec)

    df = pd.DataFrame(matched_records)
    print(f"Total facilities matched: {len(df)} (Unmatched: {df['trump_pct'].isna().sum()})")

    # Save outputs
    df.to_csv("data_centres_with_2024_election_results.csv", index=False)

    unique_counties = df.groupby(["matched_county_fips", "matched_county_name", "matched_state"]).agg(
        trump_pct=("trump_pct", "first"),
        county_winner=("county_winner", "first"),
        total_votes=("total_votes", "first"),
        facility_count=("id", "count"),
        total_mw=("mw", "sum")
    ).reset_index()
    unique_counties.to_csv("data_centre_counties_summary.csv", index=False)

    all_counties_df = pd.DataFrame(counties)
    all_counties_df.to_csv("all_us_counties_2024_election.csv", index=False)

    print("CSVs written successfully.")
    return df, unique_counties, all_counties_df

if __name__ == "__main__":
    run_cross_reference()
