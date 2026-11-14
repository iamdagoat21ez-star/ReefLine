# Raspberry Pi hardware work — intentionally deferred

The current station implementation is preserved unchanged in this scaffold.
Do not modify `reef_station.py`, `sensors.py`, or `vision.py` during the
satellite/data-foundation phase.

Future hardware tasks (not implemented yet):
- Replace placeholder DS18B20 temperature read with verified sensor acquisition.
- Implement MPU6050 vibration monitoring if required by the final build.
- Validate camera capture and calibration on the selected Raspberry Pi model.
- Replace the demo color heuristic with a calibrated and validated coral-image method.
- Test offline buffering, timestamping, and safe synchronization to the laptop.
