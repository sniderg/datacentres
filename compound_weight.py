import pandas as pd

df = pd.read_csv("data_centres_with_2024_election_results.csv")
all_c = pd.read_csv("all_us_counties_2024_election.csv", dtype={"fips": str})
df_mw = df.dropna(subset=["mw"]).copy()

# Compound metric: MW * Votes
df_mw["mw_x_trump_votes"] = df_mw["mw"] * df_mw["trump_votes"]
df_mw["mw_x_harris_votes"] = df_mw["mw"] * df_mw["harris_votes"]
df_mw["mw_x_total_votes"] = df_mw["mw"] * df_mw["total_votes"]

total_mw_votes = df_mw["mw_x_total_votes"].sum()
df_mw["pct_of_compound_weight"] = df_mw["mw_x_total_votes"] / total_mw_votes * 100

trump_pct_val = df_mw["mw_x_trump_votes"].sum() / total_mw_votes * 100
harris_pct_val = df_mw["mw_x_harris_votes"].sum() / total_mw_votes * 100

print(f"Total MW * Votes nationally: {total_mw_votes:,.0f}")
print(f"Compound (MW x Votes) Trump %:  {trump_pct_val:.2f}%")
print(f"Compound (MW x Votes) Harris %: {harris_pct_val:.2f}%")
print(f"Net Margin: {trump_pct_val - harris_pct_val:+.2f}%")

print("\n--- TOP 10 FACILITIES BY (MW x VOTES) COMPOUND WEIGHT ---")
top_compound = df_mw.sort_values(by="mw_x_total_votes", ascending=False).head(10)
for idx, r in top_compound.iterrows():
    name = r["name"]
    co = r["matched_county_name"]
    st = r["state"]
    mw = r["mw"]
    votes = r["total_votes"]
    t_pct = r["trump_pct"]
    share = r["pct_of_compound_weight"]
    print(f"{name[:35]:35s} | {co}, {st:2s} | {mw:6,.0f} MW | {votes:9,d} voters | Trump: {t_pct:5.1f}% | Weight: {share:5.2f}%")

print("\n--- RURAL GIGAWATT SITES VS URBAN/METRO SITES ---")
sample_sites = [
    "Creekstone Energy Delta Gigasite",
    "Stratos AI Data Center Campus",
    "Buckeye Tech Corridor",
    "Project Cannoli",
    "Homer City Energy Campus"
]
for s in sample_sites:
    matches = df_mw[df_mw["name"] == s]
    if len(matches) > 0:
        row = matches.iloc[0]
        name = row["name"]
        co = row["matched_county_name"]
        st = row["state"]
        mw = row["mw"]
        votes = row["total_votes"]
        t_pct = row["trump_pct"]
        mw_votes = row["mw_x_total_votes"]
        share = row["pct_of_compound_weight"]
        print(f"{name} ({co}, {st}):")
        print(f"   Capacity: {mw:,.0f} MW | Voters: {votes:,} | Trump: {t_pct:.1f}%")
        print(f"   MW x Votes: {mw_votes:,.0f} ({share:.2f}% of national total)\n")
