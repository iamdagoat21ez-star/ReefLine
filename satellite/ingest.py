"""NASA ingest adapter scaffolding. Product-specific spatial extraction is explicit.

This module deliberately does not guess NASA collection IDs or silently download
large datasets. First identify the product, temporal resolution, units and QA
flags; then use earthaccess to discover/download granules and preprocess them.
"""
from __future__ import annotations
from pathlib import Path

def search_nasa_granules(short_name: str, temporal: str | None = None, count: int = 10):
    """Search Earthdata granules for a confirmed NASA short name.

    Requires earthaccess and an authenticated Earthdata account. This returns
    search results only; it does not download or process them.
    """
    try:
        import earthaccess
    except ImportError as exc:
        raise RuntimeError("Install earthaccess in the reefline environment first") from exc
    earthaccess.login(persist=True)
    kwargs = {"short_name": short_name, "count": count}
    if temporal:
        kwargs["temporal"] = temporal
    return earthaccess.search_data(**kwargs)

def download_granules(granules, output_dir="data/raw"):
    """Download explicitly selected granules into the ignored raw-data folder."""
    try:
        import earthaccess
    except ImportError as exc:
        raise RuntimeError("Install earthaccess in the reefline environment first") from exc
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    return earthaccess.download(granules, local_path=str(out))
