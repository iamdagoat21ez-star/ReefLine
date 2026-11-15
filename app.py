"""Run the complete ReefLine dashboard with streamlit run app.py."""
import streamlit as st

from dashboard_data import ROOT, build_dataset, render_dashboard

st.set_page_config(
    page_title="ReefLine · Coral Reef Trend Analysis", layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown("""
<style>
[data-testid="stHeader"],[data-testid="stToolbar"] {display:none}
.stMainBlockContainer {padding:0!important;max-width:none!important}
[data-testid="stVerticalBlock"] {gap:0}
iframe {display:block;width:100%;height:100dvh!important;border:0}
.stApp {background:#e3effc}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner="Analyzing monthly satellite records…")
def satellite_snapshot(log_modified):
    return build_dataset()


log = ROOT / "station/logs/events.csv"
log_modified = log.stat().st_mtime_ns if log.exists() else None
st.iframe(render_dashboard(satellite_snapshot(log_modified)), height=1100, alt="ReefLine scientific dashboard")
