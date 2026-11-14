"""Reefline app. Run from the repo root:   streamlit run app.py

Each tab is a function listed in TABS at the bottom. To add a feature, write a
function that draws a tab and add one line to TABS.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from satellite import compare, data_io, similar, trends

st.set_page_config(page_title="Reefline", layout="wide")
CFG = data_io.load_config()
COLORS = {"Significant warming trend": "#D7263D",
          "Predicted next intensification": "#F29E1F",
          "Monitor": "#8D99AE"}


@st.cache_data
def load_all():
    reefs = data_io.load_reefs()
    results = {}
    for name, vc in CFG["variables"].items():
        results[name] = trends.analyze_variable(
            reefs.site_id, lambda r, vc=vc: data_io.load_series(vc, r), CFG)
    risk = similar.risk_table(results[CFG["risk"]["variable"]], reefs, CFG)
    return reefs, results, risk


REEFS, RESULTS, RISK = load_all()
if REEFS["data_source"].astype(str).str.contains("synthetic", case=False).any():
    st.warning("DEMO DATA: these reefs and time series are synthetic. "
               "Replace data/ with real NASA-derived CSVs (see README).")


# ----------------------------------------------------------------- tabs
def tab_map():
    st.subheader("Where are reef stress trends significant, and where next?")
    df = RISK.copy()
    df["color"] = df["status"].map(COLORS)
    df["size"] = np.where(df["status"] == "Monitor", 60000, 110000)
    st.map(df, latitude="lat", longitude="lon", color="color", size="size")
    st.markdown(" ".join(f"<span style='color:{c}'>&#9679;</span> {k}&nbsp;&nbsp;" for k, c in COLORS.items()),
                unsafe_allow_html=True)
    show = df[["name", "status", "slope_per_year", "ci_low", "ci_high", "p_adj", "risk", "risk_class"]]
    st.dataframe(show.round(3), use_container_width=True, hide_index=True)
    st.caption("Slope in deg C per year (Sen's slope, with 95% CI). p_adj is Mann-Kendall with FDR correction. "
               "Risk score is a transparent rule-based ranking, not a forecast.")


def tab_detail():
    st.subheader("Reef detail")
    c1, c2 = st.columns(2)
    site_id = c1.selectbox("Reef", RISK["site_id"], format_func=lambda r: RISK.set_index("site_id").loc[r, "name"])
    var = c2.selectbox("Variable", list(CFG["variables"]), format_func=lambda v: CFG["variables"][v]["label"])
    vc = CFG["variables"][var]
    s = data_io.load_series(vc, site_id)
    res = RESULTS[var]
    row = res[res.site_id == site_id]
    if s is None or row.empty:
        st.info("No data for this reef and variable.")
        return
    row = row.iloc[0]
    anom = trends.deseasonalize(s).dropna()
    t = ((anom.index.year - anom.index[0].year) * 12 + (anom.index.month - anom.index[0].month)).to_numpy()
    slope_m = row["slope_per_year"] / 12
    line = np.median(anom.to_numpy() - slope_m * t) + slope_m * t

    m1, m2, m3 = st.columns(3)
    m1.metric("Sen's slope", f"{row['slope_per_year']:+.3f} {vc['unit']}",
              help=f"95% CI {row['ci_low']:+.3f} to {row['ci_high']:+.3f}")
    m2.metric("p (FDR adjusted)", f"{row['p_adj']:.3g}", "significant" if row["significant"] else "not significant")
    m3.metric("Kendall tau", f"{row['tau']:+.2f}")

    fig = go.Figure()
    fig.add_scatter(x=anom.index, y=anom.values, mode="lines", name="Monthly anomaly")
    fig.add_scatter(x=anom.index, y=line, mode="lines", name="Sen's trend", line=dict(width=3, dash="dash"))
    fig.update_layout(height=380, yaxis_title=f"Anomaly ({vc['label']})", margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)


def tab_station():
    st.subheader("Pi station vs satellite")
    site = st.selectbox("Deployment site", RISK["site_id"],
                        index=int(RISK.index[RISK.site_id == CFG["station"]["site_id"]][0])
                        if (RISK.site_id == CFG["station"]["site_id"]).any() else 0,
                        format_func=lambda r: RISK.set_index("site_id").loc[r, "name"])
    sat = RISK[RISK.site_id == site].iloc[0]
    events = compare.load_events(CFG["station"]["log_dir"])
    summ = compare.station_summary(events, site)

    left, right = st.columns(2)
    with left:
        st.markdown("**Satellite**")
        st.metric("Status", sat["status"])
        st.metric("Risk class", f"{sat['risk_class']} ({sat['risk']:.2f})")
        st.metric("SST trend", f"{sat['slope_per_year']:+.3f} deg C/yr")
    with right:
        st.markdown("**Pi station**")
        if not summ:
            st.info("No events logged for this site yet. In a terminal run:\n\n"
                    "`python -m station.reef_station --demo --bleach 0.0`")
            return
        latest = summ["latest"]
        st.metric("Latest class", summ["latest_class"], f"BI {float(latest['bleaching_index']):.2f}")
        img = data_io.ROOT / CFG["station"]["log_dir"] / "images" / latest["image_filename"]
        if img.exists():
            st.image(str(img), caption=latest["image_filename"])
        if "DEMO" in latest.get("notes", ""):
            st.caption("DEMO MODE: image comes from a fake camera, not a real reef.")

    verdict = compare.concordance(sat["risk_class"], summ["latest_class"])
    st.success(f"Concordance: {verdict}")
    st.caption("Consistent = satellite risk High and the station sees paling/bleaching, or risk Low and healthy. "
               "A tabletop model cannot validate a regional trend; this demonstrates the ground-truthing workflow.")
    st.dataframe(pd.DataFrame(events)[::-1].head(20), use_container_width=True, hide_index=True)


def tab_export():
    st.subheader("Export")
    st.download_button("Download risk and trend summary (CSV)", RISK.to_csv(index=False),
                       file_name="reefline_trend_summary.csv", mime="text/csv")
    for name, df in RESULTS.items():
        st.download_button(f"Download {name} trend statistics (CSV)", df.to_csv(index=False),
                           file_name=f"reefline_{name}_trends.csv", mime="text/csv", key=name)


# Add a tab by writing a function above and adding it here.
TABS = [("Map", tab_map), ("Reef detail", tab_detail), ("Station", tab_station), ("Export", tab_export)]

st.title("Reefline")
st.caption("Satellite trend detective + Raspberry Pi reef station")
for tab, (_, fn) in zip(st.tabs([n for n, _ in TABS]), TABS):
    with tab:
        fn()
