"""1-bosqich. Ma'lumotni yuklash va sifat tekshiruvidan o'tkazish."""
import pandas as pd
import numpy as np
from config import (WHEAT, CLIMATE, STATION, EXCLUDE_YEAR, BANDIXON_MERGED,
                    QIZIRIQ_ANOMALY, PROVINCE_ROW, CITY_ROW)


def load_province() -> pd.DataFrame:
    """Viloyat darajasidagi qatorni qaytaradi (2006-yil chiqarilgan)."""
    w = pd.read_csv(WHEAT)
    v = w[(w.district == PROVINCE_ROW) & (w.year != EXCLUDE_YEAR)].sort_values("year")
    return v.reset_index(drop=True)


def load_districts() -> pd.DataFrame:
    """Tumanlar panelini qaytaradi, sifat qoidalari qo'llangan holda.

    Qo'llanadigan cheklovlar (dissertatsiya 2.1.1-bo'limi):
      - 2006-yil butunlay chiqariladi;
      - Bandixon 2011-2019 yillarda Qiziriq tarkibida bo'lgani uchun chiqariladi;
      - Qiziriq 2024-yil kuzatuvi anomaliya sifatida chiqariladi;
      - viloyat va shahar qatorlari tahlilga kirmaydi.
    """
    w = pd.read_csv(WHEAT)
    w = w[w.year != EXCLUDE_YEAR]
    lo, hi = BANDIXON_MERGED
    w = w[~((w.district == "Bandixon") & (w.year.between(lo, hi)))]
    w = w[~w.district.isin([PROVINCE_ROW, CITY_ROW])].copy()
    dname, dyear = QIZIRIQ_ANOMALY
    w.loc[(w.district == dname) & (w.year == dyear), "yield_ts_ga"] = np.nan
    return w.dropna(subset=["yield_ts_ga"]).reset_index(drop=True)


def load_climate() -> pd.DataFrame:
    """ERA5-Land asosidagi tuman-yil iqlim indekslari."""
    return pd.read_csv(CLIMATE)


def load_station() -> pd.DataFrame:
    """Meteostansiyalar bo'yicha yillik indekslar."""
    return pd.read_csv(STATION)


if __name__ == "__main__":
    v, d, c, s = load_province(), load_districts(), load_climate(), load_station()
    print(f"Viloyat qatori : {len(v)} yil ({v.year.min()}-{v.year.max()})")
    print(f"Tuman paneli   : {len(d)} kuzatuv, {d.district.nunique()} tuman")
    print(f"Iqlim paneli   : {len(c)} kuzatuv")
    print(f"Stansiyalar    : {s.station.nunique()} ta")
