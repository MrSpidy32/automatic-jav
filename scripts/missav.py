from __future__ import annotations
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import asyncio
import re
import os
import csv
import json
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import aiohttp

# =========================
# CONFIGURATION
# =========================


CATEGORIES = [
    "https://missav123.com/dm515/en/playlists/dprelff6",
    "https://missav123.com/dm291/en/today-hot",
    "https://missav123.com/dm23/en/siro",
    "https://missav123.com/dm515/en/new",
    "https://missav123.com/dm1/en/english-subtitle",
    "https://missav123.com/dm150/en/fc2",
    "https://missav123.com/dm3461120/en/caribbeancom",
    "https://missav123.com/dm628/en/uncensored-leak",
    "https://missav123.com/dm727/en/genres/Ntr",
    "https://missav123.com/dm311/en/genres/Orgy",
    "https://missav123.com/dm263/en/monthly-hot",
    "https://missav123.com/dm257/en/makers/Hunter",
    "https://missav123.com/dm265/en/makers/Madonna",
    "https://missav123.com/dm151/en/makers/Wanz%20Factory",
    "https://missav123.com/dm820/en/makers/Moody%27s",
    "https://missav123.com/dm66/en/makers/Prestige",
    "https://missav123.com/en/makers/Glory%20Quest",
    "https://missav123.com/dm506/en/makers/Attackers",
    "https://missav123.com/dm183/en/makers/S1",
    "https://missav123.com/dm737/en/makers/Premium",
    "https://missav123.com/dm4420/en/genres/High%20School%20Girl",
    "https://missav123.com/dm114/en/genres/Big%20Breasts",
    "https://missav123.com/dm68/en/genres/Wife",
    "https://missav123.com/dm434/en/genres/Pretty%20Girl",
    "https://missav123.com/dm143/en/genres/Humiliation",
    
    # add more categories here
]

    

MAX_PAGES = 300             # pagination depth per category
PAGE_CONCURRENCY = 12       # concurrent listing pages
POST_CONCURRENCY = 20      # concurrent post pages

RAW_DIR = "results/raw_missav"
MASTER_CSV = "results/processed/missav.csv"
OUTPUT_DIR = "docs"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)
OUTPUT_RAW_CODE_FILE = os.path.join(BASE_DIR, "docs", "codes.txt")
MISSAV_JSON_FILE = os.path.join(BASE_DIR, "docs", "missav.json")

def load_processed_codes() -> set[str]:
    """Load already-processed codes (lowercased) from missav.json."""
    if not os.path.isfile(MISSAV_JSON_FILE):
        return set()
    try:
        with open(MISSAV_JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {item["code"].strip().lower() for item in data if item.get("code")}
    except (json.JSONDecodeError, KeyError):
        return set()


def build_guru_code_urls() -> List[str]:
    """Read codes.txt, remove already-processed codes, return new MissAV URLs."""
    if not os.path.isfile(OUTPUT_RAW_CODE_FILE):
        print("[guru] codes.txt not found, skipping guru codes")
        return []

    processed = load_processed_codes()
    print(f"Already Processed Codes: {len(processed)}")

    base = "https://missav123.com/dm291/en/"
    new_urls = []
    with open(OUTPUT_RAW_CODE_FILE, "r", encoding="utf-8") as rc:
        for line in rc:
            code = line.strip()
            if code and code.lower() not in processed:
                new_urls.append(base + code)

    print(f"New Codes From Jav.Guru: {len(new_urls)}")
    return new_urls

# =========================
# HTTP FETCHER
# =========================

@dataclass
class Fetcher:
    session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=20)
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def fetch(self, url: str) -> Optional[str]:
        try:
            async with self.session.get(url) as r:
                if r.status != 200:
                    return None
                return await r.text(errors="ignore")
        except Exception:
            return None

# =========================
# DECODER UTILITIES
# =========================

def unquote_js_string(s: str) -> str:
    if not s:
        return s
    if len(s) >= 2 and s[0] in ("'", '"') and s[-1] == s[0]:
        s = s[1:-1]
    try:
        return s.encode("utf-8").decode("unicode_escape")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return s


def int_to_base(n: int, base: int) -> str:
    if n == 0:
        return "0"
    out = []
    while n:
        d = n % base
        out.append(str(d) if d < 10 else chr(ord("a") + d - 10))
        n //= base
    return "".join(reversed(out))


def decode_packed_eval(payload: str) -> Optional[str]:
    start = payload.find("eval(function(p,a,c,k,e,d)")
    if start == -1:
        return None

    chunk = payload[start:start + 500000]
    idx = chunk.find("}(")
    if idx == -1:
        return None

    args = chunk[idx + 2:]
    depth, buf = 1, []

    for ch in args:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth == 0:
            break
        buf.append(ch)

    parts, cur = [], []
    sq = dq = esc = False
    pd = 0

    for ch in "".join(buf):
        if esc:
            cur.append(ch)
            esc = False
            continue
        if ch == "\\":
            cur.append(ch)
            esc = True
            continue
        if ch == "'" and not dq:
            sq = not sq
        elif ch == '"' and not sq:
            dq = not dq
        elif ch == "(" and not sq and not dq:
            pd += 1
        elif ch == ")" and not sq and not dq:
            pd -= 1
        elif ch == "," and not sq and not dq and pd == 0:
            parts.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)

    if cur:
        parts.append("".join(cur).strip())

    if len(parts) < 4:
        return None

    p = unquote_js_string(parts[0])
    try:
        a, c = int(parts[1]), int(parts[2])
    except ValueError:
        return None
    k = unquote_js_string(parts[3].split(".split")[0]).split("|")

    for n in range(c - 1, -1, -1):
        key = int_to_base(n, a)
        val = k[n] if n < len(k) and k[n] else key
        p = re.sub(rf"\b{re.escape(key)}\b", val, p)

    return p


