"""4-bosqich. Iqlim omillari va hosildorlik anomaliyasi o'rtasidagi bog'liqlik.

Bu yerda dissertatsiyaning markaziy uslubiy xulosasi tekshiriladi:
panel modelidagi ahamiyatli koeffitsient avtomatik ravishda yaxshi
sug'urta indeksini anglatmaydi (3.1-bo'limga qarang).
"""
import numpy as np
import pandas as pd
from scipy import stats


def pearson_table(df, y_col, x_cols):
    """Berilgan o'zgaruvchilar bo'yicha korrelyatsiya jadvali."""
    rows = []
    for x in x_cols:
        sub = df[[y_col, x]].dropna()
        r, p = stats.pearsonr(sub[y_col], sub[x])
        rows.append({"omil": x, "r": round(r, 3), "p": round(p, 4),
                     "n": len(sub), "ahamiyatli": p < 0.05})
    return pd.DataFrame(rows)


def two_way_within(df, y_col, x_col, unit="district", time="year"):
    """Tuman va yil effektlarini olib tashlab, ichki korrelyatsiyani hisoblaydi.

    Panel FE regressiyasining koeffitsienti aynan shu o'zgarishdan kelib chiqadi.
    R-kvadrat qiymati indeksning tushuntirish kuchini ko'rsatadi.
    """
    d = df.dropna(subset=[y_col, x_col]).copy()
    for col in (y_col, x_col):
        d[col + "_u"] = d[col] - d.groupby(unit)[col].transform("mean")
        d[col + "_ut"] = d[col + "_u"] - d.groupby(time)[col + "_u"].transform("mean")
    r, p = stats.pearsonr(d[y_col + "_ut"], d[x_col + "_ut"])
    return {"r": r, "p": p, "r_squared": r ** 2, "n": len(d)}


def bonferroni_threshold(n_tests, alpha=0.05):
    """Ko'p sonli gipotezalarni tekshirish uchun tuzatilgan chegara."""
    return alpha / n_tests


if __name__ == "__main__":
    from s01_data import load_districts, load_climate
    from s02_detrend import detrend_panel
    p = detrend_panel(load_districts()).merge(load_climate(), on=["district", "year"])
    print("Yalpi korrelyatsiya:")
    print(pearson_table(p, "anom", ["heat35", "heat30", "precip_sum", "rh_min_mean"]).to_string(index=False))
    w = two_way_within(p, "anom", "heat35")
    print(f"\nTuman+yil effektlari olib tashlangach: r = {w['r']:+.3f}, "
          f"p = {w['p']:.4f}, R2 = {w['r_squared']:.3f} (n = {w['n']})")
    print(f"Bonferroni chegarasi (6 test): {bonferroni_threshold(6):.4f}")
