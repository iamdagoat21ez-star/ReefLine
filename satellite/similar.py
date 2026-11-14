"""Prediction layer: which reefs are most likely to see intensifying stress next?

A transparent, rule-based risk score (build document, section 4.6). Each
component is a small function registered in COMPONENTS and weighted in
config.yaml. To add a feature (for example heat stress from DHW), write one
function with @component("name") and add "name: weight" under risk.weights.
"""
import numpy as np
import pandas as pd

COMPONENTS = {}


def component(name):
    def deco(fn):
        COMPONENTS[name] = fn
        return fn
    return deco


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi, dl = p2 - p1, np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


@component("trend")
def trend_component(ctx):
    """Own warming rate relative to the strongest in the dataset (0 to 1)."""
    slope = ctx["df"]["slope_per_year"].clip(lower=0)
    ref = np.percentile(slope[slope > 0], 95) if (slope > 0).any() else 1.0
    return (slope / ref).clip(0, 1)


@component("anomaly")
def anomaly_component(ctx):
    """How far the last year is above normal, in units of 3 standard deviations."""
    d = ctx["df"]
    return (d["recent_anomaly"] / (3 * d["anom_std"])).clip(0, 1)


@component("neighbour")
def neighbour_component(ctx):
    """Closeness to reefs that already show a significant warming trend."""
    d, dist, sigma = ctx["df"], ctx["dist"], ctx["sigma"]
    sig = (d["significant"] & (d["slope_per_year"] > 0)).to_numpy(float)
    w = np.exp(-(dist ** 2) / (2 * sigma ** 2))
    np.fill_diagonal(w, 0.0)
    denom = w.sum(axis=1)
    score = np.divide(w @ sig, denom, out=np.zeros_like(denom), where=denom > 0)
    return pd.Series(score, index=d.index)


def risk_table(trends: pd.DataFrame, reefs: pd.DataFrame, cfg):
    """Merge trend results with reef locations and add risk score and class."""
    rc = cfg["risk"]
    df = trends.merge(reefs, on="site_id").reset_index(drop=True)
    lat, lon = df["lat"].to_numpy(), df["lon"].to_numpy()
    dist = haversine_km(lat[:, None], lon[:, None], lat[None, :], lon[None, :])
    ctx = {"df": df, "dist": dist, "sigma": rc["neighbour_sigma_km"]}

    weights = {k: w for k, w in rc["weights"].items() if k in COMPONENTS}
    total = sum(weights.values())
    for name in weights:
        df[f"c_{name}"] = COMPONENTS[name](ctx)
    df["risk"] = sum(w * df[f"c_{k}"] for k, w in weights.items()) / total

    df["risk_class"] = np.select(
        [df["risk"] >= rc["high"], df["risk"] >= rc["medium"]], ["High", "Medium"], "Low")
    warming_sig = df["significant"] & (df["slope_per_year"] > 0)
    # "Predicted next" = the highest-scoring reefs that are NOT yet significant
    # (a reef already in a significant trend is not a prediction).
    pool = df[~warming_sig & (df["risk"] >= rc["medium"])].nlargest(rc.get("top_next", 3), "risk")
    df["status"] = "Monitor"
    df.loc[warming_sig, "status"] = "Significant warming trend"
    df.loc[pool.index, "status"] = "Predicted next intensification"
    return df.sort_values("risk", ascending=False).reset_index(drop=True)
