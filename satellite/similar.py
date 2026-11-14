"""Pick the three non-significant reefs most like a worsening reference reef.

Score = 0.60 * slope difference + 0.40 * distance.
Slope difference is the absolute gap in Sen's slope, scaled by the largest gap
in the candidate pool. Distance uses kilometers relative to a 100 km preference:
0 at the same point, 0.5 at 100 km, and closer to 1 as range grows. Lower score
is more similar. Reefs farther than 100 km stay eligible, because this catalog
has no pair inside that range.
"""
import numpy as np
import pandas as pd

from satellite.trends import ALPHA, analyze_all, load_reefs

SLOPE_WEIGHT = 0.60
DISTANCE_WEIGHT = 0.40
PREFERRED_DISTANCE_KM = 100.0
_CANDIDATE_COLUMNS = [
    "site_id",
    "name",
    "lat",
    "lon",
    "region",
    "direction",
    "p_value",
    "slope_per_year",
    "significant",
    "slope_diff",
    "distance_km",
    "score",
]


def rank_candidates(site_id: str, variable: str, alpha: float = ALPHA, trends: pd.DataFrame | None = None) -> pd.DataFrame:
    """Rank every non-significant reef against a worsening reference. Lowest score is closest."""
    if trends is None:
        trends = analyze_all(variable, alpha=alpha)
    table = trends if "lat" in trends.columns else trends.merge(load_reefs(), on="site_id", how="left")
    reference = table.loc[table["site_id"] == site_id]
    if reference.empty:
        raise ValueError(f"Unknown site_id {site_id!r}")
    reference = reference.iloc[0]
    if not bool(reference["worsening"]):
        raise ValueError(
            f"{site_id} has no significant worsening {variable} trend "
            f"(direction={reference['direction']}, p={reference['p_value']:.3g})"
        )

    candidates = table.loc[~table["significant"] & (table["site_id"] != site_id)].copy()
    if candidates.empty:
        return candidates.reindex(columns=_CANDIDATE_COLUMNS)
    candidates["slope_diff"] = (candidates["slope_per_year"] - reference["slope_per_year"]).abs()
    candidates["distance_km"] = _distance_km(
        reference["lat"], reference["lon"], candidates["lat"].to_numpy(), candidates["lon"].to_numpy()
    )
    candidates["score"] = _score(candidates["slope_diff"], candidates["distance_km"])
    return candidates.sort_values(
        ["score", "distance_km", "site_id"], ascending=True
    )[_CANDIDATE_COLUMNS].reset_index(drop=True)


def find_similar(site_id: str, variable: str, alpha: float = ALPHA, trends: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return exactly 3 non-significant reefs closest to a worsening reference site."""
    ranked = rank_candidates(site_id, variable, alpha=alpha, trends=trends)
    if len(ranked) < 3:
        raise ValueError(
            f"Need 3 non-significant {variable} reefs, found {len(ranked)}"
        )
    return ranked.head(3).reset_index(drop=True)


def _score(slope_diff: pd.Series, distance_km: pd.Series) -> pd.Series:
    slope_span = float(slope_diff.max())
    slope_term = slope_diff / slope_span if slope_span > 0 else slope_diff * 0.0
    distance_term = distance_km / (distance_km + PREFERRED_DISTANCE_KM)
    return SLOPE_WEIGHT * slope_term + DISTANCE_WEIGHT * distance_term


def _distance_km(lat1, lon1, lat2, lon2) -> np.ndarray:
    radius = 6371.0
    phi1 = np.radians(float(lat1))
    phi2 = np.radians(np.asarray(lat2, dtype=float))
    dphi = phi2 - phi1
    dlambda = np.radians(np.asarray(lon2, dtype=float) - float(lon1))
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return 2 * radius * np.arcsin(np.sqrt(a))
