from __future__ import annotations

import asyncio
import csv
import json
import os
import random
import time
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin

import aiohttp
from crawl4ai import AsyncWebCrawler

# =========================
# CONFIGURATION
# =========================

BASE_URL = "https://javct.net"
MAX_RETRIES = 5
MAX_CONCURRENCY = 6
MAX_CATEGORIES = 50
TIMEOUT = 30

RAW_DIR = Path("results/raw_javct")
MASTER_CSV = Path("results/processed/javct.csv")
MODELS_CSV = Path("results/processed/javct_models.csv")

os.chdir(Path(__file__).resolve().parent.parent)

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
# DATA MODELS
# =========================

@dataclass
class JavctVideo:
    code: str
    title: str
    image_url: str
    page_url: str
    views: str
    date_scraped: str

@dataclass
class JavctModel:
    name: str
    image_url: str
    page_url: str
    views: str
    date_scraped: str

VIDEO_FIELDS = ["code", "title", "image_url", "page_url", "views", "date_scraped"]
MODEL_FIELDS = ["name", "image_url", "page_url", "views", "date_scraped"]

# =========================
# CF BOOTSTRAP (crawl4ai)
# =========================

async def get_cf_cookies(start_url: str) -> dict:
    """Use crawl4ai ONCE to pass Cloudflare and extract cookies."""
    print("🛡️  Getting Cloudflare clearance via crawl4ai (JavCT)...")
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
# PARSERS
# =========================

def parse_videos(html: str) -> List[JavctVideo]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for card in soup.select("div.card"):
        try:
            cat_el = card.select_one("span.card__category a")
            code = cat_el.get_text(strip=True) if cat_el else ""
            if not code:
                continue

            title_el = card.select_one("h3.card__title a")
            title = title_el.get_text(strip=True) if title_el else ""

            play_el = card.select_one("a.card__play")
            page_url = urljoin(BASE_URL, str(play_el.get("href", ""))) if play_el else ""

            img_el = card.select_one("img.lazy")
            image_url = ""
            if img_el:
                image_url = str(img_el.get("data-src", img_el.get("src", "")))

            rate_el = card.select_one("span.card__rate")
            views = rate_el.get_text(strip=True) if rate_el else ""

            items.append(JavctVideo(
                code=code,
                title=title,
                image_url=image_url,
                page_url=page_url,
                views=views,
                date_scraped=today,
            ))
        except Exception as e:
            print(f"[video parse error] {e}")
            continue

    return items


def parse_models(html: str) -> List[JavctModel]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for card in soup.select("div.card"):
        try:
            title_el = card.select_one("h3.card__title a")
            if not title_el:
                continue

            name = title_el.get_text(strip=True)
            page_url = urljoin(BASE_URL, str(title_el.get("href", "")))

            img_el = card.select_one("img.lazy")
            image_url = ""
            if img_el:
                image_url = str(img_el.get("data-src", img_el.get("src", "")))

            rate_el = card.select_one("span.card__rate")
            views = rate_el.get_text(strip=True) if rate_el else ""

            items.append(JavctModel(
                name=name,
                image_url=image_url,
                page_url=page_url,
                views=views,
                date_scraped=today,
            ))
        except Exception as e:
            print(f"[model parse error] {e}")
            continue

    return items


def parse_categories(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for a in soup.select(".card__title a"):
        href = str(a.get("href", ""))
        if "/category/" in href:
            urls.append(urljoin(BASE_URL, href))

    if not urls:
        for a in soup.select("a"):
            href = str(a.get("href", ""))
            if "/category/" in href:
                urls.append(urljoin(BASE_URL, href))

    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)

    return unique


# =========================
# STORAGE
# =========================

def save_items(folder: str, filename: str, items: list, is_model: bool = False):
    if not items:
        return

    out_dir = RAW_DIR / folder
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    if not safe_name:
        safe_name = "unnamed_" + str(int(time.time()))
    csv_path = out_dir / f"{safe_name}.csv"

    fields = MODEL_FIELDS if is_model else VIDEO_FIELDS

    seen = set()
    unique = []
    for it in items:
        key = getattr(it, "name" if is_model else "code").lower()
        if key not in seen:
            seen.add(key)
            unique.append(it)

    rows = [asdict(it) for it in unique]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[+] Saved {len(rows)} items to {folder}/{safe_name}.csv")