def extract_playlist_urls(text: str) -> List[str]:
    patterns = [
        r"https?://[^\s\"']+\.m3u8(?:\?[^\s\"']+)?",
        r"https?://[^\s\"']+/playlist(?:\.\w+)?(?:\?[^\s\"']+)?",
    ]
    urls = set()
    for pat in patterns:
        urls.update(re.findall(pat, text))
    return sorted(urls)

# =========================
# PARSING HELPERS
# =========================

def extract_video_code(url: str) -> Optional[str]:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    return slug.lower() if re.fullmatch(r"[a-z0-9]+-\d+", slug, re.I) else None


def infer_quality(url: str) -> str:
    if "1080" in url:
        return "1080p"
    if "720" in url:
        return "720p"
    if "480" in url:
        return "480p"
    return "playlist"


def infer_source(url: str) -> str:
    return urlparse(url).netloc.lower()

# =========================
# PAGINATION HELPERS
# =========================

def build_page_url(base: str, page: int) -> str:
    if page == 1:
        return base
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}page={page}"

# =========================
# PAGINATION + CATEGORIES
# =========================

async def collect_posts_for_category(
    start_url: str,
    fetcher: Fetcher,
    page_sem: asyncio.Semaphore,
) -> set[str]:

    async def fetch_page(page: int) -> set[str]:
        url = build_page_url(start_url, page)

        async with page_sem:
            html = await fetcher.fetch(url)

        if not html:
            return set()

        soup = BeautifulSoup(html, "html.parser")
        return {
            urljoin(start_url + "/", a["href"])
            for a in soup.select("div.thumbnail a[href]")
            if "/en/" in a["href"]
        }

    tasks = [fetch_page(p) for p in range(1, MAX_PAGES + 1)]
    results = await asyncio.gather(*tasks)

    posts = set()
    for r in results:
        if not r:
            continue
        posts.update(r)

    print(f"[category] {start_url} → {len(posts)} posts")
    return posts


async def collect_all_posts(fetcher: Fetcher) -> List[str]:
    processed_codes = load_processed_codes()
    print(f"Already Processed Codes (missav.json): {len(processed_codes)}")

    page_sem = asyncio.Semaphore(PAGE_CONCURRENCY)
    all_posts = set()

    # Add new guru codes (already filtered inside build_guru_code_urls)
    guru_urls = build_guru_code_urls()
    all_posts.update(guru_urls)

    # Collect from categories, then filter out already-processed
    for cat in CATEGORIES:
        posts = await collect_posts_for_category(cat, fetcher, page_sem)
        all_posts.update(posts)

    # Remove any post whose video code is already in missav.json
    before = len(all_posts)
    all_posts = {
        url for url in all_posts
        if (extract_video_code(url) or "").lower() not in processed_codes
    }
    skipped = before - len(all_posts)
    print(f"Skipped {skipped} already-processed links")
    print(f"Total Links To Be Processed: {len(all_posts)}")

    return sorted(all_posts)

# =========================
# POST PROCESSING
# =========================

async def process_post(url: str, fetcher: Fetcher, sem: asyncio.Semaphore):
    async with sem:
        html = await fetcher.fetch(url)
        if not html:
            return None
        decoded = decode_packed_eval(html) or html
        return url, extract_playlist_urls(decoded)

# =========================
# CSV MERGE
# =========================

def merge_daily_csvs():
    seen, rows = set(), []

    if not os.path.isdir(RAW_DIR):
        return

    for file in sorted(os.listdir(RAW_DIR)):
        if not file.endswith(".csv"):
            continue

        with open(os.path.join(RAW_DIR, file), newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                page_url = r.get("page_url", "")
                playlist_url = r.get("playlist_url", "")
                if not page_url or not playlist_url:
                    continue
                key = (page_url, playlist_url)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(r)

    os.makedirs(os.path.dirname(MASTER_CSV), exist_ok=True)

    with open(MASTER_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["page_url", "video_code", "playlist_url", "quality", "source"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"[✓] Master CSV updated: {MASTER_CSV} ({len(rows)} rows)")

# =========================
# MAIN
# =========================

async def main():
    async with Fetcher() as fetcher:
        post_urls = await collect_all_posts(fetcher)

        sem = asyncio.Semaphore(POST_CONCURRENCY)
        tasks = [process_post(u, fetcher, sem) for u in post_urls]
        results = await asyncio.gather(*tasks)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    os.makedirs(RAW_DIR, exist_ok=True)

    csv_path = f"{RAW_DIR}/Missav_links_{today}.csv"
    json_path = f"{RAW_DIR}/Missav_links_{today}.json"

    seen, rows = set(), []

    for item in results:
        if not item:
            continue

        page_url, playlists = item
        code = extract_video_code(page_url)

        for pl in playlists:
            key = (page_url, pl)
            if key in seen:
                continue
            seen.add(key)

            rows.append({
                "page_url": page_url,
                "video_code": code,
                "playlist_url": pl,
                "quality": infer_quality(pl),
                "source": infer_source(pl),
            })

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["page_url", "video_code", "playlist_url", "quality", "source"]
        )
        writer.writeheader()
        writer.writerows(rows)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"[✓] Daily files written: {csv_path}, {json_path}")

    merge_daily_csvs()

if __name__ == "__main__":
    asyncio.run(main())
