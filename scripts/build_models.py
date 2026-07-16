import csv
import json
from pathlib import Path
from urllib.parse import quote

# =========================
# CONFIGURATION
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
JAVCT_MODELS_CSV = BASE_DIR / "results/processed/javct_models.csv"
ONEJAV_CSV = BASE_DIR / "results/processed/onejav.csv"

OUTPUT_JSON = BASE_DIR / "docs/models.json"
OUTPUT_HTML = BASE_DIR / "docs/models.html"


HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Models · JAV.guru Data Hub</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>

[data-theme="light"] {
  --bg:#f8fafc;
  --surface:#ffffff;
  --card:#ffffff;
  --card-hover:#f1f5f9;
  --border:#e2e8f0;
  --text:#0f172a;
  --text-dim:#64748b;
  --line:rgba(0,0,0,0.1);
  --pill:#e2e8f0;
  --pill-hover:#cbd5e1;
  --green: #16a34a;
  --blue: #2563eb;
  --orange: #d97706;
  --red: #dc2626;
  --cyan: #0891b2;
}
* { box-sizing: border-box; }

* { margin:0; padding:0; }

:root {
  --bg:#0a0e1a;
  --surface:#111827;
  --card:#1a2236;
  --border:#2a3450;
  --accent:#ec4899;
  --text:#f1f5f9;
  --text-dim:#94a3b8;
  --radius:12px;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
}

