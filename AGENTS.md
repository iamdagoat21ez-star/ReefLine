# Reefline – Agent Instructions

## Product Goal
Dual-system coral reef trend detective for the “Be an Earth System Trend Detective!” track.

1. User selects a reef that already shows a statistically significant worsening trend.
2. System returns exactly 3 candidate reefs with the most similar statistical profile that are not yet significant.
3. User picks one of the 3 as the Pi deployment site.
4. Raspberry Pi station records motion-triggered images and logs.
5. App shows side-by-side satellite statistics + latest Pi observation for that site.

## Statistical Requirements (Must Implement)
- Mann–Kendall test (`pymannkendall.original_test`) for trend significance.
- Sen’s slope (`scipy.stats.theilslopes`) for rate of change (reported per year).
- Results must include: trend direction, p-value, slope, and whether significant (p < 0.05).
- Deseasonalize series by subtracting monthly climatology before testing (when data is monthly).
- “Similar reefs” scoring:
  - 60 % weight on absolute difference in Sen’s slope
  - 40 % weight on geographic distance (prefer < 100 km)
  - Return exactly 3 non-significant reefs.

## Data Rules
data/
├── chlorophyll/reef_XXX.csv
├── sst/reef_XXX.csv
└── reefs.csv   # site_id,name,lat,lon,region

- Load only with pandas.read_csv.
- No cache, no raw NetCDF, no earthaccess required at runtime.

## Repository Structure
reefline/
├── data/
├── satellite/
│   ├── trends.py      # Mann–Kendall + Sen’s slope
│   └── similar.py     # find exactly 3 similar reefs
├── station/
│   └── reef_station.py
├── app.py             # Streamlit
├── requirements.txt
└── AGENTS.md

## Workstreams (Parallel)
- Satellite: only satellite/trends.py + satellite/similar.py
- Pi Station: only station/reef_station.py
- App: only app.py (wires the other two)

## Hard Rules
- Do not add features outside this document.
- Use real CSVs only.
- Table-top Pi demo is acceptable.
- Cite Giovanni or AppEEARS as data source.
