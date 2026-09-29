"""2-3-bosqichlar. Texnologik trendni ajratish va anomaliya qatorini shakllantirish.

Anomaliya (dissertatsiya (2.1)-formulasi):
    A_it = (Y_it - Y_hat_it) / Y_hat_it * 100
"""
import numpy as np
import pandas as pd
from scipy import stats
from config import MIN_YEARS_TREND


def detrend_series(years, values):
    """Chiziqli trend o'rnatib, trend qiymatlari va foizli anomaliyani qaytaradi."""
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)
    slope, intercept, r, p, se = stats.linregress(years, values)
    trend = intercept + slope * years
    anomaly_pct = (values - trend) / trend * 100.0
    return {"slope": slope, "intercept": intercept, "p_value": p,
            "r_squared": r ** 2, "trend": trend, "anomaly_pct": anomaly_pct,
            "anomaly_abs": values - trend}


def detrend_panel(df, value_col="yield_ts_ga", group_col="district"):
    """Har bir tuman uchun ALOHIDA trend ajratadi.

    Bu muhim: texnologik o'sish sur'ati tumanlar bo'yicha bir xil emas,
    umumiy trend qo'llash hududiy tafovutni buzadi.
    """
    parts = []
    for name, g in df.groupby(group_col):
        g = g.sort_values("year")
        if len(g) < MIN_YEARS_TREND:
            continue
        res = detrend_series(g.year, g[value_col])
        parts.append(g.assign(trend=res["trend"], anom=res["anomaly_pct"]))
    return pd.concat(parts, ignore_index=True)


if __name__ == "__main__":
    from s01_data import load_province, load_districts
    v = load_province()
    r = detrend_series(v.year, v.production_t)
    print(f"Viloyat yalpi hosil trendi: {r['slope']:+,.0f} t/yil, p = {r['p_value']:.4f}")
    i2018 = list(v.year).index(2018)
    print(f"2018-yil anomaliyasi: {r['anomaly_abs'][i2018]:,.0f} t "
          f"({r['anomaly_pct'][i2018]:.1f}%)")
    p = detrend_panel(load_districts())
    print(f"Panel: {len(p)} kuzatuv, {p.district.nunique()} tuman")
