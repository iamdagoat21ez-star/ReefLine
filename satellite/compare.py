#!/usr/bin/env python3
"""
satellite/compare.py — Minimal implementations to enable app launch.

Provides the functions referenced by app.py:
- load_events(log_dir) — loads station event log CSV
- station_summary(events, site) — summarizes events for a site
- concordance(risk_class, station_class) — checks consistency
"""

import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_events(log_dir: str) -> pd.DataFrame:
    """Load station event log from outputs/logs/events.csv.

    Expected columns: site_id, image_filename, bleaching_index, notes, timestamp
    """
    path = ROOT / "outputs" / "logs" / "events.csv"
    if not path.exists():
        return pd.DataFrame(columns=["site_id", "image_filename", "bleaching_index",
                                      "notes", "timestamp"])
    df = pd.read_csv(path)
    # Ensure required columns exist
    for col in ["site_id", "image_filename", "bleaching_index", "notes", "timestamp"]:
        if col not in df.columns:
            df[col] = ""
    return df


def station_summary(events: pd.DataFrame, site: str) -> dict:
    """Return a summary dict for a given site.

    Keys: latest (dict with image_filename, bleaching_index, notes),
           latest_class (str: 'Bleached', 'Pale', 'Healthy'),
           event_count (int).
    """
    site_events = events[events["site_id"] == site] if not events.empty else pd.DataFrame()
    if site_events.empty:
        return {"latest": None, "latest_class": "Healthy", "event_count": 0}

    # Sort by timestamp descending if available
    if "timestamp" in site_events.columns and not site_events["timestamp"].empty:
        site_events = site_events.sort_values("timestamp", ascending=False)

    latest = site_events.iloc[0].to_dict()

    # Determine class from bleaching_index
    bi = latest.get("bleaching_index")
    try:
        bi_float = float(bi) if bi is not None and bi != "" else 0.0
    except (ValueError, TypeError):
        bi_float = 0.0

    if bi_float >= 0.8:
        latest_class = "Bleached"
    elif bi_float >= 0.3:
        latest_class = "Pale"
    else:
        latest_class = "Healthy"

    return {
        "latest": latest,
        "latest_class": latest_class,
        "event_count": len(site_events),
    }


def concordance(risk_class: str, station_class: str) -> str:
    """Return a human-readable concordance verdict.

    Consistent = satellite risk High and station sees paling/bleaching,
    or risk Low and station sees healthy.
    """
    if risk_class == "High" and station_class in ("Bleached", "Pale"):
        return "Consistent (High risk + bleaching/paling observed)"
    if risk_class == "Low" and station_class == "Healthy":
        return "Consistent (Low risk + healthy observed)"
    return "Inconsistent"