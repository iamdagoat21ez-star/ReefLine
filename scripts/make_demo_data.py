"""Generate SYNTHETIC demo data so the whole project runs before real NASA data
is downloaded. Everything this writes is fake and labelled data_source=synthetic_demo.

Replace it later with real data in the same CSV format (see README):
  data/reefs.csv, data/sst/<site_id>.csv (date, sst_c),
  data/chlorophyll/<site_id>.csv (date, chl_mg_m3)

Run from the repo root:  python scripts/make_demo_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
import os
rng = np.random.default_rng(int(os.environ.get("SEED", 10)))

# reef_id, name, lat, lon, warming trend (deg C/yr), mean SST, seasonal amplitude, recent heat (deg C)
REEFS = [
    ("reef_001", "Carysfort Reef, FL", 25.22, -80.21, 0.060, 27.0, 2.8, 0.0),
    ("reef_002", "Looe Key, FL", 24.55, -81.40, 0.050, 27.4, 2.6, 0.0),
    ("reef_003", "Dry Tortugas, FL", 24.63, -82.87, 0.000, 27.2, 2.7, 1.4),   # next-risk candidate
    ("reef_004", "Belize Barrier Reef", 17.30, -87.80, 0.045, 28.2, 1.8, 0.0),
    ("reef_005", "Lizard Island, GBR", -14.67, 145.45, 0.055, 27.0, 1.9, 0.0),
    ("reef_006", "Osprey Reef, Coral Sea", -13.90, 146.55, 0.000, 27.3, 1.7, 1.4),  # next-risk candidate
    ("reef_007", "Heron Island, GBR", -23.44, 151.91, 0.002, 25.2, 2.4, 0.0),
    ("reef_008", "Ningaloo Reef, AU", -22.70, 113.70, 0.000, 25.0, 2.5, 0.0),
    ("reef_009", "Eilat, Red Sea", 29.50, 34.90, 0.002, 24.8, 3.0, 0.0),
    ("reef_010", "Ari Atoll, Maldives", 3.90, 72.80, 0.050, 29.0, 1.1, 0.0),
    ("reef_011", "Tubbataha, Philippines", 8.90, 119.90, 0.003, 28.6, 1.2, 0.0),
    ("reef_012", "Moorea, Fr. Polynesia", -17.50, -149.85, -0.002, 27.6, 1.5, 0.0),
]

dates = pd.date_range("2003-01-01", "2025-12-01", freq="MS")
t = np.arange(len(dates))


def ar1(n, phi=0.6, sigma=0.6):
    e = rng.normal(0, sigma, n)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


(ROOT / "data/sst").mkdir(parents=True, exist_ok=True)
(ROOT / "data/chlorophyll").mkdir(parents=True, exist_ok=True)

rows = []
for rid, name, lat, lon, slope, base, amp, heat in REEFS:
    season = amp / 2 * np.sin(2 * np.pi * (dates.month - 3) / 12 * (1 if lat >= 0 else -1))
    sst = np.asarray(base + season + slope / 12 * t + ar1(len(t)), dtype=float)
    sst[-12:] += heat   # recent marine heatwave at some reefs
    chl = np.exp(np.asarray(np.log(0.25) + 0.15 * np.cos(2 * np.pi * dates.month / 12)
                 + (slope * 1.5) / 12 * t / 10 + ar1(len(t), 0.4, 0.2), dtype=float))
    pd.DataFrame({"date": dates, "sst_c": sst.round(3)}).to_csv(ROOT / f"data/sst/{rid}.csv", index=False)
    pd.DataFrame({"date": dates, "chl_mg_m3": chl.round(4)}).to_csv(ROOT / f"data/chlorophyll/{rid}.csv", index=False)
    region = "Florida Keys, USA" if rid in {"reef_001", "reef_002", "reef_003"} else "Global reef region"
    rows.append({"site_id": rid, "name": name, "lat": lat, "lon": lon, "region": region, "data_source": "synthetic_demo"})

pd.DataFrame(rows).to_csv(ROOT / "data/reefs.csv", index=False)
print(f"Wrote {len(REEFS)} synthetic demo reefs. This is FAKE data for development.")
