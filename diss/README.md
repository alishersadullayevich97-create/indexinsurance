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
| `s05_evt.py` | 5–8 | Gumbel, GEV barqarorligi, bootstrap, VaR/CVaR |
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
β = −0,651 (p = 0,007; 2018-yilsiz, klaster SE), ammo dispersiyaning atigi
**3,7%** ini tushuntiradi. Tozalangan o'zgaruvchanlikning bir standart og'ishi
(≈ 4 kun) hosildorlikni **2,6%** ga pasaytiradi.

**Falsifikatsiya.** Stansiya ma'lumotlaridan olingan chang bo'roni
gipotezasi (r = −0,820; p = 0,002) jackknife sinovida **yagona kuzatuvga**
bog'liq ekani aniqlandi: 2018-yil chiqarilganda r = −0,550, p = 0,100.
Gipoteza rad etildi.

**Ekstremal qiymatlar.** GEV shakl parametri aniqlanmaydi
(ξ = +1,14; 95% CI ≈ [−9,6; +8,6] — nol va ikkala ishorani qamraydi),
shu sababli Gumbel tanlanadi. 100 yillik qaytarilish darajasi —
o'rtacha hosilning **19,0%** i (bootstrap CI 10,0–28,5%),
CVaR(99%) — **23,7%**.

**Bazis riski.** Viloyat indeksi tumanlardagi 43 ta zarar holatidan
atigi **11 tasini (26%)** qoplaydi. Xedjlash samaradorligi: tuman
indeksi **60,4%**, viloyat indeksi **4,6%** (13 baravar farq).

**Tarif zonalari** (shartli ozod 10%, yuklama 25%, subsidiya 50%):

| Zona | Sof tarif | Fermer to'lovi | HE |
|---|---|---|---|
| Barqaror (11 tuman) | 1,14% | 0,72% | 42,7% |
| Yuqori xavf (3 tuman) | 5,98% | 3,74% | 74,4% |

---

## Dissertatsiya jadvallari va kod

| Dissertatsiya | Ko'rsatkich | Funksiya |
|---|---|---|
| 2.1.1 | Yalpi hosil, trend, 2018-yil anomaliyasi | `s02_detrend.detrend_series` |
| 2.2 | Iqlim korrelyatsiyalari, within r va R² | `s03_climate.pearson_table`, `two_way_within` |
| 2.2.5 | Panel FE koeffitsientlari (klaster SE), ta'sir kattaligi | `s07_tables.panel_fe_table`, `effect_size` |
| 2.2.7, B ilova | Chang gipotezasi: jackknife, permutatsiya | `s04_robustness` |
| 2.3.1–2.3.2 | GEV sinovi, Gumbel, qaytarilish darajalari, bootstrap CI, VaR/CVaR | `s05_evt` |
| 2.3.1 (2-ustun) | 15 yillik oyna (2010–2024) | `s07_tables.window_evt` |
| 2.3 | 2018-yil: 99,4-kvantil, ≈160 yil | `s07_tables.event_return_period` |
| 2.3.3 | EQN tariflari va burn-rate | `s07_tables.evt_tariffs` |
| 2.4.1–2.4.3, 3.2.2 | Tumanlar: SD, r, HE, sof tarif | `s07_tables.district_table` |
| 2.4.2 | Bazis riski: 43 / 11 / 26% | `s06_product.basis_risk_table` |
| 3.1.2 | Issiqlik indeksi mahsuloti | `s07_tables.simulate_heat_index` |
| 3.1.4 | Shartli ozod sezgirligi | `s07_tables.deductible_table` |
| 3.2.3 | Tarif zonalari | `s06_product.zone_tariffs` |

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
samaradorligi ko'rsatadi, chunki uning tushuntirish kuchi past (R² = 0,037).
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
Bandixon tumanining birlashtirilgan davri, Qiziriq anomaliyasi —
`config.py` da oshkora e'lon qilingan va `s01_data.py` da avtomatik
qo'llanadi. Ular yashirin emas va o'zgartirilishi mumkin.

---

## Iqtibos

Ushbu kod yoki ma'lumotdan foydalansangiz, `CITATION.cff` faylidagi
ma'lumotlar bo'yicha iqtibos keltiring.

## Litsenziya

MIT (`LICENSE` fayliga qarang). Ma'lumotlar rasmiy davlat manbalaridan
olingan bo'lib, ularning asl manbalari `data/README.md` da ko'rsatilgan.
