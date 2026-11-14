"""Create a small offline data bundle for a demo or field laptop."""
from pathlib import Path
import zipfile
ROOT = Path(__file__).resolve().parent.parent

def create_bundle(output="outputs/reefline_data_bundle.zip"):
    output_path = ROOT / output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    include = [ROOT / "data/reefs.csv"]
    include += sorted((ROOT / "data/sst").glob("*.csv"))
    include += sorted((ROOT / "data/chlorophyll").glob("*.csv"))
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in include:
            zf.write(path, path.relative_to(ROOT))
    return output_path

if __name__ == "__main__":
    print(create_bundle())
