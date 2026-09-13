import pandas as pd
import numpy as np

# Load datasets
df = pd.read_csv("data_centres_with_2024_election_results.csv")
unique_counties = pd.read_csv("data_centre_counties_summary.csv")
all_counties = pd.read_csv("all_us_counties_2024_election.csv")

print("================================================================================")
print("             AI DATA CENTRES vs. 2024 PRESIDENTIAL ELECTION RESULTS            ")
print("================================================================================")

# 1. High-Level Summary
total_fac = len(df)
trump_fac = (df["county_winner"] == "Trump").sum()
harris_fac = (df["county_winner"] == "Harris").sum()

total_mw = df["mw"].sum()
trump_mw = df[df["county_winner"] == "Trump"]["mw"].sum()
harris_mw = df[df["county_winner"] == "Harris"]["mw"].sum()

print("\n--- 1. OVERALL FACILITY & CAPACITY BREAKDOWN ---")
print(f"Total AI Data Centers Analyzed: {total_fac}")
print(f"  • In Trump-won Counties:  {trump_fac:3d} ({trump_fac/total_fac*100:5.1f}%)")
print(f"  • In Harris-won Counties: {harris_fac:3d} ({harris_fac/total_fac*100:5.1f}%)")
print(f"\nTotal Power Capacity Tracked: {total_mw:,.0f} MW (reported for {df['mw'].notna().sum()} facilities)")
print(f"  • In Trump-won Counties:  {trump_mw:,.0f} MW ({trump_mw/total_mw*100:5.1f}%)")
print(f"  • In Harris-won Counties: {harris_mw:,.0f} MW ({harris_mw/total_mw*100:5.1f}%)")

print("\n--- 2. TRUMP VOTE SHARE METRICS ---")
print(f"Mean Trump % across all 474 data center locations:   {df['trump_pct'].mean():.2f}%")
print(f"Median Trump % across all 474 data center locations: {df['trump_pct'].median():.2f}%")
print(f"Capacity-weighted Trump % (by reported MW):          {(df['trump_pct'] * df['mw']).sum() / df['mw'].sum():.2f}%")

print("\nBenchmark: National County Averages (Ballotwire 2024)")
print(f"  • All US Counties (unweighted mean):               {all_counties['trump_pct'].mean():.2f}%")
print(f"  • All US Counties (median):                        {all_counties['trump_pct'].median():.2f}%")
print(f"  • Counties won by Trump nationwide:                {(all_counties['winner'] == 'Trump').sum()} / {len(all_counties)} ({(all_counties['winner'] == 'Trump').mean()*100:.1f}%)")
national_trump_popular_vote = all_counties['rep'].sum() / all_counties['total'].sum() * 100
print(f"  • National popular vote Trump %:                   {national_trump_popular_vote:.2f}%")

# 2. Unique Counties Hosting Data Centers
print("\n--- 3. UNIQUE HOST COUNTIES COMPARISON ---")
n_unique = len(unique_counties)
trump_host_counties = (unique_counties["county_winner"] == "Trump").sum()
harris_host_counties = (unique_counties["county_winner"] == "Harris").sum()
print(f"Total Unique Counties Hosting Data Centers: {n_unique} (out of {len(all_counties)} US counties)")
print(f"  • Trump-won Host Counties:  {trump_host_counties} ({trump_host_counties/n_unique*100:.1f}%)")
print(f"  • Harris-won Host Counties: {harris_host_counties} ({harris_host_counties/n_unique*100:.1f}%)")
print(f"Mean Trump % across unique host counties:   {unique_counties['trump_pct'].mean():.2f}%")
print(f"Median Trump % across unique host counties: {unique_counties['trump_pct'].median():.2f}%")

