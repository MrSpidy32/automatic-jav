
#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import random
import re
import csv
import os
from datetime import datetime
from typing import Optional, Set, Tuple

import aiohttp
from bs4 import BeautifulSoup

from crawl4ai import AsyncWebCrawler

# ================= CONFIG =================

BASE_URL = "https://jav.guru/page/{}/"
PAGES_TO_FETCH = 40

MAX_CONCURRENCY = 6
RETRIES = 3
TIMEOUT = 30

OUT_DIR = "results/raw"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128 Safari/537.36"
    ),
    "Accept": "text/html",
    "Connection": "keep-alive",
}

POST_PATTERN = re.compile(r"^https?://jav\.guru/\d+/.+")

# ==========================================

results: Set[Tuple[str, str]] = set()
results_lock: Optional[asyncio.Lock] = None

# ================= CF BOOTSTRAP =================

async def get_cf_cookies(start_url: str) -> dict:
    """
    Use crawl4ai ONCE to pass Cloudflare
    and extract cf_clearance cookie.
    """
    print("🛡️ Getting Cloudflare clearance via crawl4ai...")
    async with AsyncWebCrawler() as crawler:
        res = await crawler.arun(start_url)

        cookies = {}
        if hasattr(res, "cookies") and res.cookies:
            cookies.update(res.cookies)

        if not cookies:
            print("⚠️ No cookies extracted — fallback will be used")
        else:
            print(f"✅ CF cookies obtained: {list(cookies.keys())}")

        return cookies


# ================= FETCH =================

async def fetch_aiohttp(
    session: aiohttp.ClientSession,
    url: str,
) -> Optional[str]:
    try:
        async with session.get(url) as r:
            if r.status != 200:
                return None
            text = await r.text(errors="ignore")

            # reject CF challenge html
            if "cf-browser-verification" in text.lower():
                return None

            return text
    except asyncio.CancelledError:
        raise
    except Exception:
        return None


async def fetch_crawl4ai(url: str) -> Optional[str]:
    try:
        async with AsyncWebCrawler() as crawler:
            res = await crawler.arun(url)
            return res.html if res and res.html else None
    except Exception:
        return None


async def fetch_with_retries(
    session: aiohttp.ClientSession,
    url: str,
) -> Optional[str]:
    for attempt in range(RETRIES + 1):
        html = await fetch_aiohttp(session, url)
        if html:
            return html

        # last-chance fallback
        if attempt == RETRIES:
            print("🛡️ Fallback crawl4ai:", url)
            return await fetch_crawl4ai(url)

        await asyncio.sleep(min(4, 0.6 * (2 ** attempt)) * random.uniform(0.8, 1.2))

# ================= PARSING (OLD LOGIC) =================

def extract_links(html: str) -> Set[Tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    found = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if POST_PATTERN.match(href):
            img = a_tag.find("img")
            if img and img.get("src"):
                found.add((href, img["src"]))

    return found


# ================= WORKER =================

async def process_page(
    page_no: int,
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
):
    url = BASE_URL.format(page_no)

    async with sem:
        html = await fetch_with_retries(session, url)

    if not html:
        print(f"❌ Page {page_no} failed")
        return

    found = extract_links(html)

    async with results_lock:
        results.update(found)

    print(f"✅ Page {page_no}: +{len(found)}")


# ================= MAIN =================

async def main():
    global results_lock
    results_lock = asyncio.Lock()
    os.makedirs(OUT_DIR, exist_ok=True)
    
    # Step 1 — pass CF once
    cookies = await get_cf_cookies(BASE_URL.format(1))

    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    connector = aiohttp.TCPConnector(
        limit=40,
        limit_per_host=15,
        ttl_dns_cache=300,
    )

    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async with aiohttp.ClientSession(
        headers=HEADERS,
        cookies=cookies,
        timeout=timeout,
        connector=connector,
    ) as session:

        tasks = [
            process_page(page, session, sem)
            for page in range(1, PAGES_TO_FETCH + 1)
        ]
        await asyncio.gather(*tasks)

    # Save CSV
    today = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filepath = os.path.join(OUT_DIR, f"jav_links_{today}.csv")

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["page_url", "image_url"])
        for row in sorted(results):
            writer.writerow(row)

    print(f"\n🎉 Saved {len(results)} entries → {filepath}")


if __name__ == "__main__":
    asyncio.run(main())
