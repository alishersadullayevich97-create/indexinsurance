"""
SACRA v2.0 — district-level pipeline
====================================

Inputs
------
  diss/                         dissertation repository v1.0.0 (unchanged):
                                wheat panel, ERA5-Land climate, analysis code
  data/sacra_districts.geojson  district boundaries from GEE

Outputs  (in  indexinsurance/app/results/)
-------
  district_results.csv        one row per district: Gumbel parameters,
                              return levels, VaR/CVaR, premium rates
  districts_enriched.geojson  boundaries + results, ready for the web map
  panel.csv                   merged yield + climate panel
  official_district_tariffs.csv  dissertation table 3.2.2
  official_zone_tariffs.csv      dissertation tariff zones

Run from anywhere:   python app/sacra_pipeline.py
"""

import json
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from sacra_core import (Gumbel, AreaYieldContract, commercial_premium,
                        validate, burn_rate, coverage_for_trigger_prob)

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
# Paths are resolved from this file's location, not the current working
# directory, so the script behaves the same whether it is run from the
# repository root, from app/, or by Claude Code.
#
#   indexinsurance/
#   ├── data/     <- inputs
#   └── app/
#       ├── sacra_pipeline.py   (this file)
#       └── results/            <- outputs, read by app.py

APP_DIR  = Path(__file__).resolve().parent
REPO_DIR = APP_DIR.parent
DATA_DIR = REPO_DIR / "data"
DISS_SRC = REPO_DIR / "diss" / "src"

# Yield and climate data are read through the dissertation's own loaders
# (diss/src/s01_data.py), so the site and the dissertation apply identical
# data-quality rules.  Only the map boundaries live in data/.
GEOJSON_FILE = DATA_DIR / "sacra_districts.geojson"
OUT_DIR      = APP_DIR / "results"

import sys
sys.path.insert(0, str(DISS_SRC))

COVERAGE   = 0.80      # trigger at 80% of reference yield
EXIT_LEVEL = 0.40      # full payout at 40%
TSI        = 1_000_000 # sum insured per hectare (UZS)
CLIMATE_VARS = ["heat35", "heat30", "t_max_abs", "rh_min_mean", "precip_sum"]
MIN_YEARS  = 10        # a district with fewer years is not priced
TARGET_P   = 0.15      # design target: contract triggers ~1 year in 7
AUTO_COVER = True      # derive coverage per district from TARGET_P

ALPHAS  = (0.90, 0.95, 0.99)
PERIODS = (5, 10, 20, 50, 100)


# ----------------------------------------------------------------------
# 1. Load and merge
# ----------------------------------------------------------------------

# GAUL (FAO) English district names -> official Uzbek Latin names.
# Applied to every file on load, so the map, the tables and yields.csv
# all speak the same names.
GAUL_TO_UZ = {
    "Altinsay district": "Oltinsoy",     "Angor district": "Angor",
    "Bandikhan district": "Bandixon",    "Baysun district": "Boysun",
    "Denau district": "Denov",           "Jarkurgan district": "Jarqo'rg'on",
    "Kizirik district": "Qiziriq",       "Kumkurgan district": "Qumqo'rg'on",
    "Sariasiya district": "Sariosiyo",   "Shurchi district": "Sho'rchi",
    "Termez district": "Termiz tumani",  "Uzun district": "Uzun",
    "Muzrabad district": "Muzrabod",     "Sherabad district": "Sherobod",
    "Termez city": "Termiz shahri",
}

# Excel may swap straight apostrophes for typographic ones.
_APOSTROPHES = str.maketrans({"\u2019": "'", "\u02bb": "'", "\u02bc": "'",
                              "\u2018": "'", "`": "'"})


