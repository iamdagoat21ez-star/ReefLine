# ReefLine

Analyze reef trends, choose a field station and export a survey recommendation.

From the repository root, use Python 3.10+ in a virtual environment:

```sh
python -m pip install streamlit plotly scipy pymannkendall pillow pandas numpy
python -m streamlit run app.py
```

Start with SST, Great Barrier Reef and the default 2021-onward period. Select a significantly warming reef, compare its three ranked matches and choose a deployment site. Full-record SST has only one eligible candidate. The dashboard requires three to proceed. Changing the analysis period recomputes the monthly climatology, test and slope.

The processed series in data/sst and data/chlorophyll accompany NASA Giovanni MODIS-Aqua downloads in data/raw. The Mann–Kendall test uses calendar-month anomalies. Candidate reefs have p ≥ 0.05 and are ranked by slope difference (60%) and geographic distance (40%). The recommended action is a prototype survey priority.

## Station workflow

Use the command shown under **Connect the station** for the selected reef. On a Pi, install the system picamera2 package. For a USB webcam install opencv-python and use --demo. A camera-free trial uses --fake-image and records a gray test frame. Copy the station/logs directory including its images to the same location on the dashboard computer and click **Refresh station log**. **Export Action Report** downloads the selected site's statistics, priority, action and latest event metadata.


## Responsive observatory

The main dashboard combines an Esri satellite map, measured NASA trends, a responsive SVG reef scene, hardware and budget sliders, illustrative species charts and a coral-cover scenario. Hardware toggles update the scene, map halos, budget and cover projections. Choose **3 reefs → Deploy** to select one of exactly three non-significant candidates, view station imagery and export its action report. **Fit matches** includes globally ranked candidates in the map bounds.

The Indonesian and East African views contain no local monthly records in this catalog. They provide clearly labeled synthetic demo locations. Measured-only mode shows unavailable telemetry in those views. Species cover, pH/disease zones, biological benefits and projected coral cover are illustrative scenarios. The historical chart uses available dates, not an assumed 1985 start. Chlorophyll risk proxies show the latest value's empirical percentile in the selected period.

Budget uses one buoy ($145) and one film ($65) per paired unit plus ceil(units / 4) Pi nodes ($185), gated by the hardware toggles. Cost per area uses a 672 m² scenario sector times selected coverage.

To build a self-contained static snapshot, run:

```sh
python dashboard_data.py
python -m http.server 8513 --directory dist
```

Static snapshots exclude local Pi camera records. The Streamlit application reads station/logs and refreshes its cached data when events.csv changes. Reload the dashboard after syncing a new Pi event.


## Location explorer

The catalog includes 300 locations across 36 regions: the original 12 NASA stations and 288 fictional demo reefs. Demo names, coordinates and monthly series are generated deterministically by satellite/demo.py. They are labeled in the map, inspector, historical chart, deployment view and CSV exports. The Location data filter switches between all, measured-only and demo-only views.

Both evidence types use the same Mann–Kendall, Sen slope and candidate-ranking pipeline. Matching pools remain separate, so measured NASA references receive measured candidates. Demo locations support deployment rehearsal without claiming a live station connection.

Use the sidebar shortcuts for Locations, Data, Layers and Hardware. The three-step navigation above the map follows reference selection, comparison of exactly three candidates, then Pi deployment and Action Report export. Browse all opens the searchable region directory. Quick guide explains controls, labels and data provenance.
