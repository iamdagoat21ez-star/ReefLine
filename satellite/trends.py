"""Mann–Kendall trend test and Sen's slope for monthly reef series.

Series are read from data/sst and data/chlorophyll. Those tables are monthly
means of the NASA Giovanni MODIS-Aqua downloads in data/raw. Tests run on
anomalies: the mean of each calendar month is removed first when the series
is monthly.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy.stats import theilslopes

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ALPHA = 0.05

# Worsening definition:
# - SST: significant decrease = worsening (cooling stress for coral reefs)
# - Chlorophyll: significant increase = worsening (rising chlorophyll-a)
VARIABLES = {
    "sst": {"folder": "sst", "column": "sst_c", "worsening": "decreasing"},
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


def _is_timestamp_column(col_name: str) -> bool:
    """Check if a column name looks like a timestamp/datetime string."""
    import re
    # Check for common timestamp patterns
    patterns = [
        r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$',  # '2002-08-06 15:25:00'
        r'^\d{4}-\d{2}-\d{2}$',  # '2002-08-06'
        r'^\d{2}/\d{2}/\d{4}$',  # '08/06/2002'
    ]
    for pattern in patterns:
        if re.match(pattern, str(col_name)):
            return True
    return False


def _detect_measurement_column(frame: pd.DataFrame) -> str:
    """Dynamically find the measurement column in a NASA Giovanni CSV.

    Priority: columns containing MODISA, NSST, CHL, CHLOR, or CHLOR_A.
    If only 2 columns and first is a timestamp, use the second column.
    Falls back to any column with 'mean_' prefix.
    Last resort: first column that can be converted to float.
    """
    meas_keywords = ['MODISA', 'NSST', 'CHL', 'CHLOR', 'CHLOR_A']

    # First try exact keyword match
    for kw in meas_keywords:
        for c in frame.columns:
            if kw in c.upper():
                return c

    # If only 2 columns and first is a timestamp, use the second column
    if len(frame.columns) == 2 and _is_timestamp_column(frame.columns[0]):
        return frame.columns[1]

    # Fall back to 'mean_' prefix
    for c in frame.columns:
        if 'mean_' in c.lower():
            return c

    # Last resort: first numeric column
    for c in frame.columns:
        try:
            frame[c].astype(float)
            return c
        except (ValueError, TypeError):
            continue

    # If all else fails, return the last column
    return frame.columns[-1]


def _skip_nasa_metadata(path: Path) -> int:
    """Detect and return the number of metadata rows to skip in a NASA Giovanni CSV.

    The format has 8 metadata rows: Title, User Start/End, Bounding Box,
    URL, Fill Value, then the data header row (containing 'time' or 'date').
    We skip all rows up to and including the header row, so read starts
    from the first data row after the header.

    Strategy: Read all lines, find the line that is the actual data header
    (has 'time' as the first column name followed by a measurement column name).
    """
    with open(path, 'r') as f:
        lines = f.readlines()

    # Find the data header row - it's the line that contains 'time,' pattern
    # (time as first column followed by comma and measurement column name)
    # or is at position 8 (0-indexed) after 8 metadata rows
    data_header_row = None
    for i, line in enumerate(lines):
        # Check for data header: "time, mean_..." or just "time, ..."
        # Avoid matching URL lines that contain 'starttime' or 'endtime'
        lower_line = line.lower()
        if 'time,' in lower_line and not lower_line.startswith('url'):
            # This is likely the data header row
            data_header_row = i
            break

    # Fallback: if not found by pattern, assume 8 metadata rows + header = 9 rows
    if data_header_row is None:
        data_header_row = 8

    # Return the number of rows to skip (all rows up to and including the header)
    return data_header_row + 1


def _parse_nasa_time_column(frame: pd.DataFrame) -> pd.Series:
    """Parse the time column from a NASA Giovanni CSV.

    The first (and only) data column contains timestamps like '2002-08-06 15:25:00'.
    Returns a datetime index.
    """
    # The first column has the timestamps
    time_col = frame.columns[0]
    dates = pd.to_datetime(frame[time_col])
    return dates


def load_series(site_id: str, variable: str, raw: bool = False) -> pd.Series:
    """Read one monthly series with pandas.read_csv.

    If raw=True, expects NASA Giovanni CSV format with 8 metadata rows
    and product-specific column names. Automatically detects skiprows,
    column names, and replaces -32767 fill values with NaN.

    If raw=False, expects processed CSV format with 'date' and the variable column.
    """
    spec = _variable(variable)
    path = DATA_DIR / spec["folder"] / f"{site_id}.csv"

    if raw:
        # Handle NASA Giovanni raw CSV format
        skip_rows = _skip_nasa_metadata(path)

        frame = pd.read_csv(path, skiprows=skip_rows)

        # Dynamically find the measurement column
        # The data has: timestamp column + measurement column
        # After skipping metadata, the first column is the time/date column
        col = _detect_measurement_column(frame)

        # Parse dates from the first column (time column)
        frame['date'] = _parse_nasa_time_column(frame)
        series = frame.set_index('date')[col].astype(float).sort_index()

        # Replace -32767 NASA fill values with NaN
        fill_mask = series == -32767
        if fill_mask.any():
            series = series.mask(fill_mask, np.nan)

        # Fill remaining NaN with column mean (ignoring NaN)
        if series.isna().any():
            col_mean = series.mean(skipna=True)
            if not np.isnan(col_mean):
                series = series.fillna(col_mean)

        # Set the proper column name based on variable type
        if variable == "sst":
            series.name = "sst_c"
        else:
            series.name = "chl_mg_m3"

        return series

    else:
        # Processed CSV format (existing behavior)
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


def analyze_site(site_id: str, variable: str, alpha: float = ALPHA, raw: bool = False) -> dict:
    """Analyze one reef. worsening is True only for a significant decrease (SST) or increase (chlorophyll)."""
    spec = _variable(variable)
    result = analyze_series(load_series(site_id, variable, raw=raw), alpha=alpha)
    result.update({
        "site_id": site_id,
        "variable": variable,
        "worsening": result["significant"] and result["direction"] == spec["worsening"],
    })
    return result


def analyze_all(variable: str, alpha: float = ALPHA, raw: bool = False) -> pd.DataFrame:
    """One row per reef in data/reefs.csv."""
    reefs = load_reefs()
    rows = [analyze_site(site_id, variable, alpha=alpha, raw=raw) for site_id in reefs["site_id"]]
    return pd.DataFrame(rows)


def _variable(variable: str) -> dict:
    try:
        return VARIABLES[variable]
    except KeyError:
        known = ", ".join(VARIABLES)
        raise ValueError(f"Unknown variable {variable!r}. Expected one of: {known}") from None


def _is_monthly(index) -> bool:
    """True for month-start series, including ones with a few missing months."""
    if not isinstance(index, pd.DatetimeIndex) or len(index) < 2:
        return False
    if bool((index.day == 1).all()):
        return True
    gaps = index.to_series().diff().dt.days.dropna()
    return bool(gaps.median() >= 28 and gaps.median() <= 31)


def _year_axis(index: pd.DatetimeIndex):
    months = (index.year - index[0].year) * 12 + (index.month - index[0].month)
    return months / 12.0
