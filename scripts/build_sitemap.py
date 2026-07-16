#!/usr/bin/env python3
import os
import csv
import json
import re
from datetime import datetime
from urllib.parse import urlsplit
from jinja2 import Environment, FileSystemLoader

RESULTS_DIR = os.path.join("results", "processed")
DOCS_DIR = "docs"
OUTPUT_FILE = os.path.join(DOCS_DIR, "sitemap.html")

SRC_DATE_RE = re.compile(r"jav_links_(\d{4}-\d{2}-\d{2})_\d{6}\.csv$", re.IGNORECASE)

def date_from_source_file(source_file: str) -> str:
    if not source_file:
        return ""
    m = SRC_DATE_RE.search(source_file.strip())
    return m.group(1) if m else ""

def host_from_url(url: str) -> str:
    try:
        return (urlsplit(url).netloc or "").lower()
    except Exception:
        return ""

def load_rows():
    urls = set()
    rows = []
    
    def add_row(url, date_added):
        if not url or url in urls:
            return
        urls.add(url)
        rows.append({
            "page_url": url,
            "date_added": date_added,
            "host": host_from_url(url)
        })

    # 1. JAV.guru
    comb_path = os.path.join(RESULTS_DIR, "combined.csv")
    if os.path.isfile(comb_path):
        with open(comb_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []
            has_source = "source_file" in fields
            has_date_added = "date_added" in fields
            
            for r in reader:
                url = (r.get("page_url") or "").strip()
                if not url:
                    continue
                d = (r.get("date_added") or "").strip() if has_date_added else ""
                if not d and has_source:
                    d = date_from_source_file((r.get("source_file") or "").strip())
                add_row(url, d)

    # 2. MissAV
    missav_path = os.path.join(RESULTS_DIR, "missav.csv")
    if os.path.isfile(missav_path):
        with open(missav_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                add_row(r.get("page_url", "").strip(), "")
                
    # 3. OneJAV
    onejav_path = os.path.join(RESULTS_DIR, "onejav.csv")
    if os.path.isfile(onejav_path):
        with open(onejav_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                add_row(r.get("page_url", "").strip(), r.get("date", "").strip())
                
    # 4. JavCT
    javct_path = os.path.join(RESULTS_DIR, "javct.csv")
    if os.path.isfile(javct_path):
        with open(javct_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                add_row(r.get("page_url", "").strip(), r.get("date_scraped", "").strip())

    # newest-first by date_added, then by URL
    rows.sort(key=lambda x: (x["date_added"] or "", x["page_url"]), reverse=True)
    return rows


def build_sitemap():
    os.makedirs(DOCS_DIR, exist_ok=True)

    rows = load_rows()
    if not rows:
        print("ℹ️ No rows found to build sitemap.")
        return

    # Export CSV/JSON for download
    sitemap_json = os.path.join(DOCS_DIR, "sitemap.json")
    sitemap_csv = os.path.join(DOCS_DIR, "sitemap_export.csv")
    
    with open(sitemap_json, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
        
    with open(sitemap_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["page_url", "date_added", "host"])
        writer.writeheader()
        writer.writerows(rows)

    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("sitemap.html")
    html = template.render(rows=rows, generated=generated, current_page="sitemap")

    print(f"✅ Sitemap built: {OUTPUT_FILE}")
    print(f"   Links: {len(rows)}")

if __name__ == "__main__":
    build_sitemap()
