"""Reef trend detective. Run with: streamlit run app.py"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import theilslopes

from satellite import similar, trends

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "station" / "logs"
EVENT_FIELDS = ["timestamp", "site_id", "motion_value", "image_filename"]

VARIABLES = {
    "sst": {"label": "Sea surface temperature (°C)", "unit": "°C", "slope_unit": "°C/year"},
    "chlorophyll": {"label": "Chlorophyll-a (mg/m³)", "unit": "mg/m³", "slope_unit": "mg/m³/year"},
}
COLORS = {
    "Significant worsening": "#D7263D",
    "Early-detection match": "#F0A202",
    "No significant trend": "#2E9B4A",
    "Significant, other direction": "#4C78A8",
}


@st.cache_data(show_spinner="Running Mann–Kendall and Sen's slope on the NASA series…")
def load_analysis(variable: str) -> pd.DataFrame:
    reefs = trends.load_reefs()
    stats = trends.analyze_all(variable)
    return reefs.merge(stats, on="site_id", validate="one_to_one")


def format_p(p_value: float) -> str:
    if p_value < 0.001:
        return "< 0.001"
    return f"{p_value:.3f}"


def format_slope(slope: float, variable: str) -> str:
    digits = 3 if variable == "sst" else 4
    return f"{slope:+.{digits}f} {VARIABLES[variable]['slope_unit']}"


def direction_label(variable: str, direction: str, significant: bool) -> str:
    if not significant or direction == "no trend":
        return "No significant trend"
    if variable == "sst" and direction == "increasing":
        return "Warming (increasing)"
    if variable == "sst" and direction == "decreasing":
        return "Cooling (decreasing)"
    if direction == "increasing":
        return "Increasing"
    return "Decreasing"


def point_status(row, match_ids) -> str:
    if row["site_id"] in match_ids:
        return "Early-detection match"
    if bool(row["worsening"]):
        return "Significant worsening"
    if bool(row["significant"]):
        return "Significant, other direction"
    return "No significant trend"


def show_latest_observation(site_id: str) -> None:
    path = LOG_DIR / "events.csv"
    if not path.exists():
        st.info("No Pi observations yet. The station has not created events.csv.")
        return
    try:
        events = pd.read_csv(path, dtype={"site_id": str, "image_filename": str})
        if not set(EVENT_FIELDS).issubset(events.columns):
            st.warning("The station log must contain timestamp, site_id, motion_value, and image_filename.")
            return
        events = events.loc[events["site_id"] == site_id].copy()
        if events.empty:
            st.info("No Pi observations logged for this deployment site yet.")
            return
        events["_time"] = pd.to_datetime(events["timestamp"], utc=True, errors="coerce")
        events = events.dropna(subset=["_time"])
        if events.empty:
            st.warning("No valid timestamps in this site's station log.")
            return
        latest = events.sort_values("_time", kind="stable").iloc[-1]
        image_path = (LOG_DIR / str(latest["image_filename"])).resolve()
        if not image_path.is_relative_to(LOG_DIR.resolve()):
            st.warning("The logged image path is outside the station log directory.")
        elif image_path.is_file():
            st.image(str(image_path), caption=f"Latest observation: {latest['timestamp']}")
        else:
            st.info("The latest event's image is not available.")
        st.dataframe(latest[EVENT_FIELDS].to_frame().T, hide_index=True, width="stretch")
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        st.warning(f"Unable to read the latest Pi observation: {exc}")


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #071422; color: #e7eef6; }
        section[data-testid="stSidebar"] { background: #0c1b2e; border-right: 1px solid #17324a; }
        section[data-testid="stSidebar"] * { color: #d5e2ee; }
        h1, h2, h3, p, label, span { color: #e7eef6; }
        div[data-testid="stCaption"] { color: #9fb3c8; }
        .dashboard-title { font-size: 1.7rem; font-weight: 700; margin: 0; }
        .dashboard-sub { color: #9fb3c8; margin: 0.15rem 0 0.8rem; }
        .updated-pill {
            background: #10283f; border: 1px solid #1e4a38; border-radius: 999px;
            padding: 0.35rem 0.8rem; color: #b7ebc9; text-align: center;
        }
        .map-legend { color: #d5e2ee; font-size: 0.92rem; margin: 0.2rem 0 0.8rem; }
        .map-legend span { margin-right: 1rem; }
        .summary-card, .risk-card {
            background: #10243a; border: 1px solid #1e3a56; border-radius: 10px;
            padding: 0.75rem 0.9rem; margin-bottom: 0.55rem;
        }
        .summary-label, .risk-meta { color: #9fb3c8; font-size: 0.85rem; }
        .summary-value { font-size: 1.45rem; font-weight: 700; line-height: 1.2; }
        .summary-detail { color: #c5d4e4; font-size: 0.9rem; }
        .risk-card h4 { margin: 0 0 0.35rem; }
        .stat-hit { color: #f6c453; font-weight: 700; }
        .stat-plain { color: #d5e2ee; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def map_view(frame: pd.DataFrame) -> tuple[float, float, float]:
    lat_span = max(float(frame["lat"].max() - frame["lat"].min()), 6)
    mid_lat = float(frame["lat"].mean())
    lon_span = max(float(frame["lon"].max() - frame["lon"].min()) * np.cos(np.radians(mid_lat)), 6)
    span = max(lat_span, lon_span) * 1.8
    zoom = float(np.clip(np.log2(360 / span) - 0.4, 1.1, 5.2))
    return mid_lat, float(frame["lon"].mean()), zoom


def trend_map(frame: pd.DataFrame, selected: str | None, matches: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if selected and not matches.empty:
        chosen = frame.loc[frame["site_id"] == selected].iloc[0]
        latitudes, longitudes = [], []
        for _, match in matches.iterrows():
            latitudes.extend([float(chosen["lat"]), float(match["lat"]), None])
            longitudes.extend([float(chosen["lon"]), float(match["lon"]), None])
        fig.add_trace(go.Scattermap(
            lat=latitudes, lon=longitudes, mode="lines",
            line=dict(width=2, color="#F0A202"),
            name="Link to at-risk reef", hoverinfo="skip",
        ))
    for status, color in COLORS.items():
        group = frame.loc[frame["status"] == status]
        if group.empty:
            continue
        labeled = group["site_id"].eq(selected) | group["site_id"].isin(matches["site_id"] if not matches.empty else [])
        fig.add_trace(go.Scattermap(
            lat=group["lat"], lon=group["lon"],
            text=np.where(labeled, group["name"], ""),
            customdata=np.stack([
                group["name"], group["region"], group["direction"],
                group["p_value"].map(format_p),
                group["slope_per_year"].map(lambda value: f"{value:+.4f}"),
            ], axis=1),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>%{customdata[1]}"
                "<br>%{customdata[2]}"
                "<br>p-value: %{customdata[3]}"
                "<br>Sen's slope: %{customdata[4]} /year<extra></extra>"
            ),
            mode="markers+text",
            textposition="top center",
            name=status,
            marker=dict(
                size=[22 if site == selected else 14 for site in group["site_id"]],
                color=color,
                allowoverlap=True,
            ),
        ))
    center_lat, center_lon, zoom = map_view(frame)
    fig.update_layout(
        map=dict(style="carto-darkmatter", center=dict(lat=center_lat, lon=center_lon), zoom=zoom),
        height=520,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#071422",
        font=dict(color="#e7eef6"),
        showlegend=False,
    )
    return fig


def slope_interval(series: pd.Series) -> tuple[float, float]:
    anomalies = trends.deseasonalize(series).dropna()
    origin = anomalies.index[0]
    years = ((anomalies.index.year - origin.year) * 12 + (anomalies.index.month - origin.month)) / 12.0
    fitted = theilslopes(anomalies.to_numpy(), np.asarray(years, dtype=float))
    return float(fitted.low_slope), float(fitted.high_slope)


def series_chart(series: pd.Series, slope: float, variable: str, reef_name: str) -> go.Figure:
    annual = series.resample("YS").mean().dropna()
    years = annual.index.year.to_numpy(dtype=float)
    centered = years - float(years.mean())
    level = float(annual.mean())
    low_slope, high_slope = slope_interval(series)
    line = level + slope * centered
    low_line = level + low_slope * centered
    high_line = level + high_slope * centered
    unit = VARIABLES[variable]["unit"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(annual.index) + list(annual.index[::-1]),
        y=list(high_line) + list(low_line[::-1]),
        fill="toself", fillcolor="rgba(79, 163, 232, 0.28)",
        line=dict(color="rgba(0,0,0,0)"),
        name="Sen's 95% interval", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=annual.index, y=annual.to_numpy(), mode="lines+markers",
        name="Annual mean",
        line=dict(color="#7ec8f0", width=2),
        marker=dict(size=6, color="#7ec8f0"),
    ))
    fig.add_trace(go.Scatter(
        x=annual.index, y=line, mode="lines",
        name="Sen's slope",
        line=dict(color="#F0A202", width=3, dash="dash"),
    ))
    fig.add_annotation(
        xref="paper", yref="paper", x=0.98, y=0.98,
        xanchor="right", yanchor="top",
        text=f"Sen's slope: {format_slope(slope, variable)}<br>95% interval {low_slope:+.3f} to {high_slope:+.3f}",
        showarrow=False,
        bgcolor="#10243a", bordercolor="#1e3a56", borderpad=6,
        font=dict(color="#e7eef6", size=12),
    )
    fig.update_layout(
        title=dict(text=f"{VARIABLES[variable]['label'].split(' (')[0]}<br><sup>{reef_name}</sup>",
                   font=dict(color="#e7eef6", size=16)),
        height=380,
        margin=dict(l=64, r=12, t=64, b=52),
        paper_bgcolor="#0d2137",
        plot_bgcolor="#0d2137",
        font=dict(color="#d5e2ee"),
        yaxis_title=unit,
        legend=dict(orientation="h", y=-0.22, x=0, font=dict(color="#d5e2ee")),
        xaxis=dict(gridcolor="#1e3a56", showgrid=True),
        yaxis=dict(gridcolor="#1e3a56", showgrid=True, automargin=True),
    )
    return fig


def match_parts(match: pd.Series, reference_slope: float, variable: str) -> tuple[bool, bool, str]:
    slope_gap = abs(float(match["slope_diff"]))
    slope_scale = 0.01 if variable == "sst" else 0.001
    slope_close = slope_gap <= max(0.35 * abs(reference_slope), slope_scale)
    distance_close = float(match["distance_km"]) <= 1000
    if slope_close and distance_close:
        reason = "Both highlighted stats are similar: the Sen's slope and the distance."
    elif slope_close:
        reason = "Sen's slope is the similar part. The distance is not."
    elif distance_close:
        reason = "Distance is the similar part. The Sen's slopes differ."
    else:
        reason = "Listed because it is not yet significant. The slope and the distance are not close."
    return slope_close, distance_close, reason


def summary_card(label: str, value: str, detail: str, accent: str) -> None:
    st.markdown(
        f"""
        <div class="summary-card" style="border-left: 4px solid {accent}">
            <div class="summary-label">{label}</div>
            <div class="summary-value" style="color:{accent}">{value}</div>
            <div class="summary-detail">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="Reefline", layout="wide")
    apply_theme()
    st.sidebar.markdown("### Reefline")
    st.sidebar.caption("Satellite data tool")

    try:
        reefs = trends.load_reefs()
    except (OSError, ValueError) as exc:
        st.error(f"Unable to read the reef registry: {exc}")
        return

    regions = ["All regions", *sorted(reefs["region"].dropna().unique())]
    region = st.sidebar.selectbox("1. Select region", regions)
    variable = st.sidebar.selectbox(
        "2. Select variable", list(VARIABLES), format_func=lambda key: VARIABLES[key]["label"]
    )
    st.sidebar.markdown("**3. Trend options**")
    show_significant = st.sidebar.checkbox("Statistically significant trends (p < 0.05)", value=True)
    show_early = st.sidebar.checkbox("Show early-detection matches", value=True)
    st.sidebar.info(
        "Data source: NASA Giovanni, MODIS-Aqua monthly 4 km.\n\n"
        "Mann–Kendall and Sen's slope are calculated on the deseasonalized monthly series. "
        "A worsening trend is a significant increase (p < 0.05)."
    )

    try:
        table = load_analysis(variable)
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Unable to load reef trends: {exc}")
        return

    in_region = table if region == "All regions" else table.loc[table["region"] == region]
    worsening = in_region.loc[in_region["worsening"]].sort_values("site_id")
    names = table.set_index("site_id")["name"].to_dict()

    if worsening.empty:
        reference = None
        st.sidebar.warning("No reef in this region has a significant worsening trend for this variable.")
    else:
        reference = st.sidebar.selectbox(
            "Known worsening reef",
            worsening["site_id"].tolist(),
            format_func=lambda site: f"{names[site]} ({site})",
        )

    matches = pd.DataFrame(columns=similar._CANDIDATE_COLUMNS)
    if reference and show_early:
        try:
            matches = similar.rank_candidates(reference, variable, trends=table)
        except (OSError, ValueError, KeyError) as exc:
            st.error(f"Unable to rank early-detection reefs: {exc}")
    shown_matches = matches.head(3)
    match_ids = set(shown_matches["site_id"]) if show_early else set()

    mapped = table.copy()
    if region != "All regions":
        mapped = table.loc[table["region"].eq(region) | table["site_id"].isin(match_ids)].copy()
    mapped["status"] = mapped.apply(lambda row: point_status(row, match_ids), axis=1)
    if not show_significant:
        mapped = mapped.loc[
            ~mapped["status"].isin(["Significant worsening", "Significant, other direction"])
            | mapped["site_id"].eq(reference)
        ]
    if not show_early:
        mapped = mapped.loc[mapped["status"] != "Early-detection match"]

    title_region = "Global reefs" if region == "All regions" else region
    header, updated = st.columns([3, 1])
    with header:
        st.markdown(f'<p class="dashboard-title">{title_region} coral reef trend analysis</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="dashboard-sub">Satellite trends for a reef that is already worsening, and the reefs at risk of following it.</p>',
            unsafe_allow_html=True,
        )
    if reference:
        series = trends.load_series(reference, variable)
        updated.markdown(
            f'<div class="updated-pill">Data through {series.index.max():%b %Y}</div>',
            unsafe_allow_html=True,
        )
    else:
        updated.markdown('<div class="updated-pill">NASA Giovanni MODIS-Aqua</div>', unsafe_allow_html=True)

    if mapped.empty:
        st.info("No reefs to map with the current filters.")
    else:
        st.plotly_chart(trend_map(mapped, reference, shown_matches if show_early else shown_matches.iloc[0:0]), width="stretch")
    st.markdown(
        """
        <div class="map-legend">
            <span style="color:#D7263D">● Significant worsening (p &lt; 0.05)</span>
            <span style="color:#F0A202">● At-risk match, not yet significant</span>
            <span style="color:#2E9B4A">● No significant trend</span>
            <span style="color:#F0A202">- - Link to an at-risk reef</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if reference is None:
        return

    row = table.set_index("site_id").loc[reference]
    chart_col, summary_col = st.columns([1.7, 1], gap="medium")
    with chart_col:
        st.plotly_chart(
            series_chart(series, float(row["slope_per_year"]), variable, names[reference]),
            width="stretch",
        )
        st.caption(
            "Annual means are shown for reading. The test itself uses every deseasonalized month. "
            "The band is the 95% Sen's slope interval, not a new statistic."
        )
    with summary_col:
        st.markdown("### Trend summary")
        st.caption(f"{series.index.min():%Y}–{series.index.max():%Y}")
        summary_card(
            "Mann–Kendall p-value",
            format_p(float(row["p_value"])),
            "Statistically significant" if row["significant"] else "Not significant",
            "#7ec8f0",
        )
        summary_card("Sen's slope", format_slope(float(row["slope_per_year"]), variable),
                     "Rate of change per year", "#3DDC97")
        summary_card(
            "Trend direction",
            direction_label(variable, row["direction"], bool(row["significant"])),
            f"{len(series)} monthly NASA Giovanni values",
            "#D7263D" if row["worsening"] else "#9fb3c8",
        )

    if not show_early:
        return

    st.subheader(f"Reefs at risk from {names[reference]}")
    st.markdown(
        "Changing the worsening reef reruns the match. A reef is at risk here when it is **not yet significant** "
        "and its profile is close: **60% Sen's slope**, **40% distance**."
    )
    if shown_matches.empty:
        st.info("Every other reef is already significant, so there is no at-risk match.")
        return
    if len(matches) < 3:
        st.caption(
            f"Only {len(matches)} reef{'s' if len(matches) != 1 else ''} "
            f"{'are' if len(matches) != 1 else 'is'} not yet significant for this variable, "
            "so that is the full at-risk list."
        )
    cards = st.columns(len(shown_matches))
    for card, (_, match) in zip(cards, shown_matches.iterrows()):
        slope_close, distance_close, reason = match_parts(match, float(row["slope_per_year"]), variable)
        slope_class = "stat-hit" if slope_close else "stat-plain"
        distance_class = "stat-hit" if distance_close else "stat-plain"
        with card:
            st.markdown(
                f"""
                <div class="risk-card">
                    <h4>{match['name']}</h4>
                    <div class="{slope_class}">Sen's slope {format_slope(float(match['slope_per_year']), variable)}</div>
                    <div class="risk-meta">Selected reef {format_slope(float(row['slope_per_year']), variable)} · gap {float(match['slope_diff']):.4f}</div>
                    <div class="{distance_class}">{float(match['distance_km']):,.0f} km away</div>
                    <div class="risk-meta">p-value {format_p(float(match['p_value']))} · not yet significant</div>
                    <div class="summary-detail">{reason}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    display = shown_matches.copy()
    display["Sen's slope"] = display["slope_per_year"].map(lambda value: format_slope(value, variable))
    display["p-value"] = display["p_value"].map(format_p)
    display["Distance (km)"] = display["distance_km"].map(lambda value: f"{value:,.0f}")
    display["Slope gap"] = display["slope_diff"].map(lambda value: f"{value:.4f}")
    display["Match score"] = display["score"].map(lambda value: f"{value:.3f}")
    st.dataframe(
        display[["site_id", "name", "region", "Sen's slope", "p-value", "Distance (km)", "Slope gap", "Match score"]],
        hide_index=True, width="stretch",
    )
    st.caption("A lower match score is more similar. The score is comparable inside this candidate pool.")

    deployment = st.selectbox(
        "Deployment site",
        shown_matches["site_id"].tolist(),
        index=None,
        placeholder="Pick one early-detection reef for the Pi station",
        format_func=lambda site: f"{names.get(site, site)} ({site})",
    )
    if deployment is None:
        return

    st.subheader(f"Deployment: {names.get(deployment, deployment)}")
    satellite_col, pi_col = st.columns(2)
    satellite = table.set_index("site_id").loc[deployment]
    with satellite_col:
        st.markdown("**Satellite statistics**")
        st.metric("Direction", direction_label(variable, satellite["direction"], bool(satellite["significant"])))
        st.metric("Mann–Kendall p-value", format_p(float(satellite["p_value"])))
        st.metric("Sen's slope", format_slope(float(satellite["slope_per_year"]), variable))
        st.metric("Significant (p < 0.05)", "Yes" if satellite["significant"] else "No")
    with pi_col:
        st.markdown("**Latest Pi observation**")
        show_latest_observation(deployment)


if __name__ == "__main__":
    main()
