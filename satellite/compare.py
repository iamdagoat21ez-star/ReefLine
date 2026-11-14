"""The link between the two systems: does the Pi station's observation agree
with the satellite risk class? (build document, section 6.2)"""
import csv

from .data_io import ROOT


def load_events(log_dir="outputs/logs"):
    path = ROOT / log_dir / "events.csv"
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def station_summary(events, site_id):
    ev = [e for e in events if e.get("site_id") == site_id]
    if not ev:
        return None
    bis = [float(e["bleaching_index"]) for e in ev if e.get("bleaching_index")]
    return {
        "events": len(ev),
        "mean_bi": sum(bis) / len(bis) if bis else None,
        "latest": ev[-1],
        "latest_class": ev[-1].get("class_label"),
    }


def concordance(risk_class, pi_class):
    """Consistent / Partially consistent / Not consistent. Reported honestly."""
    if (risk_class == "High" and pi_class in ("Paling", "Bleached")) or \
       (risk_class == "Low" and pi_class == "Healthy"):
        return "Consistent"
    if (risk_class == "High" and pi_class == "Healthy") or \
       (risk_class == "Low" and pi_class == "Bleached"):
        return "Not consistent"
    return "Partially consistent"
