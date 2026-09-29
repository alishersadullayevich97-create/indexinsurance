"""9-11-bosqichlar. Mahsulot dizayni, tariflash va bazis riskini baholash.

Dissertatsiyaning 2.4 va 3.1-3.2 bo'limlari.
"""
import numpy as np
import pandas as pd
from config import (DEDUCTIBLE, RISK_LOADING, SUBSIDY_RATE, SUBSIDY_CAP,
                    LOSS_THRESHOLD, HIGH_RISK_ZONE)


def attach_province_index(panel, province):
    """Viloyat indeksini (vanom) panelga qo'shadi.

    Muhim: viloyat indeksi tuman indeksi bilan bir xil o'lchovda -
    HOSILDORLIK (s/ga) anomaliyasi sifatida hisoblanadi, yalpi hosil
    (tonna) anomaliyasi sifatida emas. Yalpi hosil ekin maydoni
    o'zgarishini ham o'z ichiga oladi va hududiy hosildorlik indeksi
    uchun mos emas (dissertatsiya 2.4-bo'limi).
    """
    from s02_detrend import detrend_series
    res = detrend_series(province.year, province.yield_ts_ga)
    vy = province[["year"]].assign(vanom=res["anomaly_pct"])
    return panel.drop(columns=["vanom"], errors="ignore").merge(vy, on="year")


def payout_area_yield(anomaly_pct, deductible=DEDUCTIBLE):
    """Hududiy hosildorlik indeksi to'lovi (dissertatsiya (3.2)-formulasi).

    To'lov = max(0, -anomaliya - ozod)
    """
    return np.maximum(0.0, -np.asarray(anomaly_pct, float) - deductible)


def hedging_effectiveness(loss, payout):
    """Xedjlash samaradorligi (dissertatsiya (3.1)-formulasi).

        HE = [1 - sd(L - I) / sd(L)] * 100

    Manfiy qiymat shartnoma riskni kamaytirmasligini, aksincha oshirishini
    bildiradi - bu amalda kuzatilgan holat (Denov, Sariosiyo).
    """
    loss, payout = np.asarray(loss, float), np.asarray(payout, float)
    if loss.std() == 0:
        return np.nan
    return (1 - (loss - payout).std() / loss.std()) * 100


def simulate_index(panel, deductible=DEDUCTIBLE, index_level="district"):
    """Indeks shartnomasini tarixiy ma'lumotda imitatsiya qiladi.

    index_level="district" - tuman indeksi;
    index_level="province" - viloyat indeksi (bazis riskini o'lchash uchun).
    """
    rows = []
    for name, g in panel.groupby("district"):
        loss = np.maximum(0.0, -g["anom"].values)
        base = g["anom"].values if index_level == "district" else g["vanom"].values
        pay = payout_area_yield(base, deductible)
        rows.append(pd.DataFrame({"district": name, "year": g["year"].values,
                                  "loss": loss, "payout": pay, "net": loss - pay}))
    return pd.concat(rows, ignore_index=True)


def summarise(sim):
    """Imitatsiya natijalarini umumlashtiradi."""
    return {"sof_tarif_pct": round(float(sim.payout.mean()), 2),
            "tolov_chastotasi_pct": round(float((sim.payout > 0).mean() * 100), 0),
            "HE_pct": round(float(hedging_effectiveness(sim.loss, sim.payout)), 1),
            "korrelyatsiya": round(float(np.corrcoef(sim.payout, sim.loss)[0, 1]), 2)}


def basis_risk_table(panel, threshold=LOSS_THRESHOLD):
    """Viloyat indeksining tumanlardagi zararlarni qoplash ko'rsatkichlari."""
    rows = []
    for name, g in panel.groupby("district"):
        actual = g["anom"] < -threshold
        paid = g["vanom"] < -threshold
        rows.append({"tuman": name,
                     "zarar_yillari": int(actual.sum()),
                     "qoplangan": int((actual & paid).sum()),
                     "qoplanmagan": int((actual & ~paid).sum()),
                     "asossiz_tolov": int((~actual & paid).sum())})
    df = pd.DataFrame(rows)
    df.loc[len(df)] = {"tuman": "JAMI", **{c: df[c].sum() for c in df.columns[1:]}}
    return df


def tariff(pure_rate, loading=RISK_LOADING, subsidy=SUBSIDY_RATE, cap=SUBSIDY_CAP):
    """Sof tarifdan yakuniy fermer to'loviga.

    Subsidiya mukofotning belgilangan ulushi, ammo sug'urta summasining
    cap foizidan oshmaydi - amaldagi normativ talab.
    """
    loaded = pure_rate * (1 + loading)
    sub = min(subsidy * loaded, cap)
    return {"sof": round(pure_rate, 2), "yuklamali": round(loaded, 2),
            "subsidiya": round(sub, 2), "fermer": round(loaded - sub, 2),
            "chegara_ishladi": subsidy * loaded > cap}


def zone_tariffs(panel, deductible=DEDUCTIBLE, high_risk=HIGH_RISK_ZONE):
    """Tarif zonalari bo'yicha hisob-kitob."""
    sim = simulate_index(panel, deductible, "district")
    zones = {"Barqaror zona": ~sim.district.isin(high_risk),
             "Yuqori xavf zonasi": sim.district.isin(high_risk),
             "Yagona viloyat tarifi": sim.district.notna()}
    rows = []
    for zname, mask in zones.items():
        g = sim[mask]
        t = tariff(g.payout.mean())
        rows.append({"zona": zname, **t,
                     "HE_pct": round(hedging_effectiveness(g.loss, g.payout), 1),
                     "chastota_pct": round((g.payout > 0).mean() * 100, 0)})
    return pd.DataFrame(rows)
