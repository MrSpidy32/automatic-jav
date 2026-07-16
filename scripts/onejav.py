from __future__ import annotations

import asyncio
import csv
import json
import os
import re
import random
import time
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin, unquote

import aiohttp
from crawl4ai import AsyncWebCrawler

# =========================
# CONFIGURATION
# =========================

BASE_URL = "https://onejav.com"
DAYS_TO_SCRAPE = 20
MAX_RETRIES = 5
MAX_CONCURRENCY = 4

TIMEOUT = 30

# Directories
RAW_DIR = Path("results/raw_onejav")
MASTER_CSV = Path("results/processed/onejav.csv")

# Ensure working directory is the project root
os.chdir(Path(__file__).resolve().parent.parent)

# Configurable endpoints
TAGS_TO_SCRAPE = ["JavPlayer", "Cuckold", "Creampie", "Amateur", "Documentary"]
TOP_NEW_ACTRESSES_LIMIT = 10

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128 Safari/537.36"
    ),
    "Accept": "text/html",
    "Connection": "keep-alive",
}

# =========================
# DATA MODEL
# =========================

@dataclass
class TorrentItem:
    code: str
    title: str
    size: str
    image_url: str
    torrent_url: str
    tags: str           # comma-separated
    actresses: str      # comma-separated
    date: str           # YYYY-MM-DD
    page_url: str


FIELDNAMES = [
    "code", "title", "size", "image_url", "torrent_url",
    "tags", "actresses", "date", "page_url",
]

# =========================
# CF BOOTSTRAP (crawl4ai)
# =========================

async def get_cf_cookies(start_url: str) -> dict:
    """Use crawl4ai ONCE to pass Cloudflare and extract cookies."""
    print("🛡️  Getting Cloudflare clearance via crawl4ai (OneJAV)...")
    try:
        async with AsyncWebCrawler() as crawler:
            res = await crawler.arun(start_url)
            cookies = {}
            if hasattr(res, "cookies") and res.cookies:
                cookies.update(res.cookies)
            if not cookies:
                print("⚠️  No cookies extracted — fallback will be used")
            else:
                print(f"✅ CF cookies obtained: {list(cookies.keys())}")
            return cookies
    except Exception as e:
        print(f"⚠️  crawl4ai CF bootstrap failed: {e}")
        return {}


# =========================
# FETCH HELPERS
# =========================

async def fetch_aiohttp(
    session: aiohttp.ClientSession,
    url: str,
) -> Optional[str]:
    """Fast fetch using aiohttp with CF cookies."""
    try:
        async with session.get(url) as r:
            if r.status == 404:
                return None
            if r.status != 200:
                return None
            text = await r.text(errors="ignore")
            if "cf-browser-verification" in text.lower():
                return None
            return text
    except asyncio.CancelledError:
        raise
    except Exception:
        return None


async def fetch_crawl4ai(url: str) -> Optional[str]:
    """Last-resort fallback: full browser fetch via crawl4ai."""
    try:
        async with AsyncWebCrawler() as crawler:
            res = await crawler.arun(url)
            return res.html if res and res.html else None
    except Exception:
        return None


async def fetch_with_retries(
    session: aiohttp.ClientSession,
    url: str,
    sem: asyncio.Semaphore,
) -> Optional[str]:
    """Fetch with retries + crawl4ai fallback on final attempt."""
    for attempt in range(MAX_RETRIES):
        async with sem:
            html = await fetch_aiohttp(session, url)
        if html:
            return html

        # last-chance fallback
        if attempt == MAX_RETRIES - 1:
            print(f"🛡️  Fallback crawl4ai: {url}")
            return await fetch_crawl4ai(url)

        wait = min(8, 1.0 * (2 ** attempt)) * random.uniform(0.8, 1.2)
        print(f"  -> Retry {attempt+1}/{MAX_RETRIES} for {url} (wait {wait:.1f}s)")
        await asyncio.sleep(wait)

    return None


# =========================
# PARSER
# =========================

