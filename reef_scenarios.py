from base64 import b64encode
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st


def show_scenarios():
    with st.container(key="projection"):
        st.subheader("Projected Live Coral Cover (%)")
        st.markdown("**With Solutions vs. No Action · 2020–2040**")
        st.caption("Illustrative scenarios from the design reference. All three share a baseline through 2024. Values are independent of the selected reef’s satellite record.")
        years = list(range(2020, 2041, 2))
        chart = go.Figure()
        for label, end, color, dash in (
            ("With Solutions", 59.5, "#00e590", "solid"),
            ("Partial Action", 33.0, "#ffd000", "dot"),
            ("No Action", 8.4, "#ff445c", "dash"),
        ):
            values = [41, 39.5, 38] + [38 + (end - 38) * (y - 2024) / 16 for y in years[3:]]
            chart.add_scatter(x=years, y=values, name=label, mode="lines+markers",
                              line=dict(color=color, dash=dash, width=3), marker_size=8,
                              fill="tozeroy" if dash == "solid" else None, fillcolor="rgba(0,229,144,.13)",
                              hovertemplate="%{y:.1f}%")
        chart.update_layout(height=330, margin=dict(l=8,r=12,t=0,b=12),
                            paper_bgcolor="#08192b", plot_bgcolor="#08192b", font_color="#d7e7f4",
                            hovermode="x unified", legend=dict(orientation="h",y=1.15),
                            xaxis=dict(dtick=2,gridcolor="#20374b"),
                            yaxis=dict(range=[0,75],ticksuffix="%",title="Live coral cover",gridcolor="#20374b"))
        st.plotly_chart(chart, theme=None, width="stretch")
    assets = Path(__file__).parent
    artwork = b64encode((assets / "assets/restored-reef.png").read_bytes()).decode("ascii")
    scene = (assets / "reef_scene.html").read_text()
    st.iframe(scene.replace("REEF_PNG", artwork), height="content", alt="Live Interactive Reef Visualizer")
