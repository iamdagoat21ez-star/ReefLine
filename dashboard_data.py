"""Compute the dashboard's measured telemetry and three-site recommendations."""
import base64
import json
from pathlib import Path

import pandas as pd
from scipy.stats import theilslopes

from satellite import similar, trends

ROOT = Path(__file__).resolve().parent
PERIODS = {"2016": "2016", "2021": "2021", "full": None}


def build_dataset(include_observations=True):
    sites = []
    registry = trends.load_reefs()
    for reef in registry.to_dict("records"):
        measurements = {}
        for variable in trends.VARIABLES:
            series = trends.load_series(reef["site_id"], variable).dropna()
            analyses = {}
            for period, start in PERIODS.items():
                window = series.loc[start:]
                result = trends.analyze_series(window)
                anomalies = trends.deseasonalize(window)
                years = trends._year_axis(anomalies.index)
                fit = theilslopes(anomalies.to_numpy(), years)
                result.update(
                    worsening=result["significant"] and result["direction"] == "increasing",
                    low_slope=float(fit.low_slope), high_slope=float(fit.high_slope),
                    start=window.index.min().strftime("%Y-%m"),
                    end=window.index.max().strftime("%Y-%m"),
                    months=len(window),
                )
                analyses[period] = result
            measurements[variable] = {
                "monthly": [[date.strftime("%Y-%m-%d"), float(value)] for date, value in series.items()],
                "analysis": analyses,
            }
        sites.append(dict(reef, measurements=measurements))
    matches = {}
    for variable in trends.VARIABLES:
        matches[variable] = {}
        for period in PERIODS:
            table = pd.DataFrame([
                dict(site_id=site["site_id"], lat=site["lat"], lon=site["lon"],
                     name=site["name"], region=site["region"],
                     **site["measurements"][variable]["analysis"][period])
                for site in sites
            ])
            pool = {}
            for site in table.loc[table.worsening, "site_id"]:
                if (~table.significant).sum() >= 3:
                    pool[site] = similar.find_similar(site, variable, trends=table).to_dict("records")
            matches[variable][period] = pool
    observations = {}
    if include_observations:
        log_dir = ROOT / "station/logs"
        try:
            events = pd.read_csv(log_dir / "events.csv")
            events["_time"] = pd.to_datetime(events.timestamp, utc=True, errors="coerce")
            for site_id, group in events.dropna(subset=["_time"]).groupby("site_id"):
                event = group.sort_values("_time").iloc[-1]
                path = (log_dir / str(event.image_filename)).resolve()
                if not path.is_relative_to(log_dir.resolve()):
                    continue
                entry = {key: event[key] for key in ["timestamp", "site_id", "motion_value", "image_filename"]}
                if path.is_file():
                    entry["image"] = "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()
                observations[site_id] = entry
        except (OSError, ValueError, AttributeError):
            pass
    return dict(sites=sites, matches=matches, observations=observations,
                source="NASA Giovanni · MODIS-Aqua monthly 4 km",
                periods=PERIODS)


def render_dashboard(dataset):
    template = (ROOT / "web/index.html").read_text()
    template = template.replace("__REEF_DATA__", json.dumps(dataset, allow_nan=False).replace("<", "\\u003c"))
    template = template.replace('<link rel="stylesheet" href="vendor/leaflet.css">',
                                "<style>" + (ROOT / "web/vendor/leaflet.css").read_text() + "</style>")
    for library in ["leaflet.js", "plotly.min.js"]:
        template = template.replace(f'<script src="vendor/{library}"></script>',
                                    "<script>" + (ROOT / "web/vendor" / library).read_text() + "</script>")
    return template


if __name__ == "__main__":
    import shutil
    destination = ROOT / "dist"
    destination.mkdir(exist_ok=True)
    # Hosted exports exclude local field camera records.
    html = (ROOT / "web/index.html").read_text().replace(
        "__REEF_DATA__", json.dumps(build_dataset(include_observations=False), allow_nan=False).replace("<", "\\u003c"))
    (destination / "index.html").write_text(html)
    shutil.copytree(ROOT / "web/vendor", destination / "vendor", dirs_exist_ok=True)
    print("Built dist/index.html with measured satellite statistics and no local camera records.")
