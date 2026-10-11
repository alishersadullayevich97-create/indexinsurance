# SACRA — Surxondaryo bug'doychiligida iqlim riski va indeksli sug'urta

Sug'oriladigan bug'doychilikda ekstremal iqlim risklarini baholash va
hududiy hosildorlik (area-yield) indeksiga asoslangan sug'urta mahsulotini
loyihalash uchun to'liq takrorlanuvchi tahlil zanjiri.

Kod PhD dissertatsiyasining empirik qismini amalga oshiradi: *"Qishloq
xo'jaligida ekstremal iqlim risklarini ekonometrik modellashtirish va
indeksli sug'urta tizimini takomillashtirish (Surxondaryo viloyati bug'doy
hosildorligi misolida)"*.

Dasturiy ta'minot O'zbekiston Respublikasida rasmiy ro'yxatdan o'tkazilgan:
**guvohnoma № DGU 60955** (talabnoma DT 202602428, 02.03.2026).

**Joriy versiya: 1.1.0.** Avvalgi versiyadan farqlar — `CHANGELOG.md` da.

---

## Tez boshlash

```bash
git clone https://github.com/alishersadullayevich97-create/sacra-index-insurance.git
cd sacra-index-insurance
pip install -r requirements.txt
cd src && python run_all.py
```

Colab uchun: `notebooks/SACRA_analysis.ipynb` faylini oching va
birinchi katakni ishga tushiring — u repozitoriyni klonlaydi va
barcha bog'liqliklarni o'rnatadi.

---

## Tahlil zanjiri

| Modul | Bosqichlar | Vazifasi |
|---|---|---|
| `s01_data.py` | 1 | Ma'lumotni yuklash, sifat qoidalarini qo'llash |
| `s02_detrend.py` | 2–3 | Texnologik trendni ajratish, anomaliya qatori |
| `s03_climate.py` | 4 | Iqlim–hosildorlik bog'liqligi, ichki (within) tahlil |
| `s04_robustness.py` | — | Jackknife, permutatsiya, qisman korrelyatsiya |
| `s05_evt.py` | 5–8 | Gumbel, GEV barqarorligi, profil ehtimollik, bootstrap, VaR/CVaR |
| `s06_product.py` | 9–11 | To'lov funksiyasi, tariflash, bazis riski, zonalar |
| `s07_tables.py` | — | Qo'shimcha jadvallar: panel FE, 15 yillik oyna, EQN tariflari, tumanlar, issiqlik indeksi, shartli ozod |
| `run_all.py` | 1–11 | Butun zanjirni bir buyruq bilan qayta hisoblash |

Har bir modulni alohida ham ishga tushirish mumkin
(`python s05_evt.py`) — u o'z natijasini chop etadi.

---

## Asosiy natijalar

Quyidagilar `run_all.py` chiqishidan olingan va dissertatsiya matniga mos.