/* ---- HEADER ---- */
.header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 16px 20px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-inner {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.header h1 {
  font-size: 20px;
  font-weight: 700;
  white-space: nowrap;
}

.header h1 span { color: var(--accent); }

.search-box {
  flex: 1;
  min-width: 200px;
  position: relative;
}

.search-box input {
  width: 100%;
  padding: 10px 14px 10px 38px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.search-box input:focus { border-color: var(--accent); }

.search-box::before {
  content: '\\1F50D';
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 14px;
  pointer-events: none;
}

.stats {
  font-size: 13px;
  color: var(--text-dim);
  white-space: nowrap;
}

.stats b { color: var(--accent); }

/* ---- MAIN ---- */
.main {
  max-width: 1600px;
  margin: 0 auto;
  padding: 16px 20px;
}

/* ---- GRID ---- */
#container {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

@media(min-width:480px)  { #container { grid-template-columns: repeat(3, 1fr); } }
@media(min-width:768px)  { #container { grid-template-columns: repeat(4, 1fr); } }
@media(min-width:1024px) { #container { grid-template-columns: repeat(5, 1fr); } }
@media(min-width:1400px) { #container { grid-template-columns: repeat(6, 1fr); } }

/* ---- CARD ---- */
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  transition: transform 0.15s, border-color 0.15s;
  display: flex;
  flex-direction: column;
  text-decoration: none;
  color: inherit;
}

.card:hover {
  transform: translateY(-2px);
  border-color: var(--accent);
}

.card-thumb {
  position: relative;
  aspect-ratio: 1/1;
  overflow: hidden;
  background: #0d1117;
}

.card-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: opacity 0.2s;
}

.card-thumb:hover img { opacity: 0.85; }

.card-body {
  padding: 12px;
  text-align: center;
}

.card-title {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-source {
  font-size: 11px;
  color: var(--text-dim);
}

.card-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0,0,0,0.75);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
  backdrop-filter: blur(4px);
}

/* ---- LOADING ---- */
.loading {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-dim);
  font-size: 15px;
}

.loading::before {
  content: "";
  display: block;
  width: 36px;
  height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  margin: 0 auto 16px;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { 100% { transform: rotate(360deg); } }

nav {
  display: flex; gap: 12px; flex-wrap: wrap;
  align-items: center; margin-bottom: 24px;
}
nav a {
  color: var(--text-dim);
  text-decoration: none;
  border: 1px solid var(--border);
  padding: 8px 16px;
  border-radius: 999px;
  background: var(--card);
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
}
nav a:hover {
  color: var(--accent);
  border-color: var(--accent);
}
</style>
</head>

<body>

<div class="header">
  <div class="header-inner">
    <h1><span>Models</span> · Gallery</h1>
    <div class="search-box">
      <input id="filter" placeholder="Search models..." autocomplete="off" aria-label="Search models">
    </div>
    <div class="stats" id="stats"></div>
  </div>
</div>

<div class="main" role="main">
  <nav>
    <a href="index.html">Index</a>
    <a href="home.html">Home</a>
    <a href="codes.html">Codes</a>
    <a href="sitemap.html">Sitemap</a>
    <a href="missav.html">MissAV</a>
    <a href="onejav.html">OneJAV</a>
    <a href="javct.html">JavCT</a>
    <a href="models.html">Models</a>
    <a href="stats.html">Stats</a>
  </nav>
  <div id="loading" class="loading">Loading data...</div>
  <div id="container"></div>
</div>

<script>
let DATA = [];

fetch("models.json")
  .then(r => r.json())
  .then(data => {
    // Sort by source (JAVCT first because they have images), then alphabetically
    DATA = data.sort((a, b) => {
      if (a.source === "JavCT" && b.source !== "JavCT") return -1;
      if (b.source === "JavCT" && a.source !== "JavCT") return 1;
      return a.name.localeCompare(b.name);
    });
    document.getElementById("loading").style.display = "none";
    updateStats(data.length);
    initVirtual();
  })
  .catch(() => {
    document.getElementById("loading").textContent = "Failed to load data.";
  });

function updateStats(shown) {
  document.getElementById("stats").innerHTML =
    `<b>${shown.toLocaleString()}</b> / ${DATA.length.toLocaleString()} models`;
}

function initVirtual() {
  const container = document.getElementById("container");
  const rowHeight = 300;
  const buffer = 4;
  let lastQ = "";
  let filtered = DATA;

  function refilter() {
    const q = document.getElementById("filter").value.toLowerCase().trim();
    if (q !== lastQ) {
      lastQ = q;
      filtered = q ? DATA.filter(v => v.name.toLowerCase().includes(q) || v.source.toLowerCase().includes(q)) : DATA;
      updateStats(filtered.length);
    }
    return filtered;
  }

  function render() {
    const items = refilter();
    const scrollTop = window.scrollY;
    const screenH = window.innerHeight;
    const cols = getCols();
    const totalRows = Math.ceil(items.length / cols);

    const startRow = Math.max(0, Math.floor(scrollTop / rowHeight) - buffer);
    const endRow = Math.min(totalRows, Math.ceil((scrollTop + screenH) / rowHeight) + buffer);

    const si = startRow * cols;
    const ei = Math.min(items.length, endRow * cols);

    container.innerHTML = "";
    if (items.length === 0) {
      const empty = document.createElement("div");
      empty.style.cssText = "grid-column:1/-1;text-align:center;padding:60px 20px;color:var(--text-dim);font-size:15px;";
      const q = document.getElementById("filter").value;
      empty.textContent = q ? "No results found for \"" + q + "\"" : "No results found";
      container.appendChild(empty);
      return;
    }
    for (let i = si; i < ei; i++) {
      container.appendChild(buildCard(items[i]));
    }

    container.style.paddingTop  = startRow * rowHeight + "px";
    container.style.paddingBottom = Math.max(0, totalRows - endRow) * rowHeight + "px";
  }

  function getCols() {
    const w = window.innerWidth;
    if (w >= 1400) return 6;
    if (w >= 1024) return 5;
    if (w >= 768)  return 4;
    if (w >= 480)  return 3;
    return 2;
  }

  let ticking = false;
  function onScroll() {
    if (!ticking) { ticking = true; requestAnimationFrame(() => { render(); ticking = false; }); }
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", render);
  document.getElementById("filter").oninput = render;
  render();
}

function buildCard(m) {
  const card = document.createElement("a");
  card.className = "card";
  card.href = m.page_url || "#";
  if (m.page_url) {
    card.target = "_blank";
    card.rel = "noopener";
  }

  // Thumbnail
  const thumbDiv = document.createElement("div");
  thumbDiv.className = "card-thumb";

  if (m.image_url) {
    const img = document.createElement("img");
    img.loading = "lazy";
    img.alt = m.name;
    img.src = m.image_url;
    img.onerror = function() {
      this.style.display = "none";
    };
    thumbDiv.appendChild(img);
  }

  if (m.views) {
    const badge = document.createElement("span");
    badge.className = "card-badge";
    badge.textContent = m.views + " views";
    thumbDiv.appendChild(badge);
  }

  // Body
  const body = document.createElement("div");
  body.className = "card-body";

  const titleDiv = document.createElement("div");
  titleDiv.className = "card-title";
  titleDiv.textContent = m.name;
  
  const sourceDiv = document.createElement("div");
  sourceDiv.className = "card-source";
  sourceDiv.textContent = m.source;

  body.appendChild(titleDiv);
  body.appendChild(sourceDiv);
  
  card.appendChild(thumbDiv);
  card.appendChild(body);
  return card;
}
</script>

<script>
  (function(){
    const toggle = document.createElement('button');
    toggle.innerHTML = '🌓';
    toggle.title = 'Toggle Theme';
    toggle.setAttribute('aria-label', 'Toggle theme');
    toggle.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;background:var(--card, #fff);border:1px solid var(--border, #ccc);color:var(--text, #000);padding:10px;border-radius:50%;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,0.2);display:flex;align-items:center;justify-content:center;font-size:22px;';
    toggle.onclick = () => {
      const isLight = document.body.getAttribute('data-theme') === 'light';
      document.body.setAttribute('data-theme', isLight ? 'dark' : 'light');
      localStorage.setItem('theme', isLight ? 'dark' : 'light');
    };
    document.body.appendChild(toggle);
    if(localStorage.getItem('theme') === 'light') document.body.setAttribute('data-theme', 'light');
  })();
</script>
</body>

</html>
"""

def generate():
    models = {}
    
    # 1. Load from JavCT
    if JAVCT_MODELS_CSV.exists():
        with JAVCT_MODELS_CSV.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                name = r.get("name", "").strip()
                if not name:
                    continue
                models[name.lower()] = {
                    "name": name,
                    "image_url": r.get("image_url", ""),
                    "page_url": r.get("page_url", ""),
                    "views": r.get("views", ""),
                    "source": "JavCT"
                }

    # 2. Extract from OneJAV
    if ONEJAV_CSV.exists():
        with ONEJAV_CSV.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                actresses_raw = r.get("actresses", "")
                if not actresses_raw:
                    continue
                for name_raw in actresses_raw.split(","):
                    name = name_raw.strip()
                    if not name:
                        continue
                    k = name.lower()
                    if k not in models:
                        # Fallback page URL pointing to a OneJAV search if we want
                        page_url = f"https://onejav.com/actress/{quote(name)}"
                        models[k] = {
                            "name": name,
                            "image_url": "",
                            "page_url": page_url,
                            "views": "",
                            "source": "OneJAV"
                        }
                        
    data = list(models.values())
    
    # Ensure output folders exist
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_JSON.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    OUTPUT_HTML.write_text(HTML, encoding="utf-8")

    print(f"[ok] Models page generated: {len(data)} total models.")

if __name__ == "__main__":
    generate()