# 3. Vote Share Tiers / Buckets
print("\n--- 4. FACILITY DISTRIBUTION ACROSS POLITICAL TIERS ---")
bins = [0, 35, 50, 65, 100]
labels = [
    "Strong Harris (Trump <35%)",
    "Moderate/Lean Harris (Trump 35-50%)",
    "Moderate/Lean Trump (Trump 50-65%)",
    "Strong Trump (Trump >65%)"
]
df["tier"] = pd.cut(df["trump_pct"], bins=bins, labels=labels)
tier_summary = df.groupby("tier", observed=False).agg(
    facilities=("id", "count"),
    reported_mw=("mw", "sum"),
    mean_mw=("mw", "mean")
)
tier_summary["facility_pct"] = tier_summary["facilities"] / total_fac * 100
tier_summary["mw_pct"] = tier_summary["reported_mw"] / total_mw * 100
print(tier_summary[["facilities", "facility_pct", "reported_mw", "mw_pct", "mean_mw"]].to_string())

# 4. Status Breakdown
print("\n--- 5. STATUS BREAKDOWN BY POLITICAL CONTROL ---")
status_order = ["operational", "under_construction", "permitted", "proposed", "cancelled"]
st_df = df.groupby(["status", "county_winner"]).size().unstack(fill_value=0)
st_df["total"] = st_df["Trump"] + st_df["Harris"]
st_df["trump_pct_of_facs"] = (st_df["Trump"] / st_df["total"] * 100).round(1)
st_df["mean_trump_vote"] = df.groupby("status")["trump_pct"].mean().round(1)
st_df["total_mw"] = df.groupby("status")["mw"].sum()
st_df["trump_mw"] = df[df["county_winner"] == "Trump"].groupby("status")["mw"].sum()
st_df["trump_mw_pct"] = (st_df["trump_mw"] / st_df["total_mw"] * 100).round(1)
print(st_df.loc[status_order].to_string())

# 5. Top States for Data Centers
print("\n--- 6. TOP STATES FOR AI DATA CENTERS ---")
state_summary = df.groupby("state").agg(
    facility_count=("id", "count"),
    trump_facs=("county_winner", lambda x: (x == "Trump").sum()),
    harris_facs=("county_winner", lambda x: (x == "Harris").sum()),
    total_mw=("mw", "sum"),
    mean_county_trump_pct=("trump_pct", "mean")
).sort_values(by="facility_count", ascending=False).head(12)
state_summary["trump_fac_pct"] = (state_summary["trump_facs"] / state_summary["facility_count"] * 100).round(1)
print(state_summary.to_string())

# 6. Top Counties by Number of Data Centers
print("\n--- 7. TOP COUNTIES BY NUMBER OF DATA CENTERS ---")
top_counties = unique_counties.sort_values(by="facility_count", ascending=False).head(15)
print(top_counties[["matched_county_name", "matched_state", "facility_count", "total_mw", "trump_pct", "county_winner"]].to_string(index=False))

# 7. Major Operators
print("\n--- 8. MAJOR TECH OPERATORS & HYPERSCALERS ---")
# Identify key operators
def categorize_operator(op):
    if not isinstance(op, str): return "Other / Co-location / Energy"
    op_l = op.lower()
    if "amazon" in op_l or "aws" in op_l: return "Amazon / AWS"
    if "microsoft" in op_l: return "Microsoft"
    if "google" in op_l or "alphabet" in op_l: return "Google"
    if "meta" in op_l or "facebook" in op_l: return "Meta"
    if "xai" in op_l or "elon" in op_l: return "xAI"
    if "apple" in op_l: return "Apple"
    if "vantage" in op_l: return "Vantage Data Centers"
    if "qts" in op_l: return "QTS"
    if "cyrusone" in op_l: return "CyrusOne"
    if "digital realty" in op_l: return "Digital Realty"
    if "compass" in op_l: return "Compass Datacenters"
    if "stack" in op_l: return "Stack Infrastructure"
    return "Other / Utility / Developer"

df["operator_category"] = df["operator"].apply(categorize_operator)
op_summary = df.groupby("operator_category").agg(
    facility_count=("id", "count"),
    trump_facs=("county_winner", lambda x: (x == "Trump").sum()),
    harris_facs=("county_winner", lambda x: (x == "Harris").sum()),
    total_mw=("mw", "sum"),
    mean_county_trump_pct=("trump_pct", "mean")
).sort_values(by="facility_count", ascending=False)
op_summary["trump_pct_of_facs"] = (op_summary["trump_facs"] / op_summary["facility_count"] * 100).round(1)
print(op_summary.to_string())