**Ishlab chiqarish dinamikasi (2005–2024).** Yalpi hosil barqaror
(o'rtacha 594 721 t, CV 6,9%), trend statistik ahamiyatsiz
(+2 175 t/yil, p = 0,21). Ekin maydoni 17,5% ga qisqargan (p = 0,006),
hosildorlik esa o'sgan (p = 0,046) — barqarorlik ikki qarama-qarshi
jarayon muvozanati natijasi.

**Iqlim signali.** Mavsumiy o'rtacha ko'rsatkichlar hosildorlik
tebranishini tushuntirmaydi (|r| ≤ 0,23). Tuman va yil effektlari olib
tashlangandan keyin issiqlik indeksi ahamiyatli bo'ladi: panel koeffitsienti
β = −0,620 (p = 0,013; 2018-yilsiz, klaster SE), ammo dispersiyaning atigi
**4,6%** ini tushuntiradi. Tozalangan o'zgaruvchanlikning bir standart og'ishi
(≈ 4 kun) hosildorlikni **2,5%** ga pasaytiradi.

**Falsifikatsiya.** Stansiya ma'lumotlaridan olingan chang bo'roni
gipotezasi (r = −0,820; p = 0,002) jackknife sinovida **yagona kuzatuvga**
bog'liq ekani aniqlandi: 2018-yil chiqarilganda r = −0,550, p = 0,100.
Gipoteza rad etildi.

**Ekstremal qiymatlar.** GEV shakl parametri aniqlanmaydi
(ξ = +1,14; 95% CI ≈ [−9,6; +8,6] — nol va ikkala ishorani qamraydi),
shu sababli Gumbel tanlanadi. Profil ehtimollik ham shuni tasdiqlaydi:
ξ ≈ 0,02 (95% oraliq [−0,19; +0,37]), Gumbel modeliga nisbatan LR = 0,02
(p = 0,88). 100 yillik qaytarilish darajasi —
o'rtacha hosilning **19,0%** i (bootstrap CI 10,0–28,5%),
CVaR(99%) — **23,7%**.

**Bazis riski.** Viloyat indeksi tumanlardagi 41 ta zarar holatidan
atigi **11 tasini (27%)** qoplaydi. Xedjlash samaradorligi: tuman
indeksi **51,5%**, viloyat indeksi **7,6%** (qariyb 7 baravar farq).

**Tarif zonalari** (shartli ozod 10%, yuklama 25%, subsidiya — mukofotning 50%,
chegarasiz). Yuqori xavf zonasi mezon bo'yicha aniqlanadi: anomaliyaning standart
og'ishi 14% dan yuqori va viloyat anomaliyasi bilan korrelyatsiya 0,5 dan past
(`config.ZONE_SD_MIN`, `config.ZONE_R_MAX`). Bu shartni faqat Boysun tumani
qanoatlantiradi (32,9%; r = 0,12).

| Zona | Sof tarif | Fermer to'lovi | HE |
|---|---|---|---|
| Barqaror (13 tuman) | 1,14% | 0,71% | 42,7% |
| Yuqori xavf (Boysun) | 8,29% | 5,18% | 69,0% |

Subsidiya Vazirlar Mahkamasining 28.04.2026 dagi 206-son qarori (15-ilova)
bo'yicha hisoblanadi: mukofotning 50 foizi, sug'urta summasiga nisbatan chegarasiz
(`config.SUBSIDY_CAP = None`). Avvalgi tartib (373-son qaror, 4% chegara) bilan
solishtirish uchun `s06_product.tariff(..., cap=4.0)` — bunda Boysunda fermer
to'lovi 6,36% bo'lar edi.

---

## Dissertatsiya jadvallari va kod

| Dissertatsiya | Ko'rsatkich | Funksiya |
|---|---|---|
| 2.1.1 | Yalpi hosil, trend, 2018-yil anomaliyasi | `s02_detrend.detrend_series` |
| 2.2 | Iqlim korrelyatsiyalari, within r va R² | `s03_climate.pearson_table`, `two_way_within` |
| 2.2.5 | Panel FE koeffitsientlari (klaster SE), ta'sir kattaligi | `s07_tables.panel_fe_table`, `effect_size` |
| 2.2.7, B ilova | Chang gipotezasi: jackknife, permutatsiya | `s04_robustness` |
| 2.3.1–2.3.2, 2-ilova | GEV sinovi, profil ehtimollik, Gumbel, qaytarilish darajalari, bootstrap CI, VaR/CVaR | `s05_evt` |
| 2.3.1 (2-ustun) | 15 yillik oyna (2010–2024) | `s07_tables.window_evt` |
| 2.3 | 2018-yil: 99,4-kvantil, ≈160 yil | `s07_tables.event_return_period` |
| 2.3.3 | EQN tariflari va burn-rate | `s07_tables.evt_tariffs` |
| 2.4.1–2.4.3, 3.2.2 | Tumanlar: SD, r, HE, sof tarif | `s07_tables.district_table` |
| 2.4.2 | Bazis riski: 41 / 11 / 27% | `s06_product.basis_risk_table` |
| 3.1.2 | Issiqlik indeksi mahsuloti | `s07_tables.simulate_heat_index` |
| 3.1.4 | Shartli ozod sezgirligi | `s07_tables.deductible_table` |
| 3.2.3 | Tarif zonalari, zona mezoni | `s06_product.zone_tariffs`, `high_risk_districts` |

**Repozitoriyga kiritilmagan ma'lumotlar.** Quyidagi natijalar tashqi
ma'lumotlarga tayanadi va `run_all.py` bilan qayta hisoblanmaydi: NASA POWER
oylik qatorlari (2.2.2, 2.2.4-jadvallar; power.larc.nasa.gov da ochiq),
meteostansiyalarning kunlik qatorlari (2.2.3–2.2.4; repozitoriyda faqat yillik
agregatlar bor), ERA5-Land asosidagi chang ta'riflari va ularning panel
koeffitsientlari (2.2.3, 2.2.7), sug'urta tashkilotlari ma'lumotlari (2.5.1–2.5.4)
va fermerlar so'rovi (2.5.5).

---

## Uslubiy jihatdan e'tiborga loyiq ikki nuqta

**Statistik ahamiyatlilik yetarli mezon emas.** Panel modelida ahamiyatli
deb topilgan issiqlik indeksi imitatsion sinovda manfiy xedjlash
samaradorligi ko'rsatadi, chunki uning tushuntirish kuchi past (R² = 0,046).
Indeks tanlovida HE va R² bevosita o'lchanishi kerak.

**Kichik tanlanmada EVT.** Uch parametrli GEV modelini 19 ta kuzatuvda
baholab bo'lmaydi. Bu yerda u tasdiqlanmagan taxmin sifatida emas,
bootstrap orqali **empirik ko'rsatilgan** va Gumbel spetsifikatsiyasiga
o'tish shu asosda asoslangan.

---

## Takrorlanuvchanlik

Barcha tasodifiy jarayonlar (bootstrap, permutatsiya) `config.py` dagi
`RANDOM_SEED = 42` bilan qat'iylashtirilgan, shu sababli natijalar
ishga tushirishlar orasida o'zgarmaydi.

Ma'lumot sifati bo'yicha barcha qarorlar — 2006-yilni chiqarish,
Bandixon tumanining birlashtirilgan davri (2011–2019), 2010-yildagi
Bandixon va Qiziriq o'tish kuzatuvlari (v1.1.0), Qiziriq 2024 anomaliyasi —
`config.py` da oshkora e'lon qilingan va `s01_data.py` da avtomatik
qo'llanadi. Ular yashirin emas va o'zgartirilishi mumkin.

**2010-yil qoidasi.** Ma'lumot faylida 2010-yilda Bandixon uchun 5 821,5 ga
maydonda 0 t hosil, Qiziriq uchun esa 72,9 s/ga (qo'shni yillarda 41–58 s/ga)
qayd etilgan; ikki tuman birgalikda 48,2 s/ga beradi, Qiziriq maydoni esa
2011-yilda Bandixon maydoniga teng miqdorda (+5 842 ga) oshgan. Ya'ni tuman
tugatilgan yili Bandixon hosili Qiziriq hisobotiga yozilgan. Shu sababli ikkala
kuzatuv ham chiqariladi (`config.TRANSITION_2010`); faqat Bandixon 2010 chiqarilsa,
Qiziriqdagi ko'zgu-xato tahlilda qolardi.

---

## Iqtibos

Ushbu kod yoki ma'lumotdan foydalansangiz, `CITATION.cff` faylidagi
ma'lumotlar bo'yicha iqtibos keltiring. Har bir reliz Zenodo'da alohida
versiya DOI'sini oladi (v1.0.0: 10.5281/zenodo.22933347); muayyan natijalarga
iqtibos keltirishda shu versiyaning DOI'sidan, barcha versiyalarga umumiy
havola uchun esa Zenodo yozuvidagi «Cite all versions» (concept DOI) dan
foydalaning.

## Litsenziya

MIT (`LICENSE` fayliga qarang). Ma'lumotlar rasmiy davlat manbalaridan
olingan bo'lib, ularning asl manbalari `data/README.md` da ko'rsatilgan.
