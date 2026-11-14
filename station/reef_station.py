"""Reef station: wait for motion -> take a photo -> score it -> log it.

Runs on the Raspberry Pi or on a laptop in demo mode. It does NOT import
anything from the satellite code, so you can copy just this folder to the Pi.

Laptop demo:   python -m station.reef_station --demo --bleach 0.0
               (press Enter to trigger; try --bleach 0.2, then 0.5)
On the Pi:     python -m station.reef_station --trigger pir --camera picamera
"""
import argparse
import csv
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .sensors import CAMERAS, TRIGGERS, read_temperature
from .vision import bleaching_index, classify

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["event_id", "timestamp_utc", "site_id", "trigger_source", "motion_value", "water_temp_c",
          "image_filename", "image_sha256", "whiteness", "mean_saturation", "bleaching_index",
          "class_label", "notes"]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def log_event(log_dir, row):
    path = log_dir / "events.csv"
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="keyboard trigger + fake camera (laptop)")
    ap.add_argument("--trigger", default="keyboard", choices=TRIGGERS)
    ap.add_argument("--camera", default="fake", choices=CAMERAS)
    ap.add_argument("--site", help="reef_id of the deployment site (default: config.yaml)")
    ap.add_argument("--bleach", type=float, default=0.0, help="demo camera only: share of white patches 0-1")
    ap.add_argument("--reset-baseline", action="store_true", help="treat the next photo as the new healthy baseline")
    ap.add_argument("--max-events", type=int, default=0, help="stop after N events (0 = run forever)")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(ROOT / "config.yaml"))["station"]
    site = args.site or cfg["site_id"]
    log_dir = ROOT / cfg["log_dir"]
    (log_dir / "images").mkdir(parents=True, exist_ok=True)
    demo = args.demo or args.camera == "fake"

    trigger = TRIGGERS["keyboard" if args.demo else args.trigger]()
    camera = CAMERAS["fake" if args.demo else args.camera]()
    print(f"Reef station for {site} ({'DEMO MODE' if demo else 'live'}). Waiting for motion...")

    # The first photo at a site is saved as the "healthy" colour baseline (used for the paling score).
    base_file = log_dir / f"baseline_{site}.json"
    baseline_sat = None
    if base_file.exists() and not args.reset_baseline:
        baseline_sat = json.loads(base_file.read_text())["mean_saturation"]
    count = 0
    while True:
        source, motion = trigger.wait()
        ts = datetime.now(timezone.utc)
        eid = uuid.uuid4().hex[:8]
        img_path = log_dir / "images" / f"{site}_{ts:%Y%m%dT%H%M%S}_{eid}.jpg"
        camera.capture(img_path, bleach=args.bleach)

        scores = bleaching_index(img_path, baseline_sat)
        if baseline_sat is None:
            baseline_sat = scores["mean_saturation"]
            base_file.write_text(json.dumps({"mean_saturation": baseline_sat, "image": img_path.name}))
        label = classify(scores["bleaching_index"], cfg["paling_threshold"], cfg["bleached_threshold"])

        log_event(log_dir, {
            "event_id": eid, "timestamp_utc": ts.isoformat(), "site_id": site,
            "trigger_source": source, "motion_value": motion, "water_temp_c": read_temperature() or "",
            "image_filename": img_path.name, "image_sha256": sha256(img_path),
            "whiteness": round(scores["whiteness"], 4), "mean_saturation": round(scores["mean_saturation"], 2),
            "bleaching_index": round(scores["bleaching_index"], 4), "class_label": label,
            "notes": "DEMO MODE" if demo else "",
        })
        print(f"[{ts:%H:%M:%S}] {source}  BI={scores['bleaching_index']:.3f}  {label}  {img_path.name}")

        count += 1
        if args.max_events and count >= args.max_events:
            break


if __name__ == "__main__":
    main()
