"""Markaziy sozlamalar. Barcha modullar shu yerdan parametr oladi."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT  = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

# --- Ma'lumot fayllari ---
WHEAT   = DATA / "wheat_panel.csv"
CLIMATE = DATA / "climate_annual_era5.csv"
STATION = DATA / "station_annual.csv"

# --- Ma'lumot sifati bo'yicha qarorlar (dissertatsiya 2.1.3-bo'limi) ---
EXCLUDE_YEAR      = 2006                      # hisobot metodologiyasidagi uzilish
BANDIXON_MERGED   = (2011, 2019)              # tuman Qiziriq tarkibida bo'lgan davr
# v1.1.0: 2010-yil - Bandixon hosili Qiziriq hisobiga yozilgan yil. Bandixon: 5 821,5 ga, 0 t (0,0 s/ga);
# Qiziriq: 11 328 ga, 82 591 t (72,9 s/ga). Ikkalasi birgalikda 48,2 s/ga. Ikkala kuzatuv ham chiqariladi.
TRANSITION_2010   = (("Bandixon", 2010), ("Qiziriq", 2010))
QIZIRIQ_ANOMALY   = ("Qiziriq", 2024)         # maydon 82% ga kamaygan anomaliya
PROVINCE_ROW      = "Surxondaryo (viloyat)"
CITY_ROW          = "Termiz shahri"

# --- Model parametrlari ---
MIN_YEARS_TREND = 8        # trend baholash uchun minimal kuzatuv soni
N_BOOTSTRAP     = 2000     # bootstrap takrorlari
RANDOM_SEED     = 42

# --- Sug'urta mahsuloti parametrlari (dissertatsiya 3.1-3.2 bo'limlari) ---
DEDUCTIBLE      = 10.0     # shartli ozod, %
RISK_LOADING    = 0.25     # risk yuklamasi
SUBSIDY_RATE    = 0.50     # davlat subsidiyasi ulushi
SUBSIDY_CAP     = None     # sug'urta summasidan maksimal subsidiya, % (None - chegara yo'q).
                           # v1.1.0: VM 28.04.2026 dagi 206-son qarori, 15-ilova - mukofotning 50% i,
                           # chegarasiz. Avvalgi tartib (VM 02.07.2024 dagi 373-son qarori): 4,0%.
LOSS_THRESHOLD  = 10.0     # bazis riski tahlilida zarar chegarasi, %

# --- Tarif zonalari (dissertatsiya 3.2.3-bo'limi) ---
# Yuqori xavf zonasi mezon bo'yicha aniqlanadi: anomaliya SD > ZONE_SD_MIN va
# viloyat anomaliyasi bilan korrelyatsiya < ZONE_R_MAX (v1.1.0 natijasi: faqat Boysun).
ZONE_SD_MIN    = 14.0
ZONE_R_MAX     = 0.5
HIGH_RISK_ZONE = None      # None - mezon bo'yicha avtomatik; ro'yxat berilsa, shu ro'yxat ishlatiladi
