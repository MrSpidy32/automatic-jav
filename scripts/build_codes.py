#!/usr/bin/env python3
import os
import csv
import json
import re
from datetime import datetime
from html import escape

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

    items = "\n".join(
        f"<div class='code' onclick=\"copy('{escape(code)}')\">{escape(code)}</div>"
        for code in codes
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Code Index</title>
<style>
:root {{
  --bg:#0b0f17;
  --card:#111827;
  --line:rgba(255,255,255,.1);
  --text:#e5eefc;
  --muted:#93a4b8;
  --accent:#60a5fa;
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
  background:var(--bg);
  color:var(--text);
  font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;
}}
.wrap {{
  max-width:1000px;
  margin:auto;
  padding:24px;
}}
header {{
  display:flex;
  justify-content:space-between;
  align-items:flex-end;
  gap:12px;
  flex-wrap:wrap;
}}
h1 {{
  margin:0;
  font-size:22px;
}}
.meta {{
  font-size:12px;
  color:var(--muted);
}}
.controls {{
  margin-top:14px;
}}
.controls input {{
  width:100%;
  max-width:420px;
  padding:10px 12px;
  border-radius:12px;
  border:1px solid var(--line);
  background:rgba(255,255,255,.03);
  color:var(--text);
  outline:none;
}}
.controls input::placeholder {{
  color:rgba(147,164,184,.7);
}}
.grid {{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(140px,1fr));
  gap:12px;
  margin-top:20px;
}}
.code {{
  background:var(--card);
  border:1px solid var(--line);
  border-radius:12px;
  padding:14px 10px;
  text-align:center;
  font-weight:600;
  letter-spacing:.4px;
  font-size:14px;
  cursor:pointer;
  user-select:none;
  transition:border-color .15s,color .15s,transform .15s;
}}
.code:hover {{
  border-color:var(--accent);
  color:var(--accent);
  transform:translateY(-2px);
}}
footer {{
  margin-top:26px;
  font-size:12px;
  color:var(--muted);
  text-align:center;
}}
</style>
</head>
<body>
<div class="wrap" role="main">

<header>
  <h1>📚 Code Index</h1>
  <div class="meta">{total} codes from all sources · Generated {escape(generated)}</div>
</header>

<div class="controls">
  <input id="search" type="text" placeholder="Search code..." aria-label="Search codes" />
</div>

<div class="grid" id="grid">
{items}
</div>

<footer>Source: JAV.guru, MissAV, OneJAV, JavCT · Click a code to copy</footer>

</div>

<script>
const allCodes = [...document.querySelectorAll('.code')];

document.getElementById('search').addEventListener('input', e => {{
  const q = e.target.value.toLowerCase();
  allCodes.forEach(el => {{
    el.style.display = el.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}});

function copy(text) {{
  navigator.clipboard.writeText(text);
}}
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