def parse_listing_page(html: str, fallback_date: str) -> List[TorrentItem]:
    """Parse a OneJAV page and extract torrent cards."""
    soup = BeautifulSoup(html, "html.parser")
    items = []

    for card in soup.select("div.card.mb-3"):
        try:
            title_el = card.select_one("h5.title a")
            if not title_el:
                continue
            code = title_el.get_text(strip=True)
            page_url = urljoin(BASE_URL, str(title_el.get("href", "")))

            size_el = card.select_one("h5.title span.is-size-6")
            size = size_el.get_text(strip=True) if size_el else ""

            img_el = card.select_one("img.image")
            image_url = str(img_el.get("src", "")) if img_el else ""

            # Extract date from link like "/2026/02/26"
            date_el = card.select_one("p.subtitle a")
            date_str = fallback_date
            if date_el:
                href = str(date_el.get("href", ""))
                m = re.search(r"/(\d{4})/(\d{2})/(\d{2})", href)
                if m:
                    date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

            tag_els = card.select("div.tags a.tag")
            tags = [t.get_text(strip=True) for t in tag_els]

            desc_el = card.select_one("p.level.has-text-grey-dark")
            title_text = desc_el.get_text(strip=True) if desc_el else ""

            actress_els = card.select("div.panel a.panel-block")
            actresses = [a.get_text(strip=True) for a in actress_els]

            dl_el = card.select_one("a.button[href*='/download/']")
            torrent_url = ""
            if dl_el:
                torrent_url = urljoin(BASE_URL, str(dl_el.get("href", "")))

            items.append(TorrentItem(
                code=code,
                title=title_text,
                size=size,
                image_url=image_url,
                torrent_url=torrent_url,
                tags=", ".join(tags),
                actresses=", ".join(actresses),
                date=date_str,
                page_url=page_url,
            ))

        except Exception as e:
            print(f"[parse error] {e}")
            continue

    return items


# =========================
# STORAGE
# =========================

