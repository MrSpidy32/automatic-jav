#!/usr/bin/env python3
import os
import csv
import json
import re
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# =========================
# CONFIG
# =========================
RESULTS_DIR = "results/processed"
INPUT_FILE = os.path.join(RESULTS_DIR, "combined.csv")

OUTPUT_DIR = "docs"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "codes.html")
# codes.txt is critical for other scripts to check "is this a JAV.guru code?"
OUTPUT_RAW_CODE_FILE = os.path.join(OUTPUT_DIR, "codes.txt")

PAGE_COL = "page_url"

# match codes like: dldss-436, ipx-123, abcd-9999
CODE_RE = re.compile(r"\b[a-z]{2,6}-\d{2,5}\b", re.IGNORECASE)

# =========================
# EXTRACT ALL CODES
# =========================
def extract_all():
    guru = set()
    all_codes = set()
    
    # 1. JAV.guru
    if os.path.isfile(INPUT_FILE):
        with open(INPUT_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames and PAGE_COL in reader.fieldnames:
                for row in reader:
                    text = (row.get(PAGE_COL) or "").lower()
                    for m in CODE_RE.findall(text):
                        guru.add(m.upper())
                        all_codes.add(m.upper())

    # 2. MissAV
    missav_file = os.path.join(OUTPUT_DIR, "missav.json")
    if os.path.isfile(missav_file):
        with open(missav_file, encoding="utf-8") as f:
            try:
                data = json.load(f)
                for d in data:
                    c = d.get("code", "")
                    if c:
                        all_codes.add(c.upper())
            except Exception:
                pass

    # 3. OneJAV
    onejav_file = os.path.join(RESULTS_DIR, "onejav.csv")
    if os.path.isfile(onejav_file):
        with open(onejav_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                c = row.get("code", "")
                if c:
                    all_codes.add(c.upper())

    # 4. JavCT
    javct_file = os.path.join(RESULTS_DIR, "javct.csv")
    if os.path.isfile(javct_file):
        with open(javct_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                c = row.get("code", "")
                if c:
                    all_codes.add(c.upper())

    return sorted(guru), sorted(all_codes)


# =========================
# BUILD HTML
# =========================
def build_html(codes):
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(codes)

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("codes.html")
    return template.render(codes=codes, total=total, generated=generated, current_page="codes")


# =========================
# MAIN
# =========================
def build():
    guru_codes, all_codes = extract_all()
    if not all_codes:
        print("ℹ️ No codes found.")
        return

    # ONLY write guru_codes to codes.txt to maintain cross-referencing logic
    with open(OUTPUT_RAW_CODE_FILE, "w", encoding="utf-8") as rc:
        for code in guru_codes:
            rc.write(f"{code}\n")

    # Write all codes to the HTML UI
    html = build_html(all_codes)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Code index built at {OUTPUT_FILE}")
    print(f"   JAV.guru Codes: {len(guru_codes)}")
    print(f"   Total All Codes: {len(all_codes)}")


if __name__ == "__main__":
    build()
