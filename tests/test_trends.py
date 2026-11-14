import numpy as np
import pandas as pd
from scipy.stats import kendalltau, theilslopes

from satellite import trends


def make_series(slope_per_year=0.05, n=240, noise=0.3, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2003-01-01", periods=n, freq="MS")
    t = np.arange(n)
    seasonal = 2 * np.sin(2 * np.pi * idx.month / 12)
    return pd.Series(20 + seasonal + slope_per_year / 12 * t + rng.normal(0, noise, n), index=idx)


def test_matches_scipy():
    s = trends.deseasonalize(make_series()).dropna()
    mk = trends.mann_kendall(s.to_numpy())
    tau, p = kendalltau(np.arange(len(s)), s.to_numpy())
    assert abs(mk["tau"] - tau) < 0.02          # scipy uses tau-b; no ties here
    assert (mk["p"] < 0.05) == (p < 0.05)
    slope, _, lo, hi = theilslopes(s.to_numpy(), np.arange(len(s)))
    mine, mlo, mhi = trends.sens_slope(s.to_numpy(), np.arange(len(s)), mk["var_s"])
    assert abs(mine - slope) < 1e-9


def test_recovers_known_slope():
    r = trends.analyze_series(make_series(0.05))
    assert r["ci_low"] < 0.05 < r["ci_high"]
    assert r["p"] < 0.05


def test_no_trend_is_not_significant():
    r = trends.analyze_series(make_series(0.0, seed=3))
    assert r["p"] > 0.05


def test_fdr_monotone():
    p = np.array([0.001, 0.02, 0.04, 0.5])
    adj = trends.benjamini_hochberg(p)
    assert (adj >= p).all() and (adj <= 1).all()
