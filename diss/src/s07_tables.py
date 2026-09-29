"""Dissertatsiyaning qo'shimcha jadvallari.

Ushbu modul run_all.py ning asosiy zanjiriga qo'shimcha ravishda dissertatsiyadagi
quyidagi jadval va ko'rsatkichlarni qayta hisoblaydi:

  2.2.5-jadval  - ikki yo'nalishli qat'iy effektli panel (klaster SE) va ta'sir kattaligi
  2.3.1-jadval  - 15 yillik oyna (2010-2024) bo'yicha Gumbel parametrlari
  2.3-bo'lim    - 2018-yil yo'qotishining kvantili va qaytarilish davri
  2.3.3-jadval  - EQN asosidagi viloyat tariflari va burn-rate
  2.4.1, 2.4.3, 3.2.2-jadvallar - tumanlar bo'yicha risk, HE va sof tarif
  3.1.2-jadval  - issiqlik indeksi (35 C+ kunlar) mahsulotining imitatsion sinovi
  3.1.4-jadval  - shartli ozod darajasi bo'yicha sezgirlik
"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import integrate
from s02_detrend import detrend_series
from s05_evt import loss_series, fit_gumbel, return_levels, var_cvar
from s06_product import (payout_area_yield, hedging_effectiveness, simulate_index,
                         summarise)


# ---------- 2.2.5: panel regressiya ----------
def _fe(df, formula):
    d = df.dropna(subset=["anom", "heat35"]).reset_index(drop=True)
    groups = d["district"].astype("category").cat.codes
    m = smf.ols(formula, d).fit(cov_type="cluster", cov_kwds={"groups": groups})
    return m.params["heat35"], m.pvalues["heat35"], len(d)


def panel_fe_table(panel, drop_year=2018):
    """Issiq kunlar koeffitsienti: tuman FE, tuman+yil FE, to'liq model."""
    specs = [("Tuman effektli", "anom ~ heat35 + C(district)"),
             ("Tuman va yil effektli", "anom ~ heat35 + C(district) + C(year)"),
             ("To'liq model (+ yog'in, namlik)",
              "anom ~ heat35 + precip_sum + rh_min_mean + C(district) + C(year)")]
    rows = []
    for name, f in specs:
        b1, p1, n1 = _fe(panel, f)
        b2, p2, n2 = _fe(panel[panel.year != drop_year], f)
        rows.append({"spetsifikatsiya": name, "beta_barcha": round(b1, 3), "p_barcha": round(p1, 3),
                     "beta_2018siz": round(b2, 3), "p_2018siz": round(p2, 3), "n": f"{n1}/{n2}"})
    return pd.DataFrame(rows)


def within_sd(panel, col):
    """Tuman va yil o'rtachalaridan tozalangan (within) standart og'ish."""
    u = panel[col] - panel.groupby("district")[col].transform("mean")
    return float((u - u.groupby(panel["year"]).transform("mean")).std(ddof=1))


def effect_size(panel, beta):
    """Ta'sir kattaligi = beta x within SD; r = beta x sd_x / sd_y (2.2.8)."""
    sx, sy = within_sd(panel, "heat35"), within_sd(panel, "anom")
    return {"within_sd_kun": round(sx, 2), "tasir_pct": round(float(beta * sx), 2),
            "r": round(float(beta * sx / sy), 3), "R2": round(float((beta * sx / sy) ** 2), 3)}


# ---------- 2.3: EQN qo'shimchalari ----------
def window_evt(province, start=2010):
    """Qisqa oyna (masalan, 2010-2024) bo'yicha Gumbel - 2.3.1-jadval 2-ustuni."""
    w = province[province.year >= start]
    res = detrend_series(w.year, w.production_t)
    g = fit_gumbel(loss_series(res["anomaly_abs"]))
    mp = w.production_t.mean()
    return g, return_levels(g["dist"], mean_production=mp), var_cvar(g["dist"], mean_production=mp)


