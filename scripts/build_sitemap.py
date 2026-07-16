#!/usr/bin/env python3
import os
import csv
import json
import re
from datetime import datetime
from html import escape
from urllib.parse import urlsplit

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

    items = []
    for r in rows:
        if r['page_url'].lower().startswith(('javascript:', 'data:')):
            continue
        d = r["date_added"] or "—"
        host = r["host"] or "link"
        items.append(
            f"<li>"
            f"  <span class='date'>{escape(d)}</span>"
            f"  <a class='url' href='{escape(r['page_url'])}' target='_blank' rel='noopener noreferrer'>{escape(r['page_url'])}</a>"
            f"  <span class='host'>{escape(host)}</span>"
            f"</li>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sitemap · JAV.guru</title>
<style>
:root {{
  --bg:#0b0f17; --card:#111827; --line:rgba(255,255,255,.10);
  --text:#e5eefc; --muted:#93a4b8; --accent:#60a5fa;
}}
[data-theme="light"] {{
  --bg:#f8fafc;
  --card:#ffffff;
  --line:rgba(0,0,0,0.1);
  --text:#0f172a;
  --muted:#64748b;
  --accent:#3b82f6;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  background:
    radial-gradient(1200px 700px at 20% 0%, rgba(96,165,250,0.14), transparent 60%),
    radial-gradient(900px 600px at 80% 10%, rgba(34,197,94,0.10), transparent 55%),
    var(--bg);
  color:var(--text);
  font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;
}}
.wrap {{ max-width:1200px; margin:auto; padding:24px; }}

nav {{
  display:flex; gap:10px; flex-wrap:wrap;
  align-items:center; margin-bottom:14px;
}}
nav a {{
  color:var(--muted);
  text-decoration:none;
  border:1px solid var(--line);
  padding:8px 10px;
  border-radius:999px;
  background:rgba(255,255,255,.03);
  font-size:12px;
}}
nav a:hover {{ color:var(--accent); border-color:rgba(96,165,250,.5); }}

header {{
  display:flex; justify-content:space-between; align-items:flex-end;
  gap:12px; flex-wrap:wrap;
}}
h1 {{ margin:0; font-size:20px; }}
.meta {{ color:var(--muted); font-size:12px; }}

.card {{
  margin-top:14px;
  background:rgba(17,24,39,.85);
  border:1px solid var(--line);
  border-radius:16px;
  padding:14px;
  box-shadow:0 10px 25px rgba(0,0,0,.35);
}}

.controls {{
  display:flex;
  gap:12px;
  align-items:center;
  flex-wrap:wrap;
  margin: 10px 0 14px;
}}
.controls input {{
  width:min(560px, 100%);
  padding:10px 12px;
  border-radius:12px;
  border:1px solid var(--line);
  background:rgba(255,255,255,.03);
  color:var(--text);
  outline:none;
  font-size:13px;
}}
.controls .chip {{
  font-size:12px;
  color:var(--muted);
  border:1px solid var(--line);
  padding:8px 10px;
  border-radius:999px;
  background:rgba(255,255,255,.03);
  white-space:nowrap;
}}

ul {{
  margin:0;
  padding:0;
  list-style:none;
}}

li {{
  display:grid;
  grid-template-columns: 110px 1fr 180px;
  gap:12px;
  align-items:center;
  padding:10px 8px;
  border-bottom:1px solid rgba(255,255,255,.06);
}}
li:last-child {{ border-bottom:none; }}

.date {{
  color:var(--muted);
  font-size:12px;
  border:1px solid var(--line);
  padding:5px 8px;
  border-radius:999px;
  width:fit-content;
  background:rgba(255,255,255,.03);
}}

.url {{
  color:var(--text);
  text-decoration:none;
  word-break:break-all;
  font-size:13px;
}}
.url:hover {{
  color:var(--accent);
  text-decoration:underline;
}}

.host {{
  color:var(--muted);
  font-size:12px;
  text-align:right;
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
}}

@media (max-width: 900px) {{
  li {{ grid-template-columns: 110px 1fr; }}
  .host {{ display:none; }}
}}
</style>
</head>
<body>
<div class="wrap" role="main">

<nav>
  <a href="index.html">⬅ Index</a>
  <a href="home.html">🏠 JAV.guru</a>
  <a href="missav.html">🎬 MissAV</a>
  <a href="onejav.html">🧲 OneJAV</a>
  <a href="javct.html">🌟 JavCT</a>
  <a href="codes.html">🏷️ Codes</a>
</nav>

<header>
  <h1>🗺️ Sitemap</h1>
  <div class="meta">{len(rows)} links from all sources · Generated {escape(generated)}</div>
</header>

<div class="card">
  <div class="controls">
    <input id="q" type="text" placeholder="Filter links..." autocomplete="off" aria-label="Search links">
    <div class="chip" id="count">{len(rows)} items</div>
    <div style="flex:1"></div>
    <a href="sitemap_export.csv" download class="chip" style="color:var(--accent);border-color:var(--accent);text-decoration:none;">Download CSV</a>
    <a href="sitemap.json" download class="chip" style="color:var(--accent);border-color:var(--accent);text-decoration:none;">Download JSON</a>
  </div>

  <ul id="list">
    {''.join(items)}
  </ul>
</div>

</div>

<script>
const q = document.getElementById('q');
const list = document.getElementById('list');
const count = document.getElementById('count');
const rows = Array.from(list.querySelectorAll('li'));

q.addEventListener('input', () => {{
  const term = (q.value || '').trim().toLowerCase();
  let shown = 0;
  rows.forEach(li => {{
    const t = li.textContent.toLowerCase();
    const ok = !term || t.includes(term);
    li.style.display = ok ? '' : 'none';
    if (ok) shown++;
  }});
  count.textContent = `${{shown}} items`;
}});
</script>

<script>
  (function(){{
    const toggle = document.createElement('button');
    toggle.innerHTML = '🌓';
    toggle.title = 'Toggle Theme';
    toggle.setAttribute('aria-label', 'Toggle theme');
    toggle.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;background:var(--card, #fff);border:1px solid var(--border, #ccc);color:var(--text, #000);padding:10px;border-radius:50%;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,0.2);display:flex;align-items:center;justify-content:center;font-size:22px;';
    toggle.onclick = () => {{
      const isLight = document.body.getAttribute('data-theme') === 'light';
      document.body.setAttribute('data-theme', isLight ? 'dark' : 'light');
      localStorage.setItem('theme', isLight ? 'dark' : 'light');
    }};
    document.body.appendChild(toggle);
    if(localStorage.getItem('theme') === 'light') document.body.setAttribute('data-theme', 'light');
  }})();
</script>
</body>

</html>
"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Sitemap built: {OUTPUT_FILE}")
    print(f"   Links: {len(rows)}")

if __name__ == "__main__":
    build_sitemap()
