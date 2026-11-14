import numpy as np

from satellite.compare import concordance
from station.vision import bleaching_index, classify


def test_white_is_bleached_colour_is_healthy():
    white = np.full((100, 100, 3), 240, dtype=np.uint8)
    coral = np.zeros((100, 100, 3), dtype=np.uint8)
    coral[..., 0], coral[..., 1], coral[..., 2] = 215, 95, 120
    assert classify(bleaching_index(white)["bleaching_index"]) == "Bleached"
    assert classify(bleaching_index(coral)["bleaching_index"]) == "Healthy"


def test_concordance_rules():
    assert concordance("High", "Bleached") == "Consistent"
    assert concordance("Low", "Healthy") == "Consistent"
    assert concordance("High", "Healthy") == "Not consistent"
    assert concordance("Medium", "Paling") == "Partially consistent"
