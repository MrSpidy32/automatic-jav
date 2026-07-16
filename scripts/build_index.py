#!/usr/bin/env python3
import os
import csv
import re
import json
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

COMBINED_FILE = os.path.join("results", "processed", "combined.csv")
MISSAV_JSON = os.path.join("docs", "missav.json")
DOCS_DIR = "docs"
OUTPUT_FILE = os.path.join(DOCS_DIR, "home.html")
TEMPLATES_DIR = "templates"

ITEMS_PER_PAGE = 20

# Extract date from source file: jav_links_2025-12-28_181113.csv -> 2025-12-28
SRC_DATE_RE = re.compile(r"jav_links_(\d{4}-\d{2}-\d{2})_\d{6}\.csv$", re.IGNORECASE)
CODE_RE = re.compile(r"\b[a-z]{2,6}-\d{2,5}\b", re.IGNORECASE)


def date_from_source_file(source_file: str) -> str:
    if not source_file:
        return ""
    m = SRC_DATE_RE.search(source_file.strip())
    return m.group(1) if m else ""


def load_missav_lookup() -> dict:
    """Load missav.json and return {code_lower: entries_list}."""
    if not os.path.isfile(MISSAV_JSON):
        print("ℹ️  missav.json not found, streams will be empty")
        return {}
    try:
        with open(MISSAV_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            item["code"].strip().lower(): item.get("entries", [])
            for item in data
            if item.get("code")
        }
    except (json.JSONDecodeError, KeyError):
        return {}


def extract_code(url: str) -> str:
    """Extract first video code from a URL."""
    codes = CODE_RE.findall(url)
    return codes[0].lower() if codes else ""


def load_items():
    if not os.path.isfile(COMBINED_FILE):
        print(f"❌ Missing combined file: {COMBINED_FILE}")
        return []

    missav = load_missav_lookup()
    matched = 0

    items = []
    with open(COMBINED_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("❌ combined.csv has no headers")
            return []

        if "page_url" not in reader.fieldnames or "image_url" not in reader.fieldnames:
            print("❌ combined.csv must have page_url and image_url")
            return []

        has_source = "source_file" in reader.fieldnames
        has_date_added = "date_added" in reader.fieldnames

        for row in reader:
            page_url = (row.get("page_url") or "").strip()
            image_url = (row.get("image_url") or "").strip()

            if not page_url:
                continue

            date_added = (row.get("date_added") or "").strip() if has_date_added else ""
            if not date_added and has_source:
                date_added = date_from_source_file((row.get("source_file") or "").strip())

            code = extract_code(page_url)
            entries = missav.get(code, [])
            if entries:
                matched += 1

            items.append({
                "page_url": page_url,
                "image_url": image_url,
                "date_added": date_added,
                "code": code.upper(),
                "streams": entries,
            })

    print(f"ℹ️  {matched}/{len(items)} items matched with MissAV streams")
    return items


def build_home():
    os.makedirs(DOCS_DIR, exist_ok=True)

    items = load_items()
    if not items:
        print("ℹ️ No items to build home page.")
        return

    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(items)
    with_streams = sum(1 for it in items if it["streams"])

    # Build JS data — use json.dumps for entries to avoid escaping issues
    js_entries = []
    for it in items:
        entry = {
            "u": it["page_url"],
            "i": it["image_url"],
            "d": it["date_added"],
            "c": it["code"],
            "s": it["streams"],
        }
        js_entries.append(entry)

    js_items = json.dumps(js_entries, separators=(",", ":"), ensure_ascii=False)

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template("home.html")
    
    html = template.render(
        total=total,
        with_streams=with_streams,
        generated=generated,
        ITEMS_PER_PAGE=ITEMS_PER_PAGE,
        js_items=js_items,
        current_page="home"
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Home built: {OUTPUT_FILE}")
    print(f"   Items: {total}")
    print(f"   With streams: {with_streams}")
    print(f"   Source: {COMBINED_FILE}")


if __name__ == "__main__":
    build_home()