def normalise_names(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.translate(_APOSTROPHES)
    return s.replace(GAUL_TO_UZ)


def read_csv_any(path) -> pd.DataFrame:
    """
    Read a CSV whatever Excel's locale did to it.

    Excel on Russian/Uzbek Windows saves CSV with ';' as the separator and
    ',' as the decimal mark (4620,5).  The standard reader then sees one
    column.  Sniff the separator and pick the matching decimal mark.
    """
    with open(path, encoding="utf-8-sig") as f:
        head = f.readline()
    sep = ";" if head.count(";") > head.count(",") else ","
    dec = "," if sep == ";" else "."
    return pd.read_csv(path, sep=sep, decimal=dec, encoding="utf-8-sig")


def load_panel():
    """Yield + climate panel, built with the dissertation's loaders."""
    if not DISS_SRC.exists():
        raise SystemExit(f"\nXATO: dissertatsiya kodi topilmadi -> {DISS_SRC}\n")
    from s01_data import load_districts, load_climate

    d = load_districts()
    y = pd.DataFrame({"year": d["year"].astype(int),
                      "district": d["district"],
                      "yield_kg_ha": d["yield_ts_ga"] * 100.0})   # s/ga -> kg/ga
    c = load_climate()
    c["year"] = c["year"].astype(int)

    panel = y.merge(c, on=["year", "district"], how="left")
    return panel.sort_values(["district", "year"]).reset_index(drop=True)


def official_tariffs():
    """
    Official district and zone tariffs, computed by the dissertation code
    (tables 3.2.2 and the tariff zones).  These are the numbers the site
    presents as the tariff; the Gumbel model is a supplementary scenario tool.
    """
    from s01_data import load_province, load_districts, load_climate
    from s02_detrend import detrend_series, detrend_panel
    from s06_product import attach_province_index, zone_tariffs
    from s07_tables import district_table
    from config import HIGH_RISK_ZONE

    v = load_province()
    res = detrend_series(v.year, v.production_t)
    v = v.assign(anom_abs=res["anomaly_abs"], anom=res["anomaly_pct"])
    panel = detrend_panel(load_districts()).merge(
        load_climate(), on=["district", "year"], how="left")
    panel = attach_province_index(panel, v)

    dt = district_table(panel).rename(columns={"tuman": "district"})
    dt["zone"] = np.where(dt["district"].isin(HIGH_RISK_ZONE),
                          "Yuqori xavf", "Barqaror")
    return dt, zone_tariffs(panel)


# ----------------------------------------------------------------------
# 2. Detrending
# ----------------------------------------------------------------------

def detrend(sub: pd.DataFrame):
    """
    Remove the technological trend so that the loss distribution reflects
    climate risk only.  Returns (reference yield, detrended yields).

    A linear trend is used; if it is not significant (p > 0.10) the raw
    mean is kept instead, which avoids over-fitting on short series.
    """
    x = sub["year"].to_numpy(float)
    y = sub["yield_kg_ha"].to_numpy(float)

    slope, intercept, r, p, se = stats.linregress(x, y)
    if p <= 0.10:
        fitted = intercept + slope * x
        y_ref = float(fitted[-1])                 # trend value in the last year
        adjusted = y * (y_ref / fitted)           # multiplicative adjustment
        return y_ref, adjusted, {"trend_slope": slope, "trend_p": p,
                                 "detrended": True}
    return float(y.mean()), y, {"trend_slope": slope, "trend_p": p,
                                "detrended": False}


# ----------------------------------------------------------------------
# 3. Per-district analysis
# ----------------------------------------------------------------------

def analyse_district(name: str, sub: pd.DataFrame) -> dict:
    n = len(sub)
    if n < MIN_YEARS:
        return {"district": name, "n_years": n, "status": "insufficient data"}

    y_ref, y_adj, trend_info = detrend(sub)
    shortfall = y_ref - y_adj

    try:
        g = Gumbel.fit_lmoments(shortfall)
    except ValueError as e:
        return {"district": name, "n_years": n, "status": f"fit failed: {e}"}

    cover = (coverage_for_trigger_prob(g, y_ref, TARGET_P)
             if AUTO_COVER else COVERAGE)
    # Same floor as the app: below 0.30 no valid exit level fits.
    cover = max(cover, 0.30)
    exit_lv = max(0.20, min(EXIT_LEVEL, cover - 0.05))
    contract = AreaYieldContract(y_ref=y_ref, coverage=cover,
                                 exit_level=exit_lv, tsi=TSI)
    pure = contract.pure_premium(g)
    com  = commercial_premium(pure, g, contract)
    br   = burn_rate(y_adj, contract)

    checks = validate(g, contract, ALPHAS, PERIODS)
    failed = [nm for nm, ok, _ in checks if not ok and not nm.startswith("[design]")]

    row = {
        "district": name,
        "n_years": n,
        "status": "ok" if not failed else "check failed: " + "; ".join(failed),
        "y_ref": y_ref,
        "y_min": float(sub["yield_kg_ha"].min()),
        "y_max": float(sub["yield_kg_ha"].max()),
        "cv": float(np.std(y_adj, ddof=1) / np.mean(y_adj)),
        "coverage": cover,
        "exit_level": exit_lv,
        "mu": g.mu,
        "beta": g.beta,
        "trend_slope": trend_info["trend_slope"],
        "trend_p": trend_info["trend_p"],
        "detrended": trend_info["detrended"],
        "trigger_prob": contract.trigger_probability(g),
        "pure_rate": pure / TSI,
        "gross_rate": com["rate_on_line"],
        "burn_rate": br["burn_rate"],
        "n_triggers": br["n_triggers"],
    }

    for T in PERIODS:
        row[f"RL{T}"] = g.return_level(T)
    for a in ALPHAS:
        tag = int(a * 100)
        row[f"VaR{tag}"] = g.var(a)
        row[f"CVaR{tag}"] = g.cvar(a)

    # Climate-yield correlations — the dissertation's central evidence
    # Every numeric climate column is correlated with yield.
    climate_vars = [v for v in CLIMATE_VARS if v in sub.columns]
    for var in climate_vars:
        if var in sub.columns and sub[var].notna().sum() >= MIN_YEARS:
            ok = sub[var].notna()
            # A series with no variation has no defined correlation —
            # record that instead of letting scipy warn and return NaN.
            if sub.loc[ok, var].nunique() < 2:
                row[f"r_{var}"] = np.nan
                row[f"p_{var}"] = np.nan
                row.setdefault("constant_vars", [])
                row["constant_vars"].append(var)
                continue
            r, p = stats.pearsonr(sub.loc[ok, var], sub.loc[ok, "yield_kg_ha"])
            row[f"r_{var}"] = r
            row[f"p_{var}"] = p

    if "constant_vars" in row:
        row["constant_vars"] = ",".join(row["constant_vars"])

    return row


# ----------------------------------------------------------------------
# 4. Map output
# ----------------------------------------------------------------------

def enrich_geojson(results: pd.DataFrame):
    if not os.path.exists(GEOJSON_FILE):
        warnings.warn(f"{GEOJSON_FILE} not found — skipping map export")
        return

    with open(GEOJSON_FILE, encoding="utf-8") as f:
        gj = json.load(f)

    lookup = results.set_index("district").to_dict("index")
    matched = 0
    for feat in gj["features"]:
        raw = str(feat["properties"].get("district", "")).strip()
        name = GAUL_TO_UZ.get(raw, raw)
        feat["properties"]["district"] = name       # map shows Uzbek names
        vals = lookup.get(name)
        if vals:
            matched += 1
            feat["properties"].update(
                {k: (None if pd.isna(v) else v) for k, v in vals.items()}
            )

    print(f"  matched {matched}/{len(gj['features'])} map features")
    out = os.path.join(OUT_DIR, "districts_enriched.geojson")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False)
    print(f"  wrote {out}")


