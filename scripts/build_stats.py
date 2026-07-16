#!/usr/bin/env python3
import os
import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

RESULTS_DIR = "results/processed"
DOCS_DIR = "docs"

def load_data():
    stats = {
        "sources": {
            "JAV.guru": 0,
            "MissAV": 0,
            "OneJAV": 0,
            "JavCT": 0,
            "Models": 0
        },
        "timeline": defaultdict(int),
        "total_codes": 0
    }

    # 1. JAV.guru
    comb_path = os.path.join(RESULTS_DIR, "combined.csv")
    if os.path.exists(comb_path):
        with open(comb_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return stats
            has_date = "date_added" in reader.fieldnames
            has_src = "source_file" in reader.fieldnames
            count = 0
            for r in reader:
                count += 1
                d = r.get("date_added", "") if has_date else ""
                if not d and has_src:
                    m = re.search(r"(\d{4}-\d{2}-\d{2})", r.get("source_file", ""))
                    d = m.group(1) if m else ""
                if d:
                    stats["timeline"][d] += 1
            stats["sources"]["JAV.guru"] = count

    # 2. MissAV
    missav_path = os.path.join(RESULTS_DIR, "missav.csv")
    if os.path.exists(missav_path):
        with open(missav_path, newline="", encoding="utf-8") as f:
            stats["sources"]["MissAV"] = sum(1 for _ in csv.DictReader(f))

    # 3. OneJAV
    onejav_path = os.path.join(RESULTS_DIR, "onejav.csv")
    if os.path.exists(onejav_path):
        with open(onejav_path, newline="", encoding="utf-8") as f:
            stats["sources"]["OneJAV"] = sum(1 for _ in csv.DictReader(f))

    # 4. JavCT
    javct_path = os.path.join(RESULTS_DIR, "javct.csv")
    if os.path.exists(javct_path):
        with open(javct_path, newline="", encoding="utf-8") as f:
            stats["sources"]["JavCT"] = sum(1 for _ in csv.DictReader(f))

    # 5. Models
    models_path = os.path.join(RESULTS_DIR, "javct_models.csv")
    if os.path.exists(models_path):
        with open(models_path, newline="", encoding="utf-8") as f:
            stats["sources"]["Models"] = sum(1 for _ in csv.DictReader(f))

    # Get total unique codes
    codes_path = os.path.join(DOCS_DIR, "codes.txt")
    if os.path.exists(codes_path):
        with open(codes_path, encoding="utf-8") as f:
            stats["total_codes"] = len([l for l in f.read().splitlines() if l.strip()])

    return stats



def build():
    os.makedirs(DOCS_DIR, exist_ok=True)
    stats = load_data()
    
    with open(os.path.join(DOCS_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
        
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("stats.html")
    html = template.render(current_page="stats")
    with open(os.path.join(DOCS_DIR, "stats.html"), "w", encoding="utf-8") as f:
        f.write(html)
        
    print("✅ Stats Dashboard generated")

if __name__ == "__main__":
    build()
