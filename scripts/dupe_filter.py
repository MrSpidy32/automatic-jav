#!/usr/bin/env python3
import os
import csv
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

RAW_RESULTS_DIR = "results/raw"
OUTPUT_DIR = "results/processed"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "combined.csv")

DEDUP_COL = "page_url"   # dedupe key
IMAGE_COL = "image_url"  # optional; just kept as-is unless you want to dedupe on both

def normalize_url(url: str) -> str:
    """
    Normalize URLs for reliable dedupe:
    - trim whitespace
    - lowercase scheme/host
    - remove fragments (#...)
    - remove common tracking params
    - sort query params
    """
    if url is None:
        return ""
    url = url.strip()
    if not url:
        return ""

    try:
        parts = urlsplit(url)
        scheme = parts.scheme.lower()
        netloc = parts.netloc.lower()
        fragment = ""  # drop fragments

        # drop common tracking params
        drop = {
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "gclid", "fbclid"
        }
        q = [(k, v) for (k, v) in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in drop]
        query = urlencode(sorted(q), doseq=True)

        return urlunsplit((scheme, netloc, parts.path, query, fragment))
    except Exception:
        return url

def list_csv_files():
    if not os.path.isdir(RAW_RESULTS_DIR):
        raise FileNotFoundError(f"Results directory '{RAW_RESULTS_DIR}' not found.")

    files = [
        f for f in os.listdir(RAW_RESULTS_DIR)
        if f.lower().endswith(".csv") and f != os.path.basename(OUTPUT_FILE)
    ]
    # newest first by mtime
    files.sort(key=lambda f: os.path.getmtime(os.path.join(RAW_RESULTS_DIR, f)), reverse=True)
    return files

def merge_csvs():
    csv_files = list_csv_files()
    if not csv_files:
        print("ℹ️ No CSV files found.")
        return

    # superset of all columns
    all_columns = []
    all_columns_set = set()

    # dedupe store:
    # key: normalized page_url
    # value: (file_mtime, filename, row_dict)
    seen = {}

    total_rows = 0
    skipped_missing_page_url = 0
    duplicates = 0

    for fname in csv_files:
        path = os.path.join(RAW_RESULTS_DIR, fname)
        mtime = os.path.getmtime(path)

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                continue

            # Track columns
            for col in reader.fieldnames:
                if col not in all_columns_set:
                    all_columns_set.add(col)
                    all_columns.append(col)

            # Ensure required column exists
            if DEDUP_COL not in reader.fieldnames:
                print(f"⚠️ Skipping '{fname}': missing required column '{DEDUP_COL}'")
                continue

            for row in reader:
                total_rows += 1
                raw_page = row.get(DEDUP_COL, "")
                norm_page = normalize_url(raw_page)

                if not norm_page:
                    skipped_missing_page_url += 1
                    continue

                if norm_page in seen:
                    duplicates += 1
                    prev_mtime, _, _ = seen[norm_page]
                    # keep newest row
                    if mtime > prev_mtime:
                        seen[norm_page] = (mtime, fname, row)
                else:
                    seen[norm_page] = (mtime, fname, row)

    # output columns = all columns + extras
    out_columns = list(all_columns)
    extras = ["normalized_page_url", "source_file", "source_file_mtime"]
    for c in extras:
        if c not in out_columns:
            out_columns.append(c)

    # Write output (newest first)
    items = sorted(seen.items(), key=lambda kv: kv[1][0], reverse=True)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=out_columns)
        writer.writeheader()

        for norm_page, (mtime, fname, row) in items:
            out_row = {col: row.get(col, "") for col in all_columns}
            out_row["normalized_page_url"] = norm_page
            out_row["source_file"] = fname
            out_row["source_file_mtime"] = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow(out_row)

    print("✅ Merge complete")
    print(f"   Files scanned: {len(csv_files)}")
    print(f"   Total rows read: {total_rows}")
    print(f"   Unique page_url kept: {len(seen)}")
    print(f"   Duplicates filtered: {duplicates}")
    print(f"   Skipped (blank/missing page_url): {skipped_missing_page_url}")
    print(f"   Output: {OUTPUT_FILE}")

if __name__ == "__main__":
    merge_csvs()
