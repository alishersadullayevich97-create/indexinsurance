# INDEXINSURANCE.UZ

Surxondaryo viloyati uchun parametrik (indeksli) bug'doy sug'urtasi
platformasi. Tahliliy yadro — SACRA (DGU № 60955).

## Tuzilish

```
indexinsurance/
├── site/index.html        Statik sayt → Cloudflare Pages (output: site)
├── app/                   Streamlit ilova → Streamlit Cloud (app/app.py)
│   ├── app.py             Xarita + rasmiy tariflar + stsenariy kalkulyatori
│   ├── sacra_core.py      Gumbel stsenariy modeli
│   ├── sacra_pipeline.py  diss/ → app/results/ konveyeri
│   └── results/           Hisoblangan natijalar (ilova shu yerdan o'qiydi)
├── diss/                  Dissertatsiya tahlil zanjiri v1.0.0 — O'ZGARTIRILMAYDI
├── data/                  Xarita chegaralari (GEE eksporti)
└── gee/                   Google Earth Engine skriptlari (arxiv)
```

## Tariflar qayerdan keladi

- **Rasmiy tarif** — `diss/src` dagi dissertatsiya kodi (3.2.2-jadval,
  tarif zonalari). Sayt va dissertatsiya bir xil raqam ko'rsatadi.
- **Stsenariy kalkulyatori** — `app/sacra_core.py` dagi Gumbel modeli;
  muqobil shartlarni sinash uchun, rasmiy tarifni almashtirmaydi.

## Natijalarni qayta hisoblash

```
pip install -r app/requirements.txt -r diss/requirements.txt
python app/sacra_pipeline.py
```

Keyin `app/results/` ni commit qiling — Streamlit Cloud shu fayllarni o'qiydi.

## Dissertatsiya yangilansa

`diss/` papkasini yangi versiya bilan to'liq almashtiring, konveyerni qayta
ishga tushiring, commit qiling.

© Abdullayev Alisher Sa'dulla o'g'li · DGU № 60955 · DOI 10.5281/zenodo.22933347
