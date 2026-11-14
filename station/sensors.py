"""Hardware (and stand-ins for it).

Every device is a small class with one method. The same station code runs with
real sensors on the Pi or with keyboard/fake-camera stand-ins on a laptop.
To add a sensor: write a class here and add it to TRIGGERS, CAMERAS or read_temperature().
"""
import time
from pathlib import Path

import numpy as np
from PIL import Image


# ---------------- triggers: wait() returns (source, motion_value) ----------------
class KeyboardTrigger:
    """Laptop demo: press Enter to simulate motion."""
    def wait(self):
        input("Press Enter to simulate motion (Ctrl+C to quit)... ")
        return "manual", 1.0


class PIRTrigger:
    """HC-SR501 on GPIO17 (physical pin 11). Needs gpiozero (preinstalled on Pi OS)."""
    def __init__(self, pin=17):
        from gpiozero import MotionSensor
        self.pir = MotionSensor(pin)

    def wait(self):
        self.pir.wait_for_motion()
        self.pir.wait_for_no_motion()
        return "pir", 1.0

# Idea for later: MPUTrigger (vibration) using smbus2, returning ("vibration", g_value).


# ---------------- cameras: capture(path, bleach) saves a JPEG ----------------
class PiCamera:
    """Camera Module 3 via picamera2."""
    def __init__(self):
        from picamera2 import Picamera2
        self.cam = Picamera2()
        self.cam.configure(self.cam.create_still_configuration())
        self.cam.start()
        time.sleep(1.5)  # let exposure settle

    def capture(self, path, bleach=0.0):
        self.cam.capture_file(str(path))


class FakeCamera:
    """DEMO MODE: draws a coral-coloured scene with `bleach` share of white patches.
    Lets you demo healthy -> paling -> bleached without a real reef."""
    def capture(self, path, bleach=0.0):
        rng = np.random.default_rng()
        h, w = 360, 480
        img = np.zeros((h, w, 3), dtype=float)
        img[..., 0] = 215 + rng.normal(0, 12, (h, w))   # reddish-orange coral
        img[..., 1] = 95 + rng.normal(0, 12, (h, w))
        img[..., 2] = 120 + rng.normal(0, 12, (h, w))
        patches = rng.random((h // 12, w // 12)) < bleach
        mask = np.kron(patches, np.ones((12, 12), dtype=bool))
        img[mask] = [238, 236, 232]
        Image.fromarray(np.clip(img, 0, 255).astype("uint8")).save(path, quality=90)


TRIGGERS = {"keyboard": KeyboardTrigger, "pir": PIRTrigger}
CAMERAS = {"fake": FakeCamera, "picamera": PiCamera}


def read_temperature():
    """DS18B20 water temperature in deg C, or None. Replace with w1thermsensor later."""
    return None