# ----------------------------------------------------------------------
# 5. Main
# ----------------------------------------------------------------------

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    panel = load_panel()
    print(f"Panel: {len(panel)} rows, {panel.district.nunique()} districts, "
          f"{panel.year.min()}-{panel.year.max()}")
    panel.to_csv(os.path.join(OUT_DIR, "panel.csv"), index=False)

    rows = [analyse_district(name, sub)
            for name, sub in panel.groupby("district", sort=True)]
    results = pd.DataFrame(rows)

    # Official tariffs from the dissertation code, merged per district.
    dt, zt = official_tariffs()
    dt.to_csv(OUT_DIR / "official_district_tariffs.csv", index=False)
    zt.to_csv(OUT_DIR / "official_zone_tariffs.csv", index=False)
    results = results.merge(dt, on="district", how="left", suffixes=("", "_diss"))
    print("\nRasmiy tarif zonalari (dissertatsiya):")
    print(zt[["zona", "sof", "yuklamali", "fermer", "HE_pct"]].to_string(index=False))

    out_csv = os.path.join(OUT_DIR, "district_results.csv")
    results.to_csv(out_csv, index=False)
    print(f"  wrote {out_csv}")

    enrich_geojson(results)

    # ---- console summary ------------------------------------------------
    ok = results[results.status == "ok"]
    print("\n" + "=" * 84)
    print(f"{'District':<16}{'n':>4}{'Y_ref':>9}{'CV':>7}{'Cov':>6}"
          f"{'Pure%':>8}{'Gross%':>8}{'Burn%':>8}{'CVaR99':>9}{'r_heat35':>9}")
    print("=" * 84)
    for _, r in ok.iterrows():
        print(f"{r['district'][:15]:<16}{r['n_years']:>4}{r['y_ref']:>9.0f}"
              f"{r['cv']:>7.3f}{r['coverage']:>6.2f}{r['pure_rate']*100:>8.2f}"
              f"{r['gross_rate']*100:>8.2f}{r['burn_rate']*100:>8.2f}"
              f"{r['CVaR99']:>9.0f}"
              f"{r.get('r_heat35', float('nan')):>9.3f}")

    bad = results[results.status != "ok"]
    if len(bad):
        print("\nNot priced:")
        for _, r in bad.iterrows():
            print(f"  {r['district']}: {r['status']}")

    if "constant_vars" in results.columns:
        const = results.dropna(subset=["constant_vars"])
        if len(const):
            print(f"\nDIQQAT: {len(const)} tumanda indeks o'zgarmas (korrelyatsiya yo'q):")
            for _, r in const.iterrows():
                print(f"  {r['district']}: {r['constant_vars']}")

    print(f"\nRegional mean pure rate : {ok.pure_rate.mean()*100:.2f}%")
    print(f"Regional mean burn rate : {ok.burn_rate.mean()*100:.2f}%")
    if "r_heat35" in ok.columns:
        sig = ok[ok.p_heat35 < 0.05]
        print(f"Districts with significant heat35-yield correlation: "
              f"{len(sig)}/{len(ok)}")


if __name__ == "__main__":
    main()
