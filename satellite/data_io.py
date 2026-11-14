#!/usr/bin/env python3
"""
satellite/data_io.py — Minimal implementations to enable app launch.

Provides the functions referenced by app.py:
- load_config() — returns a config dict/object
- load_series(variable, site_id) — loads processed CSV series
"""

import pathlib
from pathlib import Path

import pandas as pd

DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data"


def load_config():
    """Return a minimal config dict matching what app.py expects from data_io.load_config()."""
    return {
        "variables": {
            "sst": {
                "label": "SST (deg C)",
                "unit": "deg C",
                "folder": "sst",
                "column": "sst_c",
            },
            "chlorophyll": {
                "label": "Chlorophyll-a (mg/m³)",
                "unit": "mg/m³",
                "folder": "chlorophyll",
                "column": "chl_mg_m3",
            },
        },
        "risk": {
            "variable": "chlorophyll",
            "alpha": 0.05,
            "site_id": "reef_001",
        },
        "station": {
            "site_id": "reef_001",
            "log_dir": "logs",
        },
    }


def load_series(variable: str, site_id: str) -> pd.Series:
    """Load a processed monthly series for one reef and variable.

    Expects the CSV contract from data/contracts.md:
      - data/sst/<site_id>.csv  → columns: date, sst_c
      - data/chlorophyll/<site_id>.csv  → columns: date, chl_mg_m3
    """
    spec = {"sst": "sst_c", "chlorophyll": "chl_mg_m3"}[variable]
    path = DATA_DIR / variable / f"{site_id}.csv"

    frame = pd.read_csv(path)
    if "date" not in frame.columns or spec not in frame.columns:
        raise ValueError(f"{path.name} must have columns date and {spec}")

    frame["date"] = pd.to_datetime(frame["date"])
    series = frame.set_index("date")[spec].astype(float).sort_index()
    series.name = spec
    return series


def load_reefs():
    """Read data/reefs.csv. Required columns: site_id, name, lat, lon, region."""
    reefs = pd.read_csv(DATA_DIR / "reefs.csv")
    required = ["site_id", "name", "lat", "lon", "region"]
    missing = [column for column in required if column not in reefs.columns]
    if missing:
        raise ValueError(f"reefs.csv is missing columns: {missing}")
    return reefs


def load_site_series(vc: dict, site_id: str) -> pd.Series:
    """Legacy-friendly wrapper: load series given a variable config dict and site_id."""
    return load_series(vc["folder"], site_id)