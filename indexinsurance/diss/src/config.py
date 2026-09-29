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

# --- Ma'lumot sifati bo'yicha qarorlar (dissertatsiya 2.1.1-bo'limi) ---
EXCLUDE_YEAR      = 2006                      # hisobot metodologiyasidagi uzilish
BANDIXON_MERGED   = (2011, 2019)              # tuman Qiziriq tarkibida bo'lgan davr
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
SUBSIDY_CAP     = 4.0      # sug'urta summasidan maksimal subsidiya, %
LOSS_THRESHOLD  = 10.0     # bazis riski tahlilida zarar chegarasi, %

# --- Tarif zonalari (dissertatsiya 3.2.3-bo'limi) ---
HIGH_RISK_ZONE = ["Bandixon", "Boysun", "Qiziriq"]
