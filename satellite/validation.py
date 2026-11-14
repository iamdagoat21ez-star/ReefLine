"""Validation for Reefline's per-site monthly SST/chlorophyll CSV contract."""
from __future__ import annotations
from pathlib import Path
import pandas as pd

def validate_series_csv(path, value_col: str, min_months: int = 1) -> dict:
    path = Path(path)
    report = {"path": str(path), "valid": False, "errors": [], "rows": 0, "valid_months": 0, "missing_months": 0}
    if not path.exists():
        report["errors"].append("file does not exist")
        return report
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        report["errors"].append(f"could not read CSV: {exc}")
        return report
    required = {"date", value_col}
    if not required.issubset(df.columns):
        report["errors"].append(f"required columns are {sorted(required)}")
        return report
    report["rows"] = len(df)
    dates = pd.to_datetime(df["date"], errors="coerce")
    values = pd.to_numeric(df[value_col], errors="coerce")
    if dates.isna().any(): report["errors"].append("one or more dates are invalid")
    if values.isna().any(): report["errors"].append("one or more values are missing or non-numeric")
    valid = pd.DataFrame({"date": dates, "value": values}).dropna().sort_values("date")
    if valid["date"].duplicated().any(): report["errors"].append("duplicate dates are present")
    months = valid["date"].dt.to_period("M").drop_duplicates().sort_values()
    report["valid_months"] = int(len(months))
    if len(months):
        expected = pd.period_range(months.iloc[0], months.iloc[-1], freq="M")
        report["missing_months"] = int(len(expected.difference(months)))
    if report["valid_months"] < min_months:
        report["errors"].append(f"only {report['valid_months']} valid months; minimum is {min_months}")
    report["valid"] = not report["errors"]
    return report

def validate_registry(frame: pd.DataFrame) -> list[str]:
    required = {"site_id", "name", "lat", "lon", "region"}
    errors = []
    missing = required - set(frame.columns)
    if missing: errors.append(f"missing registry columns: {sorted(missing)}")
    elif frame["site_id"].isna().any() or frame["site_id"].duplicated().any():
        errors.append("site_id must be non-empty and unique")
    return errors
