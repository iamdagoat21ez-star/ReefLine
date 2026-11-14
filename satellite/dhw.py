"""Weekly Degree Heating Weeks (DHW) calculation.

DHW is not calculated from Reefline's monthly SST trend CSVs. This helper
requires a weekly SST series and a documented local MMM climatology value.
"""
from __future__ import annotations
import pandas as pd

def calculate_dhw(weekly_sst: pd.Series, mmm_c: float, threshold_c: float = 1.0, window_weeks: int = 12) -> pd.Series:
    """Return rolling DHW in degree-C-weeks from weekly SST observations.

    Each weekly HotSpot is max(SST - MMM - threshold, 0) + threshold only
    when SST is at least threshold above MMM; equivalently max(SST-MMM, 0)
    contributes only for weeks meeting the threshold. Inputs must be weekly.
    """
    if not isinstance(weekly_sst.index, pd.DatetimeIndex):
        raise TypeError("weekly_sst must have a DatetimeIndex")
    s = pd.to_numeric(weekly_sst, errors="coerce").dropna().sort_index()
    if len(s) < 1:
        return pd.Series(dtype=float, name="dhw_c_weeks")
    gaps = s.index.to_series().diff().dropna().dt.days
    if not gaps.empty and not gaps.between(5, 9).all():
        raise ValueError("DHW requires weekly observations (approximately 7-day spacing), not monthly data")
    hotspot = (s - float(mmm_c)).where((s - float(mmm_c)) >= float(threshold_c), 0.0)
    return hotspot.rolling(window=window_weeks, min_periods=window_weeks).sum().rename("dhw_c_weeks")
