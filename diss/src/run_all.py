"""Butun tahlil zanjirini bir buyruq bilan qayta hisoblaydi.

Ishga tushirish:  python run_all.py
Natijalar outputs/ papkasiga yoziladi.
"""
import numpy as np
import pandas as pd
from config import OUT, DEDUCTIBLE
from s01_data import load_province, load_districts, load_climate, load_station
from s02_detrend import detrend_series, detrend_panel
from s03_climate import pearson_table, two_way_within
from s04_robustness import jackknife_correlation, permutation_test, partial_correlation
from s05_evt import (loss_series, fit_gumbel, check_gev_stability, return_levels,
                     bootstrap_return_levels, var_cvar)
from s06_product import attach_province_index, simulate_index, summarise, basis_risk_table, zone_tariffs
from s07_tables import (panel_fe_table, effect_size, window_evt, event_return_period, evt_tariffs,
                       district_table, province_anomaly_sd, simulate_heat_index, deductible_table)
from scipy import stats


def hdr(t):
    print("\n" + "=" * 68); print(t); print("=" * 68)


def main():
    # --- 1-3: ma'lumot va trend ---
    hdr("1-3. MA'LUMOT VA TREND")
    v = load_province()
    res = detrend_series(v.year, v.production_t)
    v = v.assign(anom_abs=res["anomaly_abs"], anom=res["anomaly_pct"])
    mp = v.production_t.mean()
    print(f"Viloyat: {len(v)} yil, o'rtacha {mp:,.0f} t, "
          f"CV {v.production_t.std(ddof=1)/mp*100:.1f}%")
    print(f"Trend: {res['slope']:+,.0f} t/yil (p = {res['p_value']:.4f})")
    i18 = list(v.year).index(2018)
    print(f"2018: {res['anomaly_abs'][i18]:,.0f} t ({res['anomaly_pct'][i18]:.1f}%)")

    panel = detrend_panel(load_districts())
    panel = attach_province_index(panel, v)   # viloyat HOSILDORLIK anomaliyasi
    panel = panel.merge(load_climate(), on=["district", "year"], how="left")
    print(f"Panel: {len(panel)} kuzatuv, {panel.district.nunique()} tuman")

    # --- 4: iqlim bog'liqligi ---
    hdr("4. IQLIM BOG'LIQLIGI")
    print(pearson_table(panel, "anom", ["heat35", "precip_sum", "rh_min_mean"]).to_string(index=False))
    w = two_way_within(panel, "anom", "heat35")
    print(f"\nTuman+yil effektlaridan keyin: r = {w['r']:+.3f}, p = {w['p']:.4f}, "
          f"R2 = {w['r_squared']:.3f}")

    # --- barqarorlik ---
    hdr("BARQARORLIK SINOVLARI (chang gipotezasi)")
    st = load_station(); st = st[st.station == "Termiz"]
    m = v[["year", "anom_abs"]].merge(st[["year", "dust_days", "heat_days"]], on="year")
    m = m[(m.year >= 2014) & (m.year <= 2024)].reset_index(drop=True)
    r0, p0, jk = jackknife_correlation(m.anom_abs, m.dust_days)
    print(f"Asosiy: r = {r0:+.3f}, p = {p0:.4f}, n = {len(m)}")
    worst = jk.loc[jk.r.abs().idxmin()]
    print(f"Eng ta'sirchan kuzatuv: {int(m.year[worst.chiqarilgan_indeks])}-yil "
          f"-> r = {worst.r:+.3f}, p = {worst.p:.4f}")
    print(f"Spearman: rho = {stats.spearmanr(m.anom_abs, m.dust_days)[0]:+.3f}")
    print(f"Permutatsiya p = {permutation_test(m.anom_abs, m.dust_days):.4f}")
    jk.assign(yil=m.year.values).to_csv(OUT / "jackknife.csv", index=False)

    # --- 5-8: EVT ---
    hdr("5-8. EKSTREMAL QIYMATLAR NAZARIYASI")
    L = loss_series(v.anom_abs)
    gev = check_gev_stability(L)
    print(f"GEV xi = {gev['xi']:+.3f}, CI = [{gev['ci_low']:+.2f}, {gev['ci_high']:+.2f}] "
          f"-> {'aniqlangan' if gev['identified'] else 'ANIQLANMAGAN, Gumbel tanlanadi'}")
    g = fit_gumbel(L)
    print(f"Gumbel: mu = {g['mu']:,.0f}, sigma = {g['sigma']:,.0f}\n")
    rl = return_levels(g["dist"], mean_production=mp); print(rl.to_string(index=False))
    vc = var_cvar(g["dist"], mean_production=mp); print("\n" + vc.to_string(index=False))
    bs = bootstrap_return_levels(L, mean_production=mp); print("\n" + bs.to_string(index=False))
    rl.to_csv(OUT / "return_levels.csv", index=False)
    bs.to_csv(OUT / "bootstrap_ci.csv", index=False)

    # --- 9-11: mahsulot ---
    hdr("9-11. MAHSULOT DIZAYNI VA BAZIS RISKI")
    for lvl, lab in [("district", "Tuman indeksi"), ("province", "Viloyat indeksi")]:
        s = simulate_index(panel, DEDUCTIBLE, lvl)
        print(f"{lab:18s}: {summarise(s)}")
    br = basis_risk_table(panel)
    tot = br.iloc[-1]
    print(f"\nBazis riski: {tot.zarar_yillari} ta zarar holati, "
          f"{tot.qoplangan} tasi qoplangan "
          f"({tot.qoplangan/tot.zarar_yillari*100:.0f}%)")
    br.to_csv(OUT / "basis_risk.csv", index=False)

    zt = zone_tariffs(panel)
    print("\nTarif zonalari:"); print(zt.to_string(index=False))
    zt.to_csv(OUT / "zone_tariffs.csv", index=False)

    # --- Qo'shimcha dissertatsiya jadvallari (s07_tables) ---
    hdr("QO'SHIMCHA JADVALLAR: 2.2.5, 2.3, 2.4, 3.1")
    fe = panel_fe_table(panel); print("2.2.5 - panel regressiya (klaster SE):"); print(fe.to_string(index=False))
    b = abs(fe.loc[1, "beta_2018siz"])
    print(f"Ta'sir kattaligi (2.2.8): {effect_size(panel, b)}")
    print(f"\n2018-yil yo'qotishi: {event_return_period(g['dist'], L[i18], len(v))}")
    g15, rl15, vc15 = window_evt(v)
    print(f"\n2.3.1 - 15 yillik oyna (2010-2024): mu = {g15['mu']:,.0f}, sigma = {g15['sigma']:,.0f}")
    print(rl15.to_string(index=False)); print(vc15.to_string(index=False))
    et = evt_tariffs(g["dist"], L, mp); print("\n2.3.3 - viloyat tariflari, %:"); print(et.to_string(index=False))
    dt = district_table(panel); print(f"\n2.4.1/2.4.3/3.2.2 - tumanlar (viloyat anomaliyasi SD = {province_anomaly_sd(v)}%):")
    print(dt.to_string(index=False))
    hi = simulate_heat_index(panel); print("\n3.1.2 - issiqlik indeksi mahsuloti:"); print(hi.to_string(index=False))
    dd = deductible_table(panel); print("\n3.1.4 - shartli ozod sezgirligi:"); print(dd.to_string(index=False))
    for name, df in [("panel_fe", fe), ("evt_window_2010", rl15), ("evt_tariffs", et), ("districts", dt),
                     ("heat_index_product", hi), ("deductible", dd)]:
        df.to_csv(OUT / f"{name}.csv", index=False)
    print(f"\nNatijalar saqlandi: {OUT}")


if __name__ == "__main__":
    main()
