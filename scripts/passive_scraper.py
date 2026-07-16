#!/usr/bin/env python3
import cloudscraper
from bs4 import BeautifulSoup
import re
import csv
import time
import random
import os
from datetime import datetime

BASE_URL = "https://jav.guru/page/{}/"
PAGES_TO_FETCH = 20  # adjust as needed

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    )
}

pattern = re.compile(r"^https?://jav\.guru/\d+/.+")
results = set()

# Ensure results folder exists
OUT_DIR = "results/raw"
os.makedirs(OUT_DIR, exist_ok=True)

def main():
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "linux",
            "mobile": False,
        }
    )

    scraper.headers.update(HEADERS)

    for page in range(1, PAGES_TO_FETCH + 1):
        url = BASE_URL.format(page)
        print(f"📥 Fetching: {url}")

        try:
            r = scraper.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"❌ Failed {url}: {e}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if pattern.match(href):
                img = a_tag.find("img")
                if img and img.get("src"):
                    results.add((href, img["src"]))

        print(f"✅ Page {page} done, total links: {len(results)}")
        time.sleep(random.uniform(1, 3))  # polite crawling

    # Filename with current date & time to avoid overwriting in quick succession
    today = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = f"jav_links_{today}.csv"
    filepath = os.path.join(OUT_DIR, filename)

    # Save to CSV
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["page_url", "image_url"])
        # Sort for stable order (optional)
        for row in sorted(results):
            writer.writerow(row)

    print(f"\n🎉 Saved {len(results)} unique entries to {filepath}")


if __name__ == "__main__":
    main()
