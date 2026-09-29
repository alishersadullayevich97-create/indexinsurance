"""
SACRA v2.0 — interactive web application
========================================

Left:  choropleth map of Surkhandarya districts (Leaflet via folium).
Right: Gumbel risk profile and parametric premium calculator for the
       selected district.

Expected files (produced by sacra_pipeline.py):
    results/district_results.csv
    results/districts_enriched.geojson
    results/panel.csv

Run locally:   streamlit run app.py
Deploy:        push to GitHub, then share.streamlit.io
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from sacra_core import (Gumbel, AreaYieldContract, commercial_premium,
                        burn_rate, coverage_for_trigger_prob, validate)

# ----------------------------------------------------------------------
# Page setup and brand palette
# ----------------------------------------------------------------------

NAVY = "#0A1F44"
EMERALD = "#046A38"
AMBER = "#C8811A"
CRIMSON = "#A32020"

st.set_page_config(page_title="SACRA — Index Insurance Analyzer",
                   page_icon="🌾", layout="wide")

st.markdown(f"""
<style>
  .block-container {{ padding-top: 2rem; }}
  h1, h2, h3 {{ color: {NAVY}; }}
  .stMetric {{ background: #F5F7FA; padding: 0.6rem; border-radius: 6px; }}
</style>
""", unsafe_allow_html=True)

# Resolved from this file's location: Streamlit Cloud starts the app from
# the repository root, so a bare "results" path would not be found there.
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RES_CSV = RESULTS_DIR / "district_results.csv"
GEO_JSON = RESULTS_DIR / "districts_enriched.geojson"
PANEL_CSV = RESULTS_DIR / "panel.csv"
ZONE_CSV = RESULTS_DIR / "official_zone_tariffs.csv"


# ----------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------

@st.cache_data
def load_data():
    if not os.path.exists(RES_CSV):
        return None, None, None
    results = pd.read_csv(RES_CSV)
    geo = None
    if os.path.exists(GEO_JSON):
        with open(GEO_JSON, encoding="utf-8") as f:
            geo = json.load(f)
    panel = pd.read_csv(PANEL_CSV) if os.path.exists(PANEL_CSV) else None
    zones = pd.read_csv(ZONE_CSV) if os.path.exists(ZONE_CSV) else None
    return results, geo, panel, zones


results, geo, panel, zones = load_data()

if results is None:
    st.error(
        "Ma'lumot fayllari topilmadi. Avval `sacra_pipeline.py` ni ishga "
        "tushiring — u `results/` papkasini yaratadi."
    )
    st.stop()

# Official tariffs (dissertation) exist for every district; the Gumbel
# scenario model needs fitted parameters.
if "sof_tarif" not in results.columns:
    st.error("Rasmiy tariflar topilmadi. `sacra_pipeline.py` ni qayta "
             "ishga tushiring.")
    st.stop()
official = results[results["sof_tarif"].notna()
                   & results["mu"].notna() & results["beta"].notna()].copy()
priced = results[results["status"] == "ok"].copy()   # Gumbel checks passed


# ----------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------

st.title("SACRA — Surxondaryo agroiqlim risk analizatori")
st.caption(
    "Tuman hosildorlik indeksiga asoslangan parametrik sug'urta · "
    "rasmiy tariflar: dissertatsiya tahlil zanjiri v1.0.0 "
    "(DOI 10.5281/zenodo.22933347) · DGU № 60955 · INDEXINSURANCE.UZ"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Tumanlar", f"{len(official)}")
if zones is not None:
    z = zones.set_index("zona")
    def zrate(name):
        return f"{z.loc[name, 'sof']:.2f}%" if name in z.index else "—"
    c2.metric("Barqaror zona, sof tarif", zrate("Barqaror zona"))
    c3.metric("Yuqori xavf zonasi, sof tarif", zrate("Yuqori xavf zonasi"))
    c4.metric("Yagona viloyat tarifi", zrate("Yagona viloyat tarifi"))

st.divider()


# ----------------------------------------------------------------------
# Sidebar controls
# ----------------------------------------------------------------------

with st.sidebar:
    st.header("Tuman")

    district = st.selectbox("Tuman", sorted(official["district"]))
    row = official[official["district"] == district].iloc[0]
    gumbel_ok = row["status"] == "ok"

    st.markdown("---")
    st.subheader("Stsenariy parametrlari")
    st.caption("Gumbel modeli bilan muqobil shartnoma shartlarini sinash uchun. "
               "Rasmiy tarifga ta'sir qilmaydi.")
    auto = st.checkbox("Qoplamani avtomatik tanlash", value=True,
                       help="Maqsadli trigger chastotasidan teskari hisoblanadi")

    dist = Gumbel(mu=float(row["mu"]), beta=float(row["beta"]))
    y_ref = float(row["y_ref"])

    if auto:
        target_p = st.slider("Maqsadli trigger chastotasi", 0.05, 0.35,
                             0.15, 0.01,
                             help="0.15 ≈ 7 yilda bir marta")
        coverage = coverage_for_trigger_prob(dist, y_ref, target_p)
        # A volatile district can imply a very low coverage. Below 0.30 there
        # is no room for an exit level above the 0.20 floor, so clamp it and
        # tell the user rather than letting the contract become invalid.
        if coverage < 0.30:
            st.warning(
                f"Hisoblangan qoplama {coverage*100:.1f}% — juda past "
                f"(tuman o'ta o'zgaruvchan). 30% ga ko'tarildi."
            )
            coverage = 0.30
        st.info(f"Hisoblangan qoplama: **{coverage*100:.1f}%**")
    else:
        coverage = st.slider("Qoplama darajasi (λ)", 0.50, 0.98, 0.85, 0.01)

    # The default must sit inside [min, max] or Streamlit raises an error.
    exit_max = float(max(0.25, coverage - 0.05))
    exit_default = float(np.clip(min(0.50, coverage - 0.10), 0.20, exit_max))
    exit_level = st.slider("To'liq to'lov darajasi (λ_exit)",
                           0.20, exit_max, exit_default, 0.01)

    tsi = st.number_input("Sug'urta summasi (so'm/ga)",
                          min_value=100_000, max_value=50_000_000,
                          value=1_000_000, step=100_000)

    st.markdown("---")
    st.subheader("Yuklama")
    k = st.slider("Risk yuklamasi k", 0.0, 0.50, 0.15, 0.01)
    expense = st.slider("Xarajat ulushi", 0.0, 0.45, 0.25, 0.01)
    alpha = st.select_slider("CVaR darajasi", [0.90, 0.95, 0.99], value=0.99)

    st.markdown("---")
    LAYER_LABELS = {
        "sof_tarif": "Rasmiy sof tarif, % (dissertatsiya)",
        "chastota_pct": "To'lov chastotasi, % (dissertatsiya)",
        "HE_tuman": "Xedjlash samaradorligi, % (dissertatsiya)",
        "sd_pct": "Hosildorlik anomaliyasi SD, %",
        "pure_rate": "Gumbel stsenariy: sof stavka",
        "CVaR99": "Gumbel stsenariy: CVaR 99%, kg/ga",
        "r_heat35": "r (35°C+ kunlar – hosildorlik)",
    }
    metric = st.selectbox(
        "Xarita qatlami",
        [c for c in LAYER_LABELS if c in official.columns],
        format_func=lambda c: LAYER_LABELS[c],
    )


# ----------------------------------------------------------------------
# Contract for the selected district
# ----------------------------------------------------------------------

contract = AreaYieldContract(y_ref=y_ref, coverage=coverage,
                             exit_level=exit_level, tsi=tsi)
pure = contract.pure_premium(dist)
com = commercial_premium(pure, dist, contract, alpha=alpha, k=k,
                         expense_ratio=expense)


# ----------------------------------------------------------------------
# Layout
# ----------------------------------------------------------------------

left, right = st.columns([1.05, 1])

# ---------------------------- MAP -------------------------------------
with left:
    st.subheader("Hududiy risk xaritasi")

    if geo is None:
        st.warning("GeoJSON topilmadi — xarita o'rniga jadval ko'rsatilmoqda.")
        st.dataframe(official[["district", metric]].sort_values(metric),
                     width="stretch", hide_index=True)
    else:
        try:
            import folium
            from folium.features import GeoJsonTooltip
            from streamlit_folium import st_folium

            vals = official[metric].astype(float)
            vmin, vmax = float(vals.min()), float(vals.max())
            span = (vmax - vmin) or 1.0
            lookup = dict(zip(official["district"], vals))

            def shade(feature):
                name = feature["properties"].get("district")
                v = lookup.get(name)
                if v is None:
                    fill = "#DDDDDD"
                else:
                    t = (v - vmin) / span
                    # light yellow -> amber -> crimson
                    r = int(255 - 90 * t)
                    g = int(237 - 180 * t)
                    b = int(160 - 130 * t)
                    fill = f"#{r:02x}{g:02x}{b:02x}"
                selected = name == district
                return {
                    "fillColor": fill,
                    "color": EMERALD if selected else "#FFFFFF",
                    "weight": 3.5 if selected else 1.0,
                    "fillOpacity": 0.85,
                }

            tip_fields = [f for f in ["district", "zone", "sof_tarif",
                                      "chastota_pct", "HE_tuman"]
                          if f in official.columns or f == "district"]

            # OpenStreetMap: keyless and free. CartoDB basemaps now require
            # an API key, so they are deliberately not used here.
            m = folium.Map(location=[37.9, 67.6], zoom_start=8,
                           tiles="OpenStreetMap")
            folium.GeoJson(
                geo, style_function=shade,
                tooltip=GeoJsonTooltip(fields=tip_fields,
                                       aliases=tip_fields, localize=True),
            ).add_to(m)
            m.fit_bounds(folium.GeoJson(geo).get_bounds())
            st_folium(m, height=460, use_container_width=True,
                      returned_objects=[])

            st.caption(
                f"Qatlam: **{metric}** · diapazon {vmin:.4g} – {vmax:.4g} · "
                f"yashil chegara = tanlangan tuman"
            )
        except ImportError:
            st.warning(
                "Xarita uchun `folium` va `streamlit-folium` kerak. "
                "`requirements.txt` ga qo'shing."
            )
            st.dataframe(official[["district", metric]].sort_values(metric),
                         width="stretch", hide_index=True)

    st.markdown("##### Rasmiy tariflar (dissertatsiya, 3.2.2-jadval)")
    rank = official[["district", "zone", "sof_tarif", "chastota_pct",
                     "HE_tuman"]].copy()
    rank.columns = ["Tuman", "Zona", "Sof tarif %", "To'lov chastotasi %",
                    "HE %"]
    st.dataframe(rank.sort_values("Sof tarif %", ascending=False),
                 width="stretch", hide_index=True, height=260)


# ------------------------- CALCULATOR ---------------------------------
with right:
    st.subheader(district)

    # ---- official tariff: dissertation, table 3.2.2 ----
    with st.container(border=True):
        st.markdown("**Rasmiy tarif** — dissertatsiya 3.2.2-jadvali "
                    "(shartli ozod 10%, tuman hosildorlik indeksi)")
        o1, o2, o3, o4 = st.columns(4)
        o1.metric("Sof tarif", f"{row['sof_tarif']:.2f}%")
        o2.metric("Zona", str(row["zone"]))
        o3.metric("To'lov chastotasi", f"{row['chastota_pct']:.0f}%")
        o4.metric("HE (tuman indeksi)", f"{row['HE_tuman']:.1f}%")

    # ---- supplementary Gumbel scenario ----
    st.markdown("#### Stsenariy kalkulyatori (Gumbel)")
    st.caption(
        "Yon paneldagi shartlar bilan muqobil shartnomani modellashtiradi. "
        "To'lov shkalasi va yuklamalar rasmiy mahsulotdan farq qiladi, "
        "shuning uchun natija rasmiy tarifga teng bo'lmaydi."
    )
    if not gumbel_ok:
        st.warning(
            f"Bu tuman uchun Gumbel modeli tekshiruvdan o'tmadi "
            f"({row['status']}). Stsenariy natijalari ishonchli emas — "
            f"faqat rasmiy tarifga tayaning."
        )

    m1, m2, m3 = st.columns(3)
    m1.metric("Sof premiya", f"{pure:,.0f}",
              f"{pure/tsi*100:.2f}% TSI")
    m2.metric("Brutto premiya", f"{com['gross_premium']:,.0f}",
              f"{com['rate_on_line']*100:.2f}% TSI")
    m3.metric("Trigger ehtimoli",
              f"{contract.trigger_probability(dist)*100:.1f}%",
              f"≈ {1/max(contract.trigger_probability(dist),1e-9):.0f} yilda 1")

    st.markdown(
        f"**Trigger hosildorligi:** {y_ref*coverage:,.0f} kg/ha &nbsp;·&nbsp; "
        f"**To'liq to'lov:** {y_ref*exit_level:,.0f} kg/ha &nbsp;·&nbsp; "
        f"**Y_ref:** {y_ref:,.0f} kg/ha"
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        ["To'lov funksiyasi", "Qaytish davri", "Tarixiy", "Tafsilot"])

    # --- payout function ---
    with tab1:
        grid = np.linspace(0, y_ref, 400)
        pay = contract.payout(y_ref - grid)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=grid, y=pay, mode="lines",
                                 line=dict(color=NAVY, width=3),
                                 name="To'lov"))
        fig.add_vline(x=y_ref * coverage, line_dash="dash", line_color=AMBER,
                      annotation_text="Trigger")
        fig.add_vline(x=y_ref * exit_level, line_dash="dash",
                      line_color=CRIMSON, annotation_text="Exit")
        fig.update_layout(height=340, xaxis_title="Hosildorlik (kg/ha)",
                          yaxis_title="To'lov (so'm/ga)",
                          margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, width="stretch")

    # --- return levels ---
    with tab2:
        periods = np.array([2, 5, 10, 20, 50, 100, 200])
        rl = np.array([dist.return_level(float(T)) for T in periods])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=periods, y=rl, mode="lines+markers",
                                 line=dict(color=CRIMSON, width=3),
                                 name="Qaytish darajasi"))
        fig.add_hline(y=contract.attachment, line_dash="dash",
                      line_color=AMBER, annotation_text="Trigger")
        fig.update_layout(height=340, xaxis_type="log",
                          xaxis_title="Qaytish davri (yil)",
                          yaxis_title="Hosil kamomadi (kg/ha)",
                          margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, width="stretch")

        st.dataframe(
            pd.DataFrame({
                "Qaytish davri": [f"{T} yil" for T in periods],
                "Kamomad (kg/ha)": np.round(rl, 1),
                "To'lov (so'm/ga)": np.round(contract.payout(rl), 0),
            }), width="stretch", hide_index=True)

    # --- historical ---
    with tab3:
        if panel is None:
            st.info("`panel.csv` topilmadi.")
        else:
            sub = panel[panel["district"] == district].sort_values("year")
            if sub.empty:
                st.info("Bu tuman uchun tarixiy qator yo'q.")
            else:
                br = burn_rate(sub["yield_kg_ha"].to_numpy(float), contract)
                fig = go.Figure()
                fig.add_trace(go.Bar(x=sub["year"], y=sub["yield_kg_ha"],
                                     marker_color=EMERALD, name="Hosildorlik"))
                fig.add_hline(y=y_ref, line_color=NAVY,
                              annotation_text="Y_ref")
                fig.add_hline(y=y_ref * coverage, line_dash="dash",
                              line_color=AMBER, annotation_text="Trigger")
                fig.update_layout(height=320, xaxis_title="Yil",
                                  yaxis_title="Hosildorlik (kg/ha)",
                                  margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig, width="stretch")

                b1, b2 = st.columns(2)
                b1.metric("Empirik burn rate",
                          f"{br['burn_rate']*100:.2f}%",
                          f"{br['n_triggers']}/{br['n_years']} yil")
                b2.metric("Model sof tarif", f"{pure/tsi*100:.2f}%",
                          f"{(pure/tsi - br['burn_rate'])*100:+.2f} pp")

                if abs(pure / tsi - br["burn_rate"]) > 0.01:
                    st.warning(
                        "Model va empirik stavka sezilarli farq qilmoqda. "
                        "Kichik namunada bu kutiladi — konservativ yondashuv "
                        "uchun ikkalasining yuqorisini oling."
                    )

    # --- detail ---
    with tab4:
        st.markdown("**Gumbel parametrlari**")
        st.code(f"mu   = {dist.mu:10.3f}\nbeta = {dist.beta:10.3f}\n"
                f"n    = {int(row['n_years']):10d}", language="text")

        st.markdown("**Premiya tarkibi**")
        st.dataframe(pd.DataFrame({
            "Komponent": ["Sof premiya", "Risk yuklamasi",
                          "Texnik premiya", "Brutto premiya"],
            "So'm/ga": [round(com["pure_premium"]),
                        round(com["risk_load"]),
                        round(com["technical_premium"]),
                        round(com["gross_premium"])],
            "% TSI": [round(com["pure_premium"] / tsi * 100, 3),
                      round(com["risk_load"] / tsi * 100, 3),
                      round(com["technical_premium"] / tsi * 100, 3),
                      round(com["rate_on_line"] * 100, 3)],
        }), width="stretch", hide_index=True)

        st.markdown("**Tekshiruvlar**")
        for name, ok, detail in validate(dist, contract):
            st.markdown(f"{'✅' if ok else '❌'} **{name}** — {detail}")

        cols = [c for c in official.columns if c.startswith(("r_", "p_"))]
        if cols:
            st.markdown("**Iqlim–hosildorlik korrelyatsiyasi**")
            st.dataframe(row[cols].to_frame("qiymat").round(4),
                         width="stretch")


st.divider()
st.caption(
    "Rasmiy tariflar dissertatsiya tahlil zanjiri (v1.0.0) orqali tarixiy "
    "imitatsiya usulida hisoblangan. Stsenariy kalkulyatori Gumbel (EV-I) "
    "modeliga asoslangan qo'shimcha vosita. Kichik namuna sharoitida barcha "
    "baholar noaniqlikka ega — shartnoma tuzishdan oldin aktuar ekspertizasi "
    "talab etiladi. © Abdullayev A.S., DGU № 60955"
)