# =========================
# ASYNC SCRAPING TASKS
# =========================

async def scrape_videos(session: aiohttp.ClientSession, sem: asyncio.Semaphore):
    """Scrape video listing endpoints concurrently."""
    print("\n--- Scraping Video Endpoints ---")
    endpoints = [
        ("amateur", "/amateur"),
        ("amateur_new", "/amateur?sort=new-releases"),
        ("uncensored_most_viewed", "/uncensored?sort=most-viewed"),
        ("uncensored", "/uncensored"),
    ]

    async def _do_endpoint(name: str, path: str):
        url = urljoin(BASE_URL, path)
        html = await fetch_with_retries(session, url, sem)
        if html:
            items = parse_videos(html)
            save_items("videos", name, items)

    tasks = [_do_endpoint(name, path) for name, path in endpoints]
    await asyncio.gather(*tasks)


async def scrape_categories_videos(session: aiohttp.ClientSession, sem: asyncio.Semaphore):
    """Scrape top N category pages."""
    print("\n--- Scraping Categories ---")
    url = urljoin(BASE_URL, "/categories")
    html = await fetch_with_retries(session, url, sem)
    if not html:
        return

    cat_urls = parse_categories(html)[:MAX_CATEGORIES]
    print(f"[*] Found categories, will scrape top {len(cat_urls)}")

    async def _do_category(c_url: str):
        c_name = c_url.rstrip("/").split("/")[-1]
        c_html = await fetch_with_retries(session, c_url, sem)
        if c_html:
            items = parse_videos(c_html)
            save_items("categories", c_name, items)

    tasks = [_do_category(c_url) for c_url in cat_urls]
    await asyncio.gather(*tasks)


async def scrape_models_page(session: aiohttp.ClientSession, sem: asyncio.Semaphore):
    """Scrape the models listing page."""
    print("\n--- Scraping Models ---")
    url = urljoin(BASE_URL, "/models")
    html = await fetch_with_retries(session, url, sem)
    if html:
        items = parse_models(html)
        save_items("models", "models_index", items, is_model=True)


# =========================
# MERGE LOGIC
# =========================

def merge_csvs():
    """Merge all video and model CSVs into master files."""
    print("\n--- Merging Data ---")
    if not RAW_DIR.exists():
        return

    # Videos
    v_seen = set()
    v_rows = []
    for f in RAW_DIR.rglob("*.csv"):
        if f.parent.name == "models":
            continue
        with f.open(newline="", encoding="utf-8") as file:
            for r in csv.DictReader(file):
                code = r.get("code", "").strip().lower()
                if not code or code in v_seen:
                    continue
                v_seen.add(code)
                v_rows.append(r)

    if v_rows:
        MASTER_CSV.parent.mkdir(parents=True, exist_ok=True)
        with MASTER_CSV.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=VIDEO_FIELDS)
            writer.writeheader()
            writer.writerows(v_rows)
        print(f"[+] Master Video CSV: {MASTER_CSV} ({len(v_rows)} rows)")

    # Models
    m_seen = set()
    m_rows = []
    models_dir = RAW_DIR / "models"
    if models_dir.exists():
        for f in models_dir.glob("*.csv"):
            with f.open(newline="", encoding="utf-8") as file:
                for r in csv.DictReader(file):
                    name = r.get("name", "").strip().lower()
                    if not name or name in m_seen:
                        continue
                    m_seen.add(name)
                    m_rows.append(r)

    if m_rows:
        MODELS_CSV.parent.mkdir(parents=True, exist_ok=True)
        with MODELS_CSV.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=MODEL_FIELDS)
            writer.writeheader()
            writer.writerows(m_rows)
        print(f"[+] Master Model CSV: {MODELS_CSV} ({len(m_rows)} rows)")


# =========================
# MAIN
# =========================

async def main():
    # Step 1 — pass CF once
    cookies = await get_cf_cookies(BASE_URL)

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
        await scrape_videos(session, sem)
        await scrape_categories_videos(session, sem)
        await scrape_models_page(session, sem)

    merge_csvs()


if __name__ == "__main__":
    asyncio.run(main())
