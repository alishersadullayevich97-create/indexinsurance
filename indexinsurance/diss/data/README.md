# Ma'lumotlar

Ushbu papkadagi fayllar `run_all.py` va notebook natijalarini to'liq takrorlash uchun yetarli (kiritilmagan tashqi ma'lumotlar ro'yxati asosiy README da). Barchasi
rasmiy manbalardan olingan agregat ko'rsatkichlar bo'lib, shaxsiy yoki
maxfiy ma'lumot o'z ichiga olmaydi.

## `wheat_panel.csv`
Surxondaryo viloyati va uning 14 tumani bo'yicha bug'doy ko'rsatkichlari,
2005–2024-yillar.

| Ustun | Mazmuni |
|---|---|
| `district` | Tuman nomi; `Surxondaryo (viloyat)` — agregat qator |
| `year` | Yil |
| `area_ha` | Ekin maydoni, gektar |
| `production_t` | Yalpi hosil, tonna |
| `yield_ts_ga` | Hosildorlik, sentner/gektar |

*Manba:* O'zbekiston Respublikasi Statistika agentligi; Surxondaryo viloyati
statistika boshqarmasi.

**Sifat bo'yicha eslatmalar.** 2006-yil barcha tumanlarda hisobot uzilishi
sababli tahlildan chiqariladi. Bandixon tumani 2011–2019-yillarda Qiziriq
tarkibida bo'lgan. Qiziriq bo'yicha 2024-yil maydoni anomal. Ushbu qoidalar
`src/s01_data.py` da avtomatik qo'llanadi.

## `climate_annual_era5.csv`
ERA5-Land reanalizidan olingan tuman-yil iqlim indekslari (mart–iyun).
Fenologik oyna mahalliy agrotexnik kalendar asosida tanlangan: boshoqlash
20–25 mart, o'rim iyun boshi.

| Ustun | Mazmuni |
|---|---|
| `heat35`, `heat30` | Maksimal harorat 35 °C / 30 °C dan oshgan kunlar soni |
| `t_max_abs` | Davrdagi mutlaq maksimal harorat, °C |
| `rh_min_mean` | O'rtacha kunlik minimal nisbiy namlik, % |
| `precip_sum` | Yig'ma yog'in, mm |

*Manba:* Copernicus Climate Change Service, ERA5-Land hourly data.

## `station_annual.csv`
O'zgidromet meteostansiyalari (Termiz, Sherobod, Sho'rchi) bo'yicha yillik
ekstremal hodisa indekslari.

| Ustun | Ta'rifi |
|---|---|
| `dust_days` | Shamol ≥ 15 m/s **va** nisbiy namlik ≤ 30% bo'lgan kunlar |
| `heat_days` | Maksimal harorat ≥ 35 °C bo'lgan kunlar |
| `wind_days` | Maksimal shamol ≥ 15 m/s bo'lgan kunlar |

`dust_days` — bevosita kuzatuv emas, **vositachi (proksi) ko'rsatkich**.
Nisbiy namlik faqat Termiz stansiyasida qayd etiladi, shu sababli ushbu
indeks boshqa stansiyalar uchun hisoblanmaydi.

*Manba:* O'zbekiston gidrometeorologiya xizmati.

## Kiritilmagan ma'lumotlar
Kunlik xom meteorologik qatorlar (≈ 100 000 qator) hajmi sababli kiritilmagan.
Ular yuqoridagi yillik indekslarni hisoblash uchun ishlatilgan; ERA5-Land
Copernicus Climate Data Store orqali ochiq olinadi, stansiya ma'lumotlari esa
O'zgidrometdan so'rov asosida beriladi.
