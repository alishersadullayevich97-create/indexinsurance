"""Barqarorlik sinovlari. Dissertatsiyaning 2.2.7-bo'limi va B ilovasi.

Chang bo'roni gipotezasi aynan shu sinovlarda rad etilgan.
"""
import numpy as np
import pandas as pd
from scipy import stats
from config import RANDOM_SEED


def jackknife_correlation(x, y):
    """Har bir kuzatuvni navbat bilan chiqarib, korrelyatsiyani qayta hisoblaydi.

    Natija bitta kuzatuvga bog'liq bo'lsa, shu yerda ko'rinadi.
    """
    x, y = np.asarray(x, float), np.asarray(y, float)
    r0, p0 = stats.pearsonr(x, y)
    rows = []
    for i in range(len(x)):
        m = np.ones(len(x), bool); m[i] = False
        r, p = stats.pearsonr(x[m], y[m])
        rows.append({"chiqarilgan_indeks": i, "r": round(r, 3),
                     "p": round(p, 4), "ahamiyatli": p < 0.05,
                     "r_ozgarishi": round(r - r0, 3)})
    return r0, p0, pd.DataFrame(rows)


def permutation_test(x, y, n_perm=10000, seed=RANDOM_SEED):
    """Taqsimot farazisiz p-qiymat."""
    rng = np.random.default_rng(seed)
    x, y = np.asarray(x, float), np.asarray(y, float)
    obs = abs(stats.pearsonr(x, y)[0])
    count = sum(abs(stats.pearsonr(x, rng.permutation(y))[0]) >= obs
                for _ in range(n_perm))
    return count / n_perm


def partial_correlation(x, y, z):
    """z nazorat qilingan holdagi qisman korrelyatsiya."""
    x, y, z = map(lambda a: np.asarray(a, float), (x, y, z))
    rx = x - np.polyval(np.polyfit(z, x, 1), z)
    ry = y - np.polyval(np.polyfit(z, y, 1), z)
    return stats.pearsonr(rx, ry)


if __name__ == "__main__":
    from s01_data import load_province, load_station
    from s02_detrend import detrend_series
    v = load_province()
    res = detrend_series(v.year, v.production_t)
    v = v.assign(anom=res["anomaly_abs"])
    st = load_station(); st = st[st.station == "Termiz"]
    m = v[["year", "anom"]].merge(st[["year", "dust_days", "heat_days"]], on="year")
    m = m[(m.year >= 2014) & (m.year <= 2024)].reset_index(drop=True)

    r0, p0, jk = jackknife_correlation(m.anom, m.dust_days)
    print(f"Asosiy natija: r = {r0:+.3f}, p = {p0:.4f}, n = {len(m)}")
    jk["yil"] = m.year.values
    print("\nJackknife:")
    print(jk[["yil", "r", "p", "ahamiyatli"]].to_string(index=False))
    print(f"\nSpearman     : rho = {stats.spearmanr(m.anom, m.dust_days)[0]:+.3f}, "
          f"p = {stats.spearmanr(m.anom, m.dust_days)[1]:.4f}")
    pr, pp = partial_correlation(m.anom, m.dust_days, m.heat_days)
    print(f"Qisman (heat): r   = {pr:+.3f}, p = {pp:.4f}")
    print(f"Permutatsiya : p   = {permutation_test(m.anom, m.dust_days):.4f}")
