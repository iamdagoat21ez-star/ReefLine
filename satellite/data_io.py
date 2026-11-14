"""Centralized configuration and CSV access for Reefline."""
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_REEF_COLUMNS = {"site_id", "name", "lat", "lon", "region"}

def load_config(path="config.yaml"):
    with open(ROOT / path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_reefs():
    """Load candidate reef sites. data_source is optional but recommended provenance."""
    path = ROOT / "data" / "reefs.csv"
    if not path.exists():
        raise FileNotFoundError(f"Reef registry not found: {path}")
    reefs = pd.read_csv(path)
    missing = REQUIRED_REEF_COLUMNS - set(reefs.columns)
    if missing:
        raise ValueError(f"data/reefs.csv is missing required columns: {sorted(missing)}")
    if reefs["site_id"].isna().any() or reefs["site_id"].duplicated().any():
        raise ValueError("data/reefs.csv site_id values must be present and unique")
    for col in ("lat", "lon"):
        reefs[col] = pd.to_numeric(reefs[col], errors="raise")
    if not reefs["lat"].between(-90, 90).all() or not reefs["lon"].between(-180, 180).all():
        raise ValueError("Reef coordinates are outside valid latitude/longitude ranges")
    if "data_source" not in reefs.columns:
        reefs["data_source"] = "unspecified"
    return reefs

def load_series(variable_cfg, site_id):
    """Return a monthly Series indexed by month start, or None if its CSV is absent."""
    path = ROOT / variable_cfg["folder"] / f"{site_id}.csv"
    if not path.exists():
        return None
    value_col = variable_cfg["value_col"]
    df = pd.read_csv(path, parse_dates=["date"])
    if not {"date", value_col}.issubset(df.columns):
        raise ValueError(f"{path} must contain date and {value_col}")
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    return df.set_index("date")[value_col].resample("MS").mean()
