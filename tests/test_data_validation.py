import pandas as pd
from satellite.validation import validate_registry, validate_series_csv

def test_registry_requires_site_id_schema():
    good = pd.DataFrame({"site_id":["r1"],"name":["Reef"],"lat":[1.0],"lon":[2.0],"region":["Pacific"]})
    assert validate_registry(good) == []
    assert validate_registry(good.drop(columns=["region"]))

def test_series_validation_accepts_monthly_csv(tmp_path):
    path = tmp_path / "sst.csv"
    pd.DataFrame({"date":pd.date_range("2020-01-01", periods=3, freq="MS"), "sst_c":[27,28,27.5]}).to_csv(path,index=False)
    report = validate_series_csv(path, "sst_c", min_months=3)
    assert report["valid"] and report["valid_months"] == 3
