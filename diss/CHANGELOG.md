# O'zgarishlar tarixi

## [1.1.0] — 2026-10-11

### Ma'lumot sifati
- 2010-yildagi Bandixon va Qiziriq kuzatuvlari tahlildan chiqarildi
  (`config.TRANSITION_2010`, `s01_data.load_districts`). Ma'lumot faylida
  Bandixon 2010: 5 821,5 ga, 0 t (0,0 s/ga); Qiziriq 2010: 11 328 ga, 82 591 t
  (72,9 s/ga; 2008–2009-yillarda 53–58, 2011–2012-yillarda 41–43 s/ga). Ikki tuman
  birgalikda 48,2 s/ga beradi, Qiziriq maydoni esa 2011-yilda 11 328 dan
  17 170 gektarga (+5 842 ga, ya'ni Bandixon maydoniga teng) oshgan. Demak, tuman
  tugatilgan yili Bandixon hosili Qiziriq hisobotiga yozilgan. Faqat Bandixon 2010
  chiqarilsa, Qiziriqdagi ko'zgu-xato tahlilda qolardi. Fayldagi asl qiymatlar
  o'zgartirilmagan.
- Panel: 256 → 254 kuzatuv (2018-yilsiz 243 → 241).

### Mahsulot va tariflash
- Yuqori xavf zonasi qat'iy ro'yxat o'rniga mezon bo'yicha aniqlanadi:
  anomaliyaning standart og'ishi 14% dan yuqori va viloyat anomaliyasi bilan
  korrelyatsiya 0,5 dan past (`config.ZONE_SD_MIN`, `config.ZONE_R_MAX`,
  `s06_product.high_risk_districts`). Natija: faqat Boysun (32,9%; r = 0,12).
  `config.HIGH_RISK_ZONE` ga ro'yxat berilsa, shu ro'yxat ishlatiladi.
- Subsidiya chegarasi olib tashlandi (`config.SUBSIDY_CAP = None`): Vazirlar
  Mahkamasining 28.04.2026 dagi 206-son qarori (15-ilova) bo'yicha subsidiya
  mukofotning 50 foizini tashkil etadi. Avvalgi tartib (02.07.2024 dagi 373-son
  qaror, sug'urta summasining 4 foizi bilan cheklangan; 29.04.2026 dan kuchini
  yo'qotgan) `s06_product.tariff(..., cap=4.0)` bilan hisoblanadi.
- `zone_tariffs` natijasiga `tumanlar` (zonadagi tumanlar soni) ustuni qo'shildi.

### Jadvallar
- `s07_tables.simulate_heat_index`: koeffitsient `panel_fe_table` dan olinadi
  (tuman va yil effektli model, 2018-yilsiz). v1.0.0 da 0,651 qat'iy yozilgan edi;
  v1.1.0 da 0,620.

### Qo'shildi
- `s05_evt.gev_profile_likelihood`: GEV shakl parametrining profil ehtimolligi
  (dissertatsiyaning 2.3.1-bo'limi va 2-ilovasidagi natija endi kod bilan
  takrorlanadi): ξ ≈ 0,020, 95% oraliq [−0,187; +0,373], Gumbelga nisbatan
  LR = 0,024 (p = 0,876). `run_all.py` uni chop etadi va `outputs/gev_profile.csv`
  ga yozadi. Viloyat qatoriga bog'liq, shu sababli 2010-yil qoidasidan ta'sirlanmaydi.

### Natijalarga ta'siri

| Ko'rsatkich | v1.0.0 | v1.1.0 |
|---|---|---|
| Panel kuzatuvlari (2018-yilsiz) | 256 (243) | 254 (241) |
| Panel FE, tuman va yil effektli, 2018-yilsiz | −0,651 (p = 0,007) | −0,620 (p = 0,013) |
| Ichki bog'liqlik (barcha yillar): r; R² | −0,192; 0,037 | −0,214; 0,046 |
| Ta'sir kattaligi (1 SD ≈ 4 kun) | 2,6% | 2,5% |
| Bazis riski: zarar holatlari / qoplangan | 43 / 11 (26%) | 41 / 11 (27%) |
| Xedjlash samaradorligi: tuman / viloyat indeksi | 60,4% / 4,6% | 51,5% / 7,6% |
| Tuman indeksi: sof tarif; to'lov chastotasi; korrelyatsiya | 2,03%; 17%; 0,94 | 1,68%; 16%; 0,92 |
| Tuman anomaliyasi SD oralig'i | 7,3–38,1% (Bandixon) | 7,3–32,9% (Boysun) |
| Yuqori xavf zonasi | Bandixon, Boysun, Qiziriq | Boysun |
| Sof tarif: barqaror / yuqori xavf | 1,14% / 5,98% | 1,14% / 8,29% |
| Fermer to'lovi: barqaror / yuqori xavf | 0,72% / 3,74% | 0,71% / 5,18% |
| Xedjlash samaradorligi: barqaror / yuqori xavf | 42,7% / 74,4% | 42,7% / 69,0% |
| Issiqlik indeksi HE (50–80-protsentil) | −6,9 … −1,6% | −9,2 … −2,1% |
| Tuman tariflari (ozod 10%): Bandixon; Qiziriq | 10,25%; 1,17% | 1,68%; 0,84% |

O'zgarmagan: viloyat darajasidagi trend va 2018-yil anomaliyasi, ekstremal
qiymatlar tahlili (100 yillik daraja 19,0%, bootstrap CI 10,0–28,5%, CVaR(99%)
23,7%), 15 yillik oyna, EQN tariflari, chang gipotezasi sinovlari, qolgan 12
tumanning ko'rsatkichlari.

## [1.0.0] — 2026-09-24

- Dastlabki reliz (Zenodo DOI: 10.5281/zenodo.22933347).
