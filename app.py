"""Simple reef trend detective. Run with: streamlit run app.py"""
from pathlib import Path

import pandas as pd
import streamlit as st

from satellite import similar, trends

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "station" / "logs"
EVENT_FIELDS = ["timestamp", "site_id", "motion_value", "image_filename"]
VARIABLE_LABELS = {"sst": "Sea surface temperature", "chlorophyll": "Chlorophyll-a"}
UNITS = {"sst": "°C/year", "chlorophyll": "mg/m³/year"}


def show_latest_observation(site_id):
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
        st.dataframe(latest[EVENT_FIELDS].to_frame().T, hide_index=True,
                     width="stretch")
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        st.warning(f"Unable to read the latest Pi observation: {exc}")


def main():
    st.set_page_config(page_title="Reefline", layout="wide")
    st.title("Reefline")
    st.caption("Data from NASA Giovanni / AppEEARS")
    variable = st.selectbox("Satellite variable", list(VARIABLE_LABELS),
                            format_func=VARIABLE_LABELS.get)
    try:
        reefs = trends.load_reefs()
        results = trends.analyze_all(variable)
        table = reefs.merge(results, on="site_id", validate="one_to_one")
    except (OSError, ValueError, KeyError) as exc:
        st.error(f"Unable to load reef trends: {exc}")
        return
    if table.empty:
        st.info("No reefs are available in data/reefs.csv.")
        return
    if "data_source" in reefs and reefs["data_source"].astype(str).str.contains(
        "synthetic", case=False, na=False
    ).any():
        st.warning("The current CSV registry labels data as synthetic_demo. Replace these CSVs with real NASA data before interpreting the results.")

    st.subheader("Reef trends")
    map_data = table[["lat", "lon"]].copy()
    map_data["color"] = table["worsening"].map({True: "#D7263D", False: "#8D99AE"})
    st.map(map_data, latitude="lat", longitude="lon", color="color")
    st.caption("Red: significant worsening trend (p < 0.05). Gray: other reefs.")

    eligible = table.loc[table["worsening"], "site_id"].tolist()
    if not eligible:
        st.info("No reefs have a significant worsening trend for this variable.")
        return
    names = table.set_index("site_id")["name"].to_dict()
    reference = st.selectbox("Significant worsening reef", eligible,
                             format_func=lambda site: f"{names[site]} ({site})")
    context = (variable, reference)
    if st.session_state.get("candidate_context") != context:
        st.session_state["candidate_context"] = context
        st.session_state.pop("candidate_ids", None)
        st.session_state.pop("deployment_site", None)

    if st.button("Find 3 Similar"):
        st.session_state.pop("candidate_ids", None)
        st.session_state.pop("deployment_site", None)
        try:
            candidates = similar.find_similar(reference, variable)
            if (len(candidates) != 3 or candidates["site_id"].nunique() != 3
                    or candidates["significant"].any()):
                raise ValueError("Expected exactly 3 distinct non-significant candidate reefs.")
            st.session_state["candidate_ids"] = candidates["site_id"].tolist()
        except (OSError, ValueError, KeyError) as exc:
            st.error(f"Unable to find 3 similar reefs: {exc}")

    candidate_ids = st.session_state.get("candidate_ids")
    if not candidate_ids:
        return
    indexed = table.set_index("site_id", drop=False)
    if any(site not in indexed.index or bool(indexed.loc[site, "significant"])
           for site in candidate_ids):
        st.session_state.pop("candidate_ids", None)
        st.session_state.pop("deployment_site", None)
        st.info("The reef data changed. Click Find 3 Similar again.")
        return
    candidates = indexed.loc[candidate_ids]
    st.subheader("3 candidate reefs")
    st.dataframe(candidates[["site_id", "name", "region", "direction", "p_value",
                             "slope_per_year", "significant"]],
                 hide_index=True, width="stretch")
    st.caption(f"Ranked by 60% slope difference and 40% geographic distance. Slopes in {UNITS[variable]}.")
    deployment = st.selectbox("Deployment site", candidate_ids, index=None,
                              placeholder="Pick one of the 3 candidates",
                              format_func=lambda site: f"{names[site]} ({site})",
                              key="deployment_site")
    if deployment is None:
        return
    st.subheader(f"Deployment: {names[deployment]}")
    left, right = st.columns(2)
    with left:
        st.markdown("**Satellite statistics**")
        satellite = indexed.loc[deployment]
        st.metric("Direction", satellite["direction"])
        st.metric("p-value", f"{satellite['p_value']:.6g}")
        st.metric("Sen's slope", f"{satellite['slope_per_year']:.6g} {UNITS[variable]}")
        st.metric("Significant (p < 0.05)", "Yes" if satellite["significant"] else "No")
    with right:
        st.markdown("**Latest Pi observation**")
        show_latest_observation(deployment)


if __name__ == "__main__":
    main()
