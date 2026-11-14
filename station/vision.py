"""Bleaching score from a photo (build document, section 5.5).

Pure numpy + Pillow, so it runs on a Raspberry Pi with no extra installs.
Add OpenCV later if you want fancier checks (masks, white balance, etc.).
"""
import numpy as np
from PIL import Image


def _saturation_value(rgb):
    """rgb: HxWx3 uint8. Returns saturation and value arrays on a 0-255 scale."""
    a = rgb.astype(float)
    mx, mn = a.max(axis=2), a.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1) * 255, 0)
    return sat, mx


def bleaching_index(image, baseline_sat=None, roi=0.6):
    """image: path or HxWx3 uint8 array. Looks at the central `roi` fraction.

    whiteness W = share of pixels that are pale and bright
    paling    P = drop in mean saturation versus a baseline photo (optional)
    BI = 0.7*W + 0.3*P      (0 = healthy colour, 1 = fully white)
    """
    rgb = np.asarray(Image.open(image).convert("RGB")) if not isinstance(image, np.ndarray) else image
    h, w = rgb.shape[:2]
    dh, dw = int(h * (1 - roi) / 2), int(w * (1 - roi) / 2)
    rgb = rgb[dh:h - dh, dw:w - dw]
    sat, val = _saturation_value(rgb)
    whiteness = float(((sat < 40) & (val > 180)).mean())
    mean_sat = float(sat.mean())
    paling = max(0.0, (baseline_sat - mean_sat) / baseline_sat) if baseline_sat else 0.0
    bi = 0.7 * whiteness + 0.3 * paling
    return {"whiteness": whiteness, "mean_saturation": mean_sat, "bleaching_index": float(bi)}


def classify(bi, paling_threshold=0.15, bleached_threshold=0.35):
    if bi >= bleached_threshold:
        return "Bleached"
    if bi >= paling_threshold:
        return "Paling"
    return "Healthy"
