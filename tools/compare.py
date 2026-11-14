"""Command-line entry point for comparing satellite risk with station logs."""
from satellite import compare, data_io, similar, trends

def main():
    cfg = data_io.load_config()
    reefs = data_io.load_reefs()
    variable = cfg["risk"]["variable"]
    vc = cfg["variables"][variable]
    results = trends.analyze_variable(reefs.site_id, lambda sid: data_io.load_series(vc, sid), cfg)
    risk = similar.risk_table(results, reefs, cfg)
    events = compare.load_events(cfg["station"]["log_dir"])
    print(risk[["site_id", "name", "risk_class", "status"]].to_string(index=False))
    print(f"\nStation events loaded: {len(events)}")

if __name__ == "__main__":
    main()
