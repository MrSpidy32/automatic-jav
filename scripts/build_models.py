import csv
import json
from pathlib import Path
from urllib.parse import quote
from jinja2 import Environment, FileSystemLoader

# =========================
# CONFIGURATION
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
JAVCT_MODELS_CSV = BASE_DIR / "results/processed/javct_models.csv"
ONEJAV_CSV = BASE_DIR / "results/processed/onejav.csv"

OUTPUT_JSON = BASE_DIR / "docs/models.json"
OUTPUT_HTML = BASE_DIR / "docs/models.html"




def generate():
    models = {}
    
    # 1. Load from JavCT
    if JAVCT_MODELS_CSV.exists():
        with JAVCT_MODELS_CSV.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                name = r.get("name", "").strip()
                if not name:
                    continue
                models[name.lower()] = {
                    "name": name,
                    "image_url": r.get("image_url", ""),
                    "page_url": r.get("page_url", ""),
                    "views": r.get("views", ""),
                    "source": "JavCT"
                }

    # 2. Extract from OneJAV
    if ONEJAV_CSV.exists():
        with ONEJAV_CSV.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                actresses_raw = r.get("actresses", "")
                if not actresses_raw:
                    continue
                for name_raw in actresses_raw.split(","):
                    name = name_raw.strip()
                    if not name:
                        continue
                    k = name.lower()
                    if k not in models:
                        # Fallback page URL pointing to a OneJAV search if we want
                        page_url = f"https://onejav.com/actress/{quote(name)}"
                        models[k] = {
                            "name": name,
                            "image_url": "",
                            "page_url": page_url,
                            "views": "",
                            "source": "OneJAV"
                        }
                        
    data = list(models.values())
    
    # Ensure output folders exist
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_JSON.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    env = Environment(loader=FileSystemLoader(BASE_DIR / "templates"))
    template = env.get_template("models.html")
    html = template.render(current_page="models")
    OUTPUT_HTML.write_text(html, encoding="utf-8")

    print(f"[ok] Models page generated: {len(data)} total models.")

if __name__ == "__main__":
    generate()
