# Reefline

Reefline combines a satellite-derived reef trend application with a future Raspberry Pi reef station. The current laptop application runs on per-site CSV time series; the Pi implementation is preserved but hardware integration is intentionally deferred.

## Quick start

Activate the existing environment and run from this repository root:

```powershell
conda activate reefline
python scripts/make_demo_data.py
pytest -q
streamlit run app.py
```

**Important:** `make_demo_data.py` overwrites `data/reefs.csv` and all demo SST/chlorophyll CSVs with synthetic data. Do not run it after adding real observations unless you intend to regenerate the demo dataset. The included CSVs are synthetic demonstration data, not NASA observations.

## Repository structure

```text
reefline/
├── app.py                     # Streamlit application
├── config.yaml                # Analysis, variables, risk and station settings
├── environment.yml            # Conda environment specification
├── requirements.txt            # Pip dependency list
├── sites.csv                  # Actual Pi deployments; header-only until deployed
├── data/
│   ├── reefs.csv              # Candidate reef registry
│   ├── raw/                   # Original NASA downloads (git-ignored)
│   ├── cache/                 # Processed arrays/caches (git-ignored)
│   ├── reef_mask/             # Reef polygon/mask assets
│   ├── sst/                   # Per-site monthly SST CSVs
│   ├── chlorophyll/           # Per-site monthly chlorophyll CSVs
│   └── optional/swot/         # Optional sea-surface-height context
├── satellite/                 # Ingestion, preprocessing, statistics and ranking
├── station/                   # Existing Pi code preserved; hardware work deferred
├── scripts/                   # Demo-data generation
├── tools/                     # Offline bundle and comparison utilities
├── outputs/                   # Generated reports and logs
└── tests/                     # Unit tests
```

## Data contracts

| File | Required columns / format |
|---|---|
| `data/reefs.csv` | `site_id,name,lat,lon,region`; optional `data_source` provenance column |
| `sites.csv` | `site_id,lat,lon,risk` for actual deployed stations; empty until a station is deployed |
| `data/sst/<site_id>.csv` | `date,sst_c` (monthly mean, degrees C) |
| `data/chlorophyll/<site_id>.csv` | `date,chl_mg_m3` (monthly mean, mg/m³) |
| `outputs/logs/events.csv` | Existing station event schema, including `site_id` |

`site_id` is the shared identifier between the reef registry, time-series filenames and station events. `data_source=synthetic_demo` explicitly labels generated data. Keep that provenance field when adding real data (for example `NASA MODIS` or `NASA MUR`).

## Satellite data workflow

1. Identify the NASA product and collection appropriate to the variable, spatial resolution and period.
2. Authenticate with NASA Earthdata using `earthaccess.login(persist=True)`.
3. Search/download selected granules with `satellite/ingest.py`; raw files belong in `data/raw/`.
4. Perform product-specific quality filtering and spatial extraction around each reef. This extraction is not guessed by the generic scaffold and still needs to be implemented for the chosen products.
5. Aggregate valid observations to monthly site means and write the CSV contract above. `satellite/preprocess.py` provides the monthly aggregation helper.
6. Run `satellite/validation.py` before analysis.
7. Run the app and inspect the Mann–Kendall / Sen's slope results.

The current app's trend method is plain Mann–Kendall with FDR correction and seasonal-cycle removal. It does not yet implement autocorrelation-corrected or seasonal Mann–Kendall. Treat significance results as exploratory until those methods and product-specific QA are added.

## DHW scientific note

Degree Heating Weeks requires weekly SST observations and a documented local Maximum Monthly Mean (MMM) climatology. Reefline's core SST CSVs are monthly; therefore `satellite/dhw.py` explicitly rejects monthly-spaced inputs. Do not infer DHW from the monthly trend series.

## Raspberry Pi scope

`station/reef_station.py`, `station/sensors.py` and `station/vision.py` are preserved from the supplied scaffold. Do not modify them during the current satellite/data foundation phase. See `station/HARDWARE_TODO.md` for future DS18B20, MPU6050 and camera work. The current camera path includes demo behavior and the bleaching score is a basic heuristic, not a validated field classifier.

## Commands

```powershell
# Tests
pytest -q

# Streamlit app
streamlit run app.py

# Raspberry Pi station laptop demo (does not require hardware)
python -m station.reef_station --demo --bleach 0.0

# Print satellite risk table and station event count
python -m tools.compare

# Bundle the reef registry and per-site CSVs for offline use
python -m tools.bundle
```

## Git safety

Never commit credentials, `.netrc`, `.env`, private SSH keys, raw NASA downloads, caches, generated station logs or generated reports. Commit only small, documented data files that the team is allowed to redistribute.