def save_to_folder(folder_name: str, file_name: str, items: List[TorrentItem]):
    """Save extracted items to specific subfolder inside results/raw_onejav/."""
    if not items:
        return

    out_dir = RAW_DIR / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = "".join([c for c in file_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    if not safe_name:
        safe_name = "unnamed_" + str(int(time.time()))

    csv_path = out_dir / f"{safe_name}.csv"
    json_path = out_dir / f"{safe_name}.json"

    # Deduplicate
    seen = set()
    unique_items = []
    for it in items:
        k = it.code.lower()
        if k not in seen:
            seen.add(k)
            unique_items.append(it)

    rows = [asdict(it) for it in unique_items]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"[+] Saved {len(rows)} items to {folder_name}/{safe_name}")


# =========================
# ASYNC SCRAPING ROUTINES
# =========================

async def scrape_endpoint(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    url: str,
    fallback_date: str,
) -> List[TorrentItem]:
    """Fetch URL and extract TorrentItems."""
    html = await fetch_with_retries(session, url, sem)
    if not html:
        return []
    return parse_listing_page(html, fallback_date)


async def scrape_dates(session: aiohttp.ClientSession, sem: asyncio.Semaphore):
    """Scrape the last N days (default 20)."""
    print("\n--- Scraping Dates ---")
    today = datetime.now(timezone.utc).date()

    async def _do_day(i: int):
        d = today - timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        url = f"{BASE_URL}/{d.strftime('%Y/%m/%d')}"
        items = await scrape_endpoint(session, sem, url, fallback_date=date_str)
        save_to_folder("dates", date_str, items)

    tasks = [_do_day(i) for i in range(DAYS_TO_SCRAPE)]
    await asyncio.gather(*tasks)


async def scrape_lists(session: aiohttp.ClientSession, sem: asyncio.Semaphore):
    """Scrape /new and /popular/."""
    print("\n--- Scraping Lists ---")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    new_items = await scrape_endpoint(session, sem, f"{BASE_URL}/new", fallback_date=today_str)
    save_to_folder("lists", "new", new_items)

    popular_items = await scrape_endpoint(session, sem, f"{BASE_URL}/popular/", fallback_date=today_str)
    save_to_folder("lists", "popular", popular_items)


async def scrape_tags(session: aiohttp.ClientSession, sem: asyncio.Semaphore):
    """Scrape predefined tags."""
    print("\n--- Scraping Tags ---")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    async def _do_tag(tag: str):
        url = f"{BASE_URL}/tag/{tag}"
        items = await scrape_endpoint(session, sem, url, fallback_date=today_str)
        save_to_folder("tags", tag, items)

    tasks = [_do_tag(tag) for tag in TAGS_TO_SCRAPE]
    await asyncio.gather(*tasks)


async def scrape_home_page(session: aiohttp.ClientSession, sem: asyncio.Semaphore):
    """Extract 'Actress of the Day' and 'Featured Torrents' from Home."""
    print("\n--- Scraping Home Page ---")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    html = await fetch_with_retries(session, f"{BASE_URL}/", sem)
    if not html:
        return

    soup = BeautifulSoup(html, "html.parser")

    # Extract Actress of the Day
    actress_url = None
    actress_name = "ActressOfTheDay"
    for col in soup.select(".column"):
        if "Actress of the Day" in col.get_text():
            for a in col.select("a"):
                href = str(a.get("href", ""))
                if "/actress/" in href:
                    actress_url = urljoin(BASE_URL, href)
                    actress_name = a.get_text(strip=True)
                    break
            break

    if actress_url:
        print(f"[*] Found Actress of the Day: {actress_name} ({actress_url})")
        items = await scrape_endpoint(session, sem, actress_url, fallback_date=today_str)
        save_to_folder("home", f"actress_of_the_day_{unquote(actress_name)}", items)

    # Extract Featured Torrents
    featured_links = []
    for col in soup.select(".column"):
        if "Featured Torrents" in col.get_text():
            for a in col.select("a"):
                href = str(a.get("href", ""))
                if "/torrent/" in href:
                    featured_links.append(urljoin(BASE_URL, href))
            break

    if featured_links:
        print(f"[*] Found {len(featured_links)} Featured Torrents")

        async def _do_featured(link: str):
            return await scrape_endpoint(session, sem, link, fallback_date=today_str)

        results = await asyncio.gather(*[_do_featured(l) for l in featured_links])
        featured_items = [it for batch in results for it in batch]
        save_to_folder("home", "featured", featured_items)


async def scrape_new_actresses(session: aiohttp.ClientSession, sem: asyncio.Semaphore):
    """Scrape top N actresses from the 'new releases' actress feed."""
    print("\n--- Scraping New Release Actresses ---")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"{BASE_URL}/actress/?order=release"
    html = await fetch_with_retries(session, url, sem)
    if not html:
        return

    soup = BeautifulSoup(html, "html.parser")
    actress_urls = []

    # Actress cards: .column > .card > a[href*=/actress/] + p.card-header-title
    for col in soup.select(".column"):
        card = col.select_one(".card")
        if not card:
            continue
        a_tag = card.select_one("a[href*='/actress/']")
        if not a_tag:
            continue
        href = str(a_tag.get("href", ""))
        # Name is in the card header, not the link (link only has empty span)
        name_el = card.select_one("p.card-header-title")
        name = name_el.get_text(strip=True) if name_el else ""
        if name and "/actress/" in href:
            actress_urls.append((name, urljoin(BASE_URL, href)))

    # Deduplicate and limit
    unique_actresses = []
    seen = set()
    for name, a_url in actress_urls:
        if name and name not in seen:
            seen.add(name)
            unique_actresses.append((name, a_url))

    top_actresses = unique_actresses[:TOP_NEW_ACTRESSES_LIMIT]
    print(f"[*] Scraping top {len(top_actresses)} new release actresses...")

    async def _do_actress(name: str, a_url: str):
        items = await scrape_endpoint(session, sem, a_url, fallback_date=today_str)
        save_to_folder("actresses", f"{unquote(name)}", items)

    tasks = [_do_actress(name, a_url) for name, a_url in top_actresses]
    await asyncio.gather(*tasks)


# =========================
# MERGE LOGIC
# =========================

def merge_all_csvs():
    """Merge ALL .csv files recursively from results/raw_onejav/ -> onejav.csv"""
    print("\n--- Merging All Data ---")
    seen: set[str] = set()
    rows: list[dict] = []

    if not RAW_DIR.exists():
        return

    csv_files = list(RAW_DIR.rglob("*.csv"))
    print(f"[*] Found {len(csv_files)} CSV files to merge.")

    for file in sorted(csv_files, reverse=True):
        with file.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                code = r.get("code", "").strip().lower()
                if not code or code in seen:
                    continue
                seen.add(code)
                rows.append(r)

    MASTER_CSV.parent.mkdir(parents=True, exist_ok=True)

    with MASTER_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[+] Master CSV: {MASTER_CSV} ({len(rows)} unique rows)")


# =========================
# MAIN
# =========================

async def main():
    # Step 1 — pass CF once
    cookies = await get_cf_cookies(f"{BASE_URL}/new")

    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    connector = aiohttp.TCPConnector(
        limit=40,
        limit_per_host=10,
        ttl_dns_cache=300,
    )
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async with aiohttp.ClientSession(
        headers=HEADERS,
        cookies=cookies,
        timeout=timeout,
        connector=connector,
    ) as session:
        await scrape_dates(session, sem)
        await scrape_lists(session, sem)
        await scrape_tags(session, sem)
        await scrape_home_page(session, sem)
        await scrape_new_actresses(session, sem)

    merge_all_csvs()


if __name__ == "__main__":
    asyncio.run(main())
