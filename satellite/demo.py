"""Demo environmental records on fictional and documented reef locations.

NOAA reef-region marker coordinates retain their geography attribution.
All added environmental series are synthetic and never overwrite NASA records.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

REGIONS = [
    ("gbr", "Great Barrier Reef · Northern Sector", -16.8, 147.4, ["reef_005", "reef_006", "reef_007"]),
    ("triangle", "Coral Triangle · Indonesia", -3.3, 121.5, []),
    ("florida", "Florida Keys & Caribbean", 23.0, -82.7, ["reef_001", "reef_002", "reef_003", "reef_004"]),
    ("africa", "East African Coastal Reef", -7.3, 40.3, []),
    ("maldives", "Maldives · Atoll Gardens", 3.9, 72.8, ["reef_010"]),
    ("redsea", "Red Sea · Northern Reefs", 27.3, 34.8, ["reef_009"]),
    ("philippines", "Philippines · Sulu Sea", 8.9, 119.9, ["reef_011"]),
    ("polynesia", "French Polynesia · Lagoon Belt", -17.5, -149.85, ["reef_012"]),
    ("ningaloo", "Western Australia · Ningaloo", -22.7, 113.7, ["reef_008"]),
    ("fiji", "Fiji · Island Arc", -17.4, 179.0, []),
    ("palau", "Palau · Western Lagoons", 7.3, 134.4, []),
    ("samoa", "Samoa · Blue Coast", -13.8, -172.0, []),
    ("tonga", "Tonga · Southern Islands", -21.1, -175.2, []),
    ("vanuatu", "Vanuatu · Coral Passage", -16.4, 167.7, []),
    ("newcaledonia", "New Caledonia · Barrier Lagoons", -22.1, 166.2, []),
    ("solomons", "Solomon Islands · Reef Chain", -8.5, 159.8, []),
    ("papua", "Papua New Guinea · Island Shelf", -5.3, 151.0, []),
    ("micronesia", "Micronesia · Oceanic Atolls", 7.4, 151.8, []),
    ("marshall", "Marshall Islands · Outer Atolls", 7.1, 171.2, []),
    ("hawaii", "Hawaiʻi · Pacific Reef Belt", 20.7, -156.4, []),
    ("cook", "Cook Islands · Lagoon Arc", -21.2, -159.8, []),
    ("seychelles", "Seychelles · Inner Islands", -4.6, 55.5, []),
    ("mauritius", "Mauritius · Coral Coast", -20.2, 57.5, []),
    ("madagascar", "Madagascar · Western Shelf", -18.8, 43.8, []),
    ("mozambique", "Mozambique · Northern Coast", -12.4, 40.6, []),
    ("oman", "Oman · Arabian Sea", 20.5, 58.8, []),
    ("andaman", "Andaman Islands · Eastern Bay", 11.7, 92.7, []),
    ("srilanka", "Sri Lanka · Southern Shelf", 6.0, 80.3, []),
    ("bahamas", "Bahamas · Northern Banks", 24.5, -76.0, []),
    ("cayman", "Cayman Islands · Western Caribbean", 19.3, -81.2, []),
    ("roatan", "Honduras · Bay Islands", 16.3, -86.5, []),
    ("bonaire", "Bonaire · Southern Caribbean", 12.2, -68.3, []),
    ("bermuda", "Bermuda · Atlantic Reef Ring", 32.3, -64.7, []),
    ("brazil", "Brazil · Tropical Shelf", -17.8, -38.7, []),
    ("mexico", "Mexico · Caribbean Coast", 20.4, -87.0, []),
    ("panama", "Panama · Island Channels", 9.4, -78.5, []),
]
NAMES = [
    "Dawn Garden", "Rosewater Shelf", "Pearl Channel", "Moonlit Lagoon",
    "Sunrise Terrace", "Coral Haven", "Opal Passage", "Starlight Bank",
]


def demo_catalog():
    """Return fictional fixtures plus documented NOAA geography with demo series."""
    regions, stations = {}, []
    dates = pd.date_range("2016-01-01", "2025-12-01", freq="MS")
    t = np.arange(len(dates), dtype=float)
    for region_index, (key, title, lat, lon, measured) in enumerate(REGIONS):
        region_ids = list(measured)
        for index, name in enumerate(NAMES):
            site_id = f"demo_{key}_{index + 1:02d}"
            rng = np.random.default_rng(8100 + region_index * 100 + index)
            measurements = {}
            for variable in ("sst", "chlorophyll"):
                scale = 1.0 if variable == "sst" else 0.035
                # Every fourth station has a strong trend. Others vary without a trend.
                slope = (0.018 if index % 4 == 0 else 0.0001) * scale
                season = (1.0 if variable == "sst" else .05) * np.sin(2 * np.pi * t / 12)
                noise = rng.normal(0, .30 if variable == "sst" else .025, len(t))
                level = 27.4 + region_index % 4 * .3 if variable == "sst" else .30 + region_index % 5 * .04
                values = level + season + slope * t + noise
                measurements[variable] = pd.Series(values, index=dates)
            stations.append({
                "site_id": site_id, "name": f"{title.split(' · ')[0]} · {name}",
                "lat": round(lat + rng.uniform(-.8, .8), 4),
                "lon": round(((lon + rng.uniform(-.9, .9) + 180) % 360) - 180, 4),
                "region": title, "is_demo": True,
                "data_source": "Synthetic demo fixture · no connected satellite or field station",
                "series": measurements,
            })
            region_ids.append(site_id)
        regions[key] = {
            "short": title, "center": [lat, lon], "zoom": 7 if key != "gbr" else 5,
            "sites": region_ids, "base": 38 + region_index % 5,
            "factor": round(.9 + region_index % 7 * .025, 3),
        }
    coastal_catalog = json.loads((Path(__file__).resolve().parents[1] / "data/reef_coasts.json").read_text())
    coast_ids = []
    for index, location in enumerate(coastal_catalog["locations"]):
        site_id = f"demo_coast_{index + 1:03d}"
        rng = np.random.default_rng(42000 + index)
        series = {}
        for variable in ("sst", "chlorophyll"):
            scale = 1.0 if variable == "sst" else .035
            slope = (.018 if index % 4 == 0 else .0001) * scale
            seasonal = (1.0 if variable == "sst" else .05) * np.sin(2 * np.pi * t / 12)
            noise = rng.normal(0, .30 if variable == "sst" else .025, len(t))
            series[variable] = pd.Series((27.8 if variable == "sst" else .38) + seasonal + slope * t + noise, index=dates)
        stations.append(dict(
            location, site_id=site_id, region="Known reef coasts · NOAA worldwide",
            is_demo=True, geography_source=coastal_catalog["source"],
            geography_source_url=coastal_catalog["source_url"],
            data_source="Synthetic demo environmental series · NOAA marker geography",
            series=series,
        ))
        coast_ids.append(site_id)
    regions["coasts"] = dict(
        short="Known reef coasts · NOAA worldwide", center=[8, 0], zoom=1,
        sites=coast_ids, base=38, factor=1,
    )
    regions["gbr"].update(base=38, factor=1, zoom=5)
    regions["florida"]["zoom"] = 5
    all_ids = list(dict.fromkeys(site for region in regions.values() for site in region["sites"]))
    regions = {"world": dict(short="Worldwide reef explorer", center=[8, 0], zoom=1,
                              sites=all_ids, base=38, factor=1), **regions}
    return regions, stations
