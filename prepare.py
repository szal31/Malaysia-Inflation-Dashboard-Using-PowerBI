"""Turn the OpenDOSM CPI files into a star schema for Power BI and print headline findings.

Inputs (data/raw/, from https://storage.dosm.gov.my/cpi/):
  cpi_2d_state.csv, cpi_2d_state_inflation.csv, cpi_2d.csv, cpi_2d_inflation.csv
Outputs (data/clean/): fact_cpi.csv, dim_state.csv, dim_division.csv

Usage:  python prepare.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "clean"
START = "2010-01-01"  # state series begin here

DIVISIONS = {
    "overall": "Overall",
    "01": "Food & Non-Alcoholic Beverages",
    "02": "Alcoholic Beverages & Tobacco",
    "03": "Clothing & Footwear",
    "04": "Housing, Water, Electricity & Gas",
    "05": "Furnishings & Household Maintenance",
    "06": "Health",
    "07": "Transport",
    "08": "Information & Communication",
    "09": "Recreation, Sport & Culture",
    "10": "Education",
    "11": "Restaurants & Accommodation",
    "12": "Insurance & Financial Services",
    "13": "Personal Care & Misc.",
}

# region, plus a name the Power BI map can geocode
STATES = {
    "Johor": ("Southern", "Johor, Malaysia"),
    "Kedah": ("Northern", "Kedah, Malaysia"),
    "Kelantan": ("East Coast", "Kelantan, Malaysia"),
    "Melaka": ("Southern", "Melaka, Malaysia"),
    "Negeri Sembilan": ("Southern", "Negeri Sembilan, Malaysia"),
    "Pahang": ("East Coast", "Pahang, Malaysia"),
    "Perak": ("Northern", "Perak, Malaysia"),
    "Perlis": ("Northern", "Perlis, Malaysia"),
    "Pulau Pinang": ("Northern", "Penang, Malaysia"),
    "Sabah": ("East Malaysia", "Sabah, Malaysia"),
    "Sarawak": ("East Malaysia", "Sarawak, Malaysia"),
    "Selangor": ("Central", "Selangor, Malaysia"),
    "Terengganu": ("East Coast", "Terengganu, Malaysia"),
    "W.P. Kuala Lumpur": ("Central", "Kuala Lumpur, Malaysia"),
    "W.P. Labuan": ("East Malaysia", "Labuan, Malaysia"),
    "W.P. Putrajaya": ("Central", "Putrajaya, Malaysia"),
}


def load(index_file, infl_file, state=None):
    idx = pd.read_csv(RAW / index_file)
    infl = pd.read_csv(RAW / infl_file)
    keys = ["date", "division"] if state else ["state", "date", "division"]
    df = idx.merge(infl, on=keys, how="left")
    if state:
        df.insert(0, "state", state)
    return df[df["date"] >= START]


def main():
    CLEAN.mkdir(exist_ok=True)
    fact = pd.concat([
        load("cpi_2d_state.csv", "cpi_2d_state_inflation.csv"),
        load("cpi_2d.csv", "cpi_2d_inflation.csv", state="Malaysia"),
    ], ignore_index=True)
    fact = fact.rename(columns={"division": "division_code", "index": "cpi_index"})

    # Self-checks: no unknown codes, one row per key, DOSM's YoY matches the index within rounding.
    assert set(fact["division_code"]) <= set(DIVISIONS), set(fact["division_code"]) - set(DIVISIONS)
    assert set(fact["state"]) == set(STATES) | {"Malaysia"}
    assert not fact.duplicated(["state", "date", "division_code"]).any()
    f = fact.sort_values("date").copy()
    f["calc_yoy"] = f.groupby(["state", "division_code"])["cpi_index"].pct_change(12) * 100
    gap = (f["calc_yoy"] - f["inflation_yoy"]).abs().dropna()
    assert gap.quantile(0.99) < 0.3, gap.describe()  # index is rounded to 1 dp, so allow small drift

    fact.to_csv(CLEAN / "fact_cpi.csv", index=False)
    pd.DataFrame(
        [(s, r, g, True) for s, (r, g) in STATES.items()] + [("Malaysia", "National", "Malaysia", False)],
        columns=["state", "region", "map_location", "is_state"],
    ).to_csv(CLEAN / "dim_state.csv", index=False)
    pd.DataFrame(DIVISIONS.items(), columns=["division_code", "division"]) \
      .assign(sort_order=range(len(DIVISIONS))) \
      .to_csv(CLEAN / "dim_division.csv", index=False)

    findings(fact)


def findings(fact):
    latest = fact["date"].max()
    ov = fact[fact["division_code"] == "overall"]
    states = ov[ov["state"] != "Malaysia"]
    print(f"Rows: {len(fact):,}   Latest month: {latest}\n")

    now = states[states["date"] == latest].sort_values("inflation_yoy", ascending=False)
    nat = ov[(ov["state"] == "Malaysia") & (ov["date"] == latest)]["inflation_yoy"].iloc[0]
    print(f"YoY inflation {latest[:7]} (national {nat}%):")
    print(now[["state", "inflation_yoy"]].to_string(index=False), "\n")

    base = states[states["date"] == "2020-01-01"].set_index("state")["cpi_index"]
    cum = (now.set_index("state")["cpi_index"] / base - 1).mul(100).round(1).sort_values(ascending=False)
    print("Cumulative price rise since Jan 2020 (%):")
    print(cum.to_string(), "\n")

    peak = ov[ov["state"] == "Malaysia"].sort_values("inflation_yoy").iloc[-1]
    print(f"National peak YoY since 2010: {peak['inflation_yoy']}% in {peak['date'][:7]}")

    divs = fact[(fact["state"] == "Malaysia") & (fact["date"] == latest) & (fact["division_code"] != "overall")]
    print(f"\nNational YoY by division, {latest[:7]}:")
    print(divs.assign(division=divs["division_code"].map(DIVISIONS))
              .sort_values("inflation_yoy", ascending=False)[["division", "inflation_yoy"]].to_string(index=False))


if __name__ == "__main__":
    main()
