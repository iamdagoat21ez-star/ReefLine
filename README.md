# ReefLine

Analyze reef trends, choose a field station and export a survey recommendation.

From the repository root, use Python 3.10+ in a virtual environment:

```sh
python -m pip install streamlit plotly scipy pymannkendall pillow pandas numpy
python -m streamlit run app.py
```

Start with SST and the default 2016-onward period. Select a significantly warming reef, compare its three ranked matches and choose a deployment site. Full-record SST has only one eligible candidate. The dashboard requires three to proceed. Changing the analysis period recomputes the monthly climatology, test and slope.

The processed series in data/sst and data/chlorophyll accompany NASA Giovanni MODIS-Aqua downloads in data/raw. The Mann–Kendall test uses calendar-month anomalies. Candidate reefs have p ≥ 0.05 and are ranked by slope difference (60%) and geographic distance (40%). The recommended action is a prototype survey priority.

## Station workflow

Use the command shown under **Connect the station** for the selected reef. On a Pi, install the system picamera2 package. For a USB webcam install opencv-python and use --demo. A camera-free trial uses --fake-image and records a gray test frame. Copy the station/logs directory including its images to the same location on the dashboard computer and click **Refresh station log**. **Export Action Report** downloads the selected site's statistics, priority, action and latest event metadata.
