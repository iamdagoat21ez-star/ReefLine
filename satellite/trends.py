"""Mann–Kendall trend test and Sen's slope for monthly reef series.

Series are read from the CSVs in data/sst and data/chlorophyll. The reef
registry records each file's data_source. Tests run on anomalies: the mean of
each calendar month is removed first when the series is monthly.
"""
from pathlib import Path

import pandas as pd
import pymannkendall as mk
from scipy.stats import theilslopes

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ALPHA = 0.05

# Worsening is an increase: warming SST, or rising chlorophyll-a.
VARIABLES = {
    "sst": {"folder": "sst", "column": "sst_c", "worsening": "increasing"},
    "chlorophyll": {"folder": "chlorophyll", "column": "chl_mg_m3", "worsening": "increasing"},
}


def load_reefs() -> pd.DataFrame:
    """Read data/reefs.csv. Required columns: site_id, name, lat, lon, region."""
    reefs = pd.read_csv(DATA_DIR / "reefs.csv")
    required = ["site_id", "name", "lat", "lon", "region"]
    missing = [column for column in required if column not in reefs.columns]
    if missing:
        raise ValueError(f"reefs.csv is missing columns: {missing}")
    return reefs


def load_series(site_id: str, variable: str) -> pd.Series:
    """Read one monthly series with pandas.read_csv."""
    spec = _variable(variable)
    path = DATA_DIR / spec["folder"] / f"{site_id}.csv"
    frame = pd.read_csv(path)
    if "date" not in frame.columns or spec["column"] not in frame.columns:
        raise ValueError(f"{path.name} must have columns date and {spec['column']}")
    frame["date"] = pd.to_datetime(frame["date"])
    series = frame.set_index("date")[spec["column"]].astype(float).sort_index()
    series.name = spec["column"]
    return series


def deseasonalize(series: pd.Series) -> pd.Series:
    """Subtract the mean of each calendar month. Leave non-monthly series unchanged."""
    if not _is_monthly(series.index):
        return series.copy()
    anomaly = series - series.groupby(series.index.month).transform("mean")
    anomaly.name = series.name
    return anomaly


def analyze_series(series: pd.Series, alpha: float = ALPHA) -> dict:
    """Test one series. Returns direction, p-value, slope per year, and significance."""
    anomalies = deseasonalize(series).dropna()
    if len(anomalies) < 3:
        raise ValueError("A trend test needs at least 3 observations")
    years = _year_axis(anomalies.index)
    test = mk.original_test(anomalies.to_numpy(), alpha=alpha)
    slope = float(theilslopes(anomalies.to_numpy(), years).slope)
    p_value = float(test.p)
    return {
        "direction": test.trend,
        "p_value": p_value,
        "slope_per_year": slope,
        "significant": p_value < alpha,
    }


def analyze_site(site_id: str, variable: str, alpha: float = ALPHA) -> dict:
    """Analyze one reef. worsening is True only for a significant increase."""
    spec = _variable(variable)
    result = analyze_series(load_series(site_id, variable), alpha=alpha)
    result.update({
        "site_id": site_id,
        "variable": variable,
        "worsening": result["significant"] and result["direction"] == spec["worsening"],
    })
    return result


def analyze_all(variable: str, alpha: float = ALPHA) -> pd.DataFrame:
    """One row per reef in data/reefs.csv."""
    reefs = load_reefs()
    rows = [analyze_site(site_id, variable, alpha=alpha) for site_id in reefs["site_id"]]
    return pd.DataFrame(rows)


def _variable(variable: str) -> dict:
    try:
        return VARIABLES[variable]
    except KeyError:
        known = ", ".join(VARIABLES)
        raise ValueError(f"Unknown variable {variable!r}. Expected one of: {known}") from None


def _is_monthly(index) -> bool:
    if not isinstance(index, pd.DatetimeIndex) or len(index) < 2:
        return False
    gaps = index.to_series().diff().dt.days.dropna()
    return bool(gaps.between(28, 31).all())


def _year_axis(index: pd.DatetimeIndex):
    months = (index.year - index[0].year) * 12 + (index.month - index[0].month)
    return months / 12.0
