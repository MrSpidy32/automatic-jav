import csv
import json
from pathlib import Path

# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_CSV = BASE_DIR / "results/processed/onejav.csv"
CODES_TXT = BASE_DIR / "docs/codes.txt"
OUTPUT_JSON = BASE_DIR / "docs/onejav.json"
OUTPUT_HTML = BASE_DIR / "docs/onejav.html"


def load_guru_codes() -> set[str]:
    """Load JAV.guru codes (lowercased) from codes.txt."""
    if not CODES_TXT.exists():
        return set()
    return {
        line.strip().lower()
        for line in CODES_TXT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>OneJAV · JAV.guru Data Hub</title>
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
  --card-hover:#1f2a42;
  --border:#2a3450;
  --accent:#8b5cf6;
  --accent-hover:#7c3aed;
  --green:#22c55e;
  --blue:#3b82f6;
  --orange:#f59e0b;
  --red:#ef4444;
  --cyan:#06b6d4;
  --text:#f1f5f9;
  --text-dim:#94a3b8;
  --pill:#1e293b;
  --pill-hover:#334155;
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

.header h1 span { color: var(--cyan); }

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

.search-box input:focus { border-color: var(--cyan); }

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

.stats b { color: var(--cyan); }

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

@media(min-width:640px)  { #container { grid-template-columns: repeat(3, 1fr); } }
@media(min-width:1024px) { #container { grid-template-columns: repeat(4, 1fr); } }
@media(min-width:1400px) { #container { grid-template-columns: repeat(5, 1fr); } }

/* ---- CARD ---- */
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  transition: transform 0.15s, border-color 0.15s;
  display: flex;
  flex-direction: column;
}

.card:hover {
  transform: translateY(-2px);
  border-color: var(--cyan);
}

.card-thumb {
  position: relative;
  aspect-ratio: 16/10;
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

.size-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0,0,0,0.75);
  color: var(--orange);
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
  backdrop-filter: blur(4px);
}

.date-badge {
  position: absolute;
  bottom: 8px;
  left: 8px;
  background: rgba(0,0,0,0.75);
  color: var(--text-dim);
  font-size: 10px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 6px;
  backdrop-filter: blur(4px);
}

.card-body {
  padding: 10px 12px 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-code {
  font-weight: 700;
  font-size: 14px;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title {
  font-size: 12px;
  color: var(--text-dim);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tag {
  font-size: 9px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  flex-shrink: 0;
}

.tag-guru {
  background: rgba(96,165,250,0.15);
  color: #60a5fa;
  border: 1px solid rgba(96,165,250,0.3);
}

.tag-cat {
  background: rgba(168,85,247,0.15);
  color: #a855f7;
  border: 1px solid rgba(168,85,247,0.3);
}

/* ---- ACTRESSES ---- */
.actresses {
  font-size: 11px;
  color: var(--accent);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---- TAGS ---- */
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tag-pill {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 500;
  background: var(--pill);
  color: var(--text-dim);
  white-space: nowrap;
}

/* ---- TORRENT BUTTON ---- */
.torrent-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: auto;
  padding: 7px 14px;
  background: linear-gradient(135deg, var(--green), #16a34a);
  color: white;
  font-size: 12px;
  font-weight: 700;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  text-decoration: none;
  transition: transform 0.1s, filter 0.1s;
  text-align: center;
  justify-content: center;
}

.torrent-btn:hover { transform: scale(1.03); filter: brightness(1.15); }
.torrent-btn:active { transform: scale(0.97); }

.torrent-btn svg {
  width: 14px;
  height: 14px;
  fill: currentColor;
}

/* ---- LOADING ---- */
.loading {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-dim);
  font-size: 15px;
}

.loading::before {
  content: '';
  display: block;
  width: 36px;
  height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--cyan);
  border-radius: 50%;
  margin: 0 auto 16px;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

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
    <h1><span>OneJAV</span> · JAV.guru</h1>
    <div class="search-box">
      <input id="filter" placeholder="Search by code, actress, tag..." autocomplete="off" aria-label="Search videos">
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

fetch("onejav.json")
  .then(r => r.json())
  .then(data => {
    DATA = data;
    document.getElementById("loading").style.display = "none";
    updateStats(data.length);
    initVirtual();
  })
  .catch(() => {
    document.getElementById("loading").textContent = "Failed to load data.";
  });

function updateStats(shown) {
  document.getElementById("stats").innerHTML =
    `<b>${shown.toLocaleString()}</b> / ${DATA.length.toLocaleString()} torrents`;
}

/* ---- VIRTUAL SCROLL ---- */

function initVirtual() {
  const container = document.getElementById("container");
  const rowHeight = 420;
  const buffer = 4;
  let lastQ = "";
  let filtered = DATA;

  function refilter() {
    const q = document.getElementById("filter").value.toLowerCase().trim();
    if (q !== lastQ) {
      lastQ = q;
      filtered = q ? DATA.filter(v => {
        return v.code.toLowerCase().includes(q)
          || (v.actresses || "").toLowerCase().includes(q)
          || (v.tags || "").toLowerCase().includes(q)
          || (v.title || "").toLowerCase().includes(q)
          || (v.source_tag || "").includes(q);
      }) : DATA;
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
    if (w >= 1400) return 5;
    if (w >= 1024) return 4;
    if (w >= 640)  return 3;
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

/* ---- BUILD CARD ---- */

const DOWNLOAD_SVG = '<svg viewBox="0 0 24 24"><path d="M12 16l-5-5h3V4h4v7h3l-5 5zm-7 4h14v-2H5v2z"/></svg>';

function buildCard(v) {
  const card = document.createElement("div");
  card.className = "card";

  // Thumbnail
  const thumbDiv = document.createElement("div");
  thumbDiv.className = "card-thumb";

  if (v.image_url) {
    const img = document.createElement("img");
    img.loading = "lazy";
    img.alt = v.code;
    img.src = v.image_url;
    img.onerror = function() {
      this.style.display = "none";
    };
    thumbDiv.appendChild(img);
  }

  // Size badge
  if (v.size) {
    const sizeBadge = document.createElement("span");
    sizeBadge.className = "size-badge";
    sizeBadge.textContent = v.size;
    thumbDiv.appendChild(sizeBadge);
  }

  // Date badge
  if (v.date) {
    const dateBadge = document.createElement("span");
    dateBadge.className = "date-badge";
    dateBadge.textContent = v.date;
    thumbDiv.appendChild(dateBadge);
  }

  // Body
  const body = document.createElement("div");
  body.className = "card-body";

  // Code + source tag
  const codeDiv = document.createElement("div");
  codeDiv.className = "card-code";
  codeDiv.textContent = v.code.toUpperCase();

  if (v.source_tag) {
    const tag = document.createElement("span");
    tag.className = v.source_tag === "jav.guru" ? "tag tag-guru" : "tag tag-cat";
    tag.textContent = v.source_tag === "jav.guru" ? "JAV.guru" : "New";
    codeDiv.appendChild(tag);
  }

  body.appendChild(codeDiv);

  // Title
  if (v.title) {
    const titleDiv = document.createElement("div");
    titleDiv.className = "card-title";
    titleDiv.textContent = v.title;
    titleDiv.title = v.title;
    body.appendChild(titleDiv);
  }

  // Actresses
  if (v.actresses) {
    const actDiv = document.createElement("div");
    actDiv.className = "actresses";
    actDiv.textContent = v.actresses;
    body.appendChild(actDiv);
  }

  // Tags
  if (v.tags) {
    const tagsDiv = document.createElement("div");
    tagsDiv.className = "tags";
    const tagList = v.tags.split(", ").slice(0, 5);
    for (const t of tagList) {
      const pill = document.createElement("span");
      pill.className = "tag-pill";
      pill.textContent = t;
      tagsDiv.appendChild(pill);
    }
    if (v.tags.split(", ").length > 5) {
      const more = document.createElement("span");
      more.className = "tag-pill";
      more.textContent = "+" + (v.tags.split(", ").length - 5);
      tagsDiv.appendChild(more);
    }
    body.appendChild(tagsDiv);
  }

  // Torrent download button
  if (v.torrent_url) {
    const btn = document.createElement("a");
    btn.className = "torrent-btn";
    btn.href = v.torrent_url;
    btn.target = "_blank";
    btn.rel = "noopener";
    btn.innerHTML = DOWNLOAD_SVG + " Download .torrent";
    body.appendChild(btn);
  }

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

    if not INPUT_CSV.exists():
        print(f"[x] CSV not found: {INPUT_CSV}")
        return

    guru_codes = load_guru_codes()
    print(f"[i] Loaded {len(guru_codes)} codes from codes.txt")

    data = []
    seen_codes = set()

    with INPUT_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        required = {"code", "title", "size", "image_url", "torrent_url", "tags", "actresses", "date", "page_url"}
        if not required.issubset(reader.fieldnames or []):
            print("[x] CSV headers mismatch.")
            print("Found:", reader.fieldnames)
            return

        for r in reader:
            code = (r.get("code") or "").strip()
            if not code:
                continue

            code_lower = code.lower()
            if code_lower in seen_codes:
                continue
            seen_codes.add(code_lower)

            source_tag = "jav.guru" if code_lower in guru_codes else "new"

            data.append({
                "code": code,
                "title": (r.get("title") or "").strip(),
                "size": (r.get("size") or "").strip(),
                "image_url": (r.get("image_url") or "").strip(),
                "torrent_url": (r.get("torrent_url") or "").strip(),
                "tags": (r.get("tags") or "").strip(),
                "actresses": (r.get("actresses") or "").strip(),
                "date": (r.get("date") or "").strip(),
                "page_url": (r.get("page_url") or "").strip(),
                "source_tag": source_tag,
            })

    guru_count = sum(1 for d in data if d["source_tag"] == "jav.guru")
    new_count = len(data) - guru_count

    print(f"[i] Tagged: {guru_count} JAV.guru, {new_count} New")

    # Ensure output folders exist
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)

    # Write structured JSON
    OUTPUT_JSON.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    # Write HTML
    OUTPUT_HTML.write_text(HTML, encoding="utf-8")

    print(f"[ok] OneJAV page build generated.")
    print(f"Torrents: {len(data)}")
    print(f"JSON: {OUTPUT_JSON}")
    print(f"HTML: {OUTPUT_HTML}")


if __name__ == "__main__":
    generate()
