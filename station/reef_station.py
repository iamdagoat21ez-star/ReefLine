"""Motion-triggered photos and event logs for a reef deployment.

Table-top demo (wave in front of a USB/laptop webcam)::
    python station/reef_station.py --demo --site reef_004 --max-events 3

Raspberry Pi camera::
    python station/reef_station.py --camera picamera --site reef_004

Hardware-free test (save one plain image and log one event, then exit)::
    python station/reef_station.py --fake-image --site reef_004

Webcams require opencv-python; Pi cameras require the system picamera2 package.
Images are real camera frames unless --fake-image is used (motion_value=0.0).
Events go to station/logs/events.csv by default;
image_filename is relative to that directory. Satellite data source: NASA Giovanni.
"""

import argparse
import csv
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

FIELDS = ["timestamp", "site_id", "motion_value", "image_filename"]
DEFAULT_LOG_DIR = Path(__file__).resolve().parent / "logs"


class Camera:
    """Provide RGB frames from either a webcam or a Raspberry Pi camera."""

    def __init__(self, kind, index=0):
        self.kind = kind
        if kind == "picamera":
            from picamera2 import Picamera2

            self.device = Picamera2()
            try:
                self.device.configure(self.device.create_video_configuration(
                    main={"size": (640, 480), "format": "RGB888"}
                ))
                self.device.start()
                time.sleep(2)
            except Exception:
                self.device.close()
                raise
        else:
            import cv2

            self.cv2 = cv2
            self.device = cv2.VideoCapture(index)
            if not self.device.isOpened():
                self.device.release()
                raise RuntimeError(f"Cannot open webcam {index}")

    def read(self):
        if self.kind == "picamera":
            # Picamera2 RGB888 arrays use BGR channel order, like OpenCV.
            return self.device.capture_array()[:, :, ::-1].copy()
        ok, frame = self.device.read()
        if not ok:
            raise RuntimeError("Camera did not return a frame")
        return self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)

    def close(self):
        if self.kind == "picamera":
            try:
                self.device.stop()
            finally:
                self.device.close()
        else:
            self.device.release()


def motion_frame(frame):
    """Reduce noise and work by comparing small grayscale frames."""
    return np.asarray(Image.fromarray(frame).convert("L").resize((160, 120)),
                      dtype=np.float32)


def motion_value(previous, current, pixel_threshold=25):
    """Fraction of pixels whose brightness changed (0 to 1)."""
    return float(np.mean(np.abs(current - previous) >= pixel_threshold))


def log_event(log_dir, row):
    """Append one event without silently mixing incompatible CSV schemas."""
    path = Path(log_dir) / "events.csv"
    with path.open("a+", newline="", encoding="utf-8") as handle:
        handle.seek(0)
        header = next(csv.reader(handle), None)
        if header is not None and header != FIELDS:
            raise ValueError(f"{path} has an incompatible header; use a new --log-dir")
        handle.seek(0, 2)
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if header is None:
            writer.writeheader()
        writer.writerow(row)


def record_event(log_dir, site_id, frame, motion):
    log_dir = Path(log_dir)
    images = log_dir / "images"
    images.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    filename = f"{timestamp:%Y%m%dT%H%M%S_%fZ}_{uuid.uuid4().hex[:8]}.jpg"
    image_path = images / filename
    Image.fromarray(frame).save(image_path, format="JPEG")
    row = {"timestamp": timestamp.isoformat(), "site_id": site_id,
           "motion_value": motion, "image_filename": f"images/{filename}"}
    try:
        log_event(log_dir, row)
    except Exception:
        image_path.unlink(missing_ok=True)
        raise
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site", "--site-id", dest="site_id", required=True)
    parser.add_argument("--demo", action="store_true", help="use a webcam for the table-top demo")
    parser.add_argument("--fake-image", action="store_true",
                        help="save one plain test image and log motion_value=0.0, then exit without a camera")
    parser.add_argument("--camera", choices=("webcam", "picamera"), default="webcam")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--motion-threshold", type=float, default=0.03,
                        help="changed-pixel fraction required to trigger (default: 0.03)")
    parser.add_argument("--cooldown", type=float, default=3,
                        help="minimum seconds between captures (default: 3)")
    parser.add_argument("--max-events", type=int, default=0, help="stop after N events; 0 runs continuously")
    args = parser.parse_args(argv)
    if not args.site_id.strip():
        parser.error("--site must not be empty")
    if not 0 < args.motion_threshold <= 1:
        parser.error("--motion-threshold must be greater than 0 and at most 1")
    if not np.isfinite(args.cooldown) or args.cooldown < 0 or args.max_events < 0:
        parser.error("--cooldown must be finite and nonnegative; --max-events must be nonnegative")

    camera = None
    try:
        if args.fake_image:
            frame = np.full((480, 640, 3), 128, dtype=np.uint8)
            row = record_event(args.log_dir, args.site_id, frame, 0.0)
            print(f"{row['timestamp']} TEST IMAGE motion=0.000 {row['image_filename']}", flush=True)
            return
        camera = Camera("webcam" if args.demo else args.camera, args.camera_index)
        previous = motion_frame(camera.read())
        last_capture = float("-inf")
        count = 0
        print(f"Station {args.site_id}: waiting for motion. Ctrl+C to stop.", flush=True)
        while args.max_events == 0 or count < args.max_events:
            frame = camera.read()
            current = motion_frame(frame)
            motion = motion_value(previous, current)
            previous = current
            now = time.monotonic()
            if motion >= args.motion_threshold and now - last_capture >= args.cooldown:
                row = record_event(args.log_dir, args.site_id, frame, motion)
                last_capture = now
                count += 1
                print(f"{row['timestamp']} motion={motion:.3f} {row['image_filename']}", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStation stopped.")
    except (ImportError, RuntimeError, OSError, ValueError) as exc:
        parser.exit(1, f"Station error: {exc}\n")
    finally:
        if camera is not None:
            camera.close()


if __name__ == "__main__":
    main()
