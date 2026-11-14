import pandas as pd
import pytest
from satellite.preprocess import monthly_mean
from satellite.dhw import calculate_dhw

def test_monthly_mean_aggregates_daily_values():
    frame = pd.DataFrame({"when":["2024-01-01","2024-01-15","2024-02-01"],"sst":[26,28,27]})
    out = monthly_mean(frame,"when","sst")
    assert len(out) == 2
    assert out.loc[0,"sst"] == 27

def test_dhw_rejects_monthly_spacing():
    s = pd.Series([28.0,28.0], index=pd.to_datetime(["2024-01-01","2024-02-01"]))
    with pytest.raises(ValueError):
        calculate_dhw(s, 27.0)
