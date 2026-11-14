"""Trend statistics: Mann-Kendall test and Sen's slope (with confidence interval).

Math follows the Reefline build document, section 4.4.
Input is a monthly series; the seasonal cycle is removed first (anomalies).
"""
import numpy as np
import pandas as pd
from scipy.stats import norm


def deseasonalize(s: pd.Series) -> pd.Series:
    """Subtract the mean of each calendar month (monthly climatology)."""
    return s - s.groupby(s.index.month).transform("mean")


def mann_kendall(x):
    """Returns S, Var(S), Z, two-sided p, Kendall tau. Tie-corrected."""
    x = np.asarray(x, float)
    n = len(x)
    i, j = np.triu_indices(n, 1)
    s = float(np.sign(x[j] - x[i]).sum())
    _, counts = np.unique(x, return_counts=True)
    c = counts[counts > 1]
    ties = float((c * (c - 1) * (2 * c + 5)).sum())
    var_s = (n * (n - 1) * (2 * n + 5) - ties) / 18.0
    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0
    p = 2 * (1 - norm.cdf(abs(z)))
    tau = s / (n * (n - 1) / 2)
    return {"S": s, "var_s": var_s, "z": float(z), "p": float(p), "tau": float(tau)}


def sens_slope(x, t, var_s, alpha=0.05):
    """Median of all pairwise slopes, plus a (1-alpha) confidence interval.
    t is the time axis (months), so the slope is per month."""
    x, t = np.asarray(x, float), np.asarray(t, float)
    i, j = np.triu_indices(len(x), 1)
    q = np.sort((x[j] - x[i]) / (t[j] - t[i]))
    big_n = len(q)
    c = norm.ppf(1 - alpha / 2) * np.sqrt(var_s)
    m1, m2 = (big_n - c) / 2, (big_n + c) / 2
    pos = np.arange(big_n)
    lo = np.interp(np.clip(m1 - 1, 0, big_n - 1), pos, q)
    hi = np.interp(np.clip(m2, 0, big_n - 1), pos, q)
    return float(np.median(q)), float(lo), float(hi)


def analyze_series(s: pd.Series, alpha=0.05, min_months=60, recent_months=12):
    """Full analysis of one monthly series. Returns a dict, or None if too short."""
    anom = deseasonalize(s).dropna()
    if len(anom) < min_months:
        return None
    t = ((anom.index.year - anom.index[0].year) * 12 + (anom.index.month - anom.index[0].month)).to_numpy()
    mk = mann_kendall(anom.to_numpy())
    slope, lo, hi = sens_slope(anom.to_numpy(), t, mk["var_s"], alpha)
    return {
        "n": len(anom),
        "tau": mk["tau"], "z": mk["z"], "p": mk["p"],
        "slope_per_year": slope * 12, "ci_low": lo * 12, "ci_high": hi * 12,
        "recent_anomaly": float(anom.iloc[-recent_months:].mean()),
        "anom_std": float(anom.std()),
    }


def benjamini_hochberg(p):
    """FDR-adjusted p-values (same order as input)."""
    p = np.asarray(p, float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / (np.arange(n) + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(adj, 0, 1)
    return out


def analyze_variable(site_ids, load_fn, cfg):
    """Run analyze_series for every site. load_fn(site_id) -> monthly Series.
    Returns a DataFrame with one row per reef."""
    a = cfg["analysis"]
    rows = []
    for sid in site_ids:
        s = load_fn(sid)
        if s is None:
            continue
        r = analyze_series(s, a["alpha"], a["min_months"], a["recent_months"])
        if r:
            rows.append({"site_id": sid, **r})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["p_adj"] = benjamini_hochberg(df["p"]) if a.get("use_fdr", True) else df["p"]
    df["significant"] = df["p_adj"] < a["alpha"]
    df["direction"] = np.where(df["slope_per_year"] > 0, "increasing", "decreasing")
    return df
