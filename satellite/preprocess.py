"""Small, deterministic preprocessing helpers for site-level observations."""
from __future__ import annotations
import pandas as pd

def monthly_mean(frame: pd.DataFrame, date_col: str, value_col: str) -> pd.DataFrame:
    """Aggregate observations to calendar-month means, returning date + value."""
    if date_col not in frame or value_col not in frame:
        raise ValueError(f"Expected columns {date_col!r} and {value_col!r}")
    data = frame[[date_col, value_col]].copy()
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce", utc=True).dt.tz_convert(None)
    data[value_col] = pd.to_numeric(data[value_col], errors="coerce")
    data = data.dropna(subset=[date_col, value_col]).sort_values(date_col)
    if data.empty:
        raise ValueError("No valid date/value observations remain after cleaning")
    out = data.set_index(date_col)[value_col].resample("MS").mean().dropna().reset_index()
    return out.rename(columns={date_col: "date"})

def write_site_monthly_csv(frame: pd.DataFrame, output_path, date_col: str, value_col: str) -> None:
    """Write one site's normalized monthly time series in Reefline CSV format."""
    monthly_mean(frame, date_col, value_col).to_csv(output_path, index=False, date_format="%Y-%m-%d")