def event_return_period(dist, loss, n_years):
    """Kuzatilgan yo'qotishning kvantili, qaytarilish davri va n yilda kuzatilish ehtimoli."""
    q = float(dist.cdf(loss)); T = 1.0 / (1.0 - q)
    return {"kvantil_pct": round(q * 100, 2), "davr_yil": round(T), "P_n_yilda_pct": round((1 - (1 - 1 / T) ** n_years) * 100, 1)}


def evt_tariffs(dist, losses, mean_production, triggers=(90.0, 92.5, 95.0), loading=0.25, subsidy=0.5):
    """2.3.3-jadval: EQN (Gumbel integrali) va burn-rate asosidagi viloyat tariflari."""
    lp = np.asarray(losses) / mean_production * 100
    rows = []
    for tr in triggers:
        ded = 100 - tr
        f = lambda x: max(0.0, x / mean_production * 100 - ded) * dist.pdf(x)
        ev, _ = integrate.quad(f, ded * mean_production / 100, dist.ppf(0.999999), limit=500)
        rows.append({"trigger_pct": tr, "sof_EQN": round(ev, 2), "yuklamali": round(ev * (1 + loading), 2),
                     "subsidiyadan_keyin": round(ev * (1 + loading) * (1 - subsidy), 2),
                     "burn_rate": round(float(np.maximum(0, lp - ded).mean()), 2)})
    return pd.DataFrame(rows)


# ---------- 2.4, 3.1, 3.2: tumanlar va mahsulot ----------
def district_table(panel, deductible=10.0):
    """Tumanlar: anomaliya SD, viloyat bilan r, HE (tuman/viloyat), sof tarif, chastota."""
    st = simulate_index(panel, deductible, "district")
    sv = simulate_index(panel, deductible, "province")
    rows = []
    for d, g in st.groupby("district"):
        gv, gp = sv[sv.district == d], panel[panel.district == d]
        rows.append({"tuman": d, "n": len(gp), "sd_pct": round(gp.anom.std(ddof=1), 1),
                     "r_viloyat": round(gp.anom.corr(gp.vanom), 2),
                     "HE_tuman": round(hedging_effectiveness(g.loss, g.payout), 1),
                     "HE_viloyat": round(hedging_effectiveness(gv.loss, gv.payout), 1),
                     "sof_tarif": round(g.payout.mean(), 2),
                     "chastota_pct": round((g.payout > 0).mean() * 100)})
    return pd.DataFrame(rows).sort_values("sd_pct", ascending=False).reset_index(drop=True)


def province_anomaly_sd(province):
    """Viloyat hosildorlik anomaliyasining standart og'ishi (2.4.1: 7,0%)."""
    return round(float(np.std(detrend_series(province.year, province.yield_ts_ga)["anomaly_pct"], ddof=1)), 1)


def simulate_heat_index(panel, beta=0.651, percentiles=(50, 60, 70, 75, 80)):
    """3.1.2-jadval: to'lov = beta x max(0, issiq kunlar - tuman protsentili)."""
    loss = np.maximum(0.0, -panel["anom"].to_numpy())
    rows = []
    for q in percentiles:
        thr = panel.groupby("district")["heat35"].transform(lambda s: np.percentile(s, q))
        pay = beta * np.maximum(0.0, panel["heat35"] - thr).to_numpy()
        rows.append({"protsentil": q, "sof_tarif": round(pay.mean(), 2), "chastota_pct": round((pay > 0).mean() * 100),
                     "HE_pct": round(hedging_effectiveness(loss, pay), 1), "korrelyatsiya": round(np.corrcoef(pay, loss)[0, 1], 2)})
    return pd.DataFrame(rows)


def deductible_table(panel, levels=(5.0, 7.5, 10.0, 12.5, 15.0, 20.0)):
    """3.1.4-jadval: shartli ozod darajasiga qarab tarif, chastota, HE, korrelyatsiya."""
    return pd.DataFrame([{"ozod_pct": d, **summarise(simulate_index(panel, d, "district"))} for d in levels])
