# Reefline – Agent Instructions

## Product Goal
Dual-system coral reef early-detection tool that also recommends action.

1. User selects a reef with a statistically significant worsening trend.
2. App returns exactly 3 candidate reefs with similar statistical profiles (not yet significant).
3. User picks one as the Pi deployment site.
4. Pi station captures motion-triggered images and logs them.
5. App shows satellite stats + Pi image side-by-side.
6. App displays a clear **Recommended Action** based on the risk level.

## Statistical Requirements
- Mann–Kendall + Sen’s slope on deseasonalized monthly series.
- Significant = p < 0.05.
- Similar reefs: 60 % slope difference + 40 % distance, return exactly 3.

## UI Requirements (Working Prototype)
- Clean Streamlit layout with sidebar controls.
- Interactive map showing significant reefs and at-risk matches.
- Time-series plot with Sen’s slope line.
- Trend summary cards (p-value, slope, direction).
- “Reefs at risk” section with the 3 candidates.
- Deployment site selector.
- Side-by-side satellite vs Pi panel.
- **Recommended Action** box that appears when a site is selected (e.g. “Prioritize for field survey within 30 days”).
- Export Action Report button (CSV or simple download).
- Data citation visible: NASA Giovanni / AppEEARS.

## Data & Structure
data/sst/, data/chlorophyll/, data/reefs.csv  
satellite/trends.py, satellite/similar.py  
station/reef_station.py  
app.py

## Rules
Build a working, demoable prototype. Prioritize clear UI and the action recommendation over extra features.