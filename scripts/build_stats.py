#!/usr/bin/env python3
import os
import csv
import json
import re
from collections import defaultdict
from datetime import datetime

RESULTS_DIR = "results/processed"
DOCS_DIR = "docs"

def load_data():
    stats = {
        "sources": {
            "JAV.guru": 0,
            "MissAV": 0,
            "OneJAV": 0,
            "JavCT": 0,
            "Models": 0
        },
        "timeline": defaultdict(int),
        "total_codes": 0
    }

    # 1. JAV.guru
    comb_path = os.path.join(RESULTS_DIR, "combined.csv")
    if os.path.exists(comb_path):
        with open(comb_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return stats
            has_date = "date_added" in reader.fieldnames
            has_src = "source_file" in reader.fieldnames
            count = 0
            for r in reader:
                count += 1
                d = r.get("date_added", "") if has_date else ""
                if not d and has_src:
                    m = re.search(r"(\d{4}-\d{2}-\d{2})", r.get("source_file", ""))
                    d = m.group(1) if m else ""
                if d:
                    stats["timeline"][d] += 1
            stats["sources"]["JAV.guru"] = count

    # 2. MissAV
    missav_path = os.path.join(RESULTS_DIR, "missav.csv")
    if os.path.exists(missav_path):
        with open(missav_path, newline="", encoding="utf-8") as f:
            stats["sources"]["MissAV"] = sum(1 for _ in csv.DictReader(f))

    # 3. OneJAV
    onejav_path = os.path.join(RESULTS_DIR, "onejav.csv")
    if os.path.exists(onejav_path):
        with open(onejav_path, newline="", encoding="utf-8") as f:
            stats["sources"]["OneJAV"] = sum(1 for _ in csv.DictReader(f))

    # 4. JavCT
    javct_path = os.path.join(RESULTS_DIR, "javct.csv")
    if os.path.exists(javct_path):
        with open(javct_path, newline="", encoding="utf-8") as f:
            stats["sources"]["JavCT"] = sum(1 for _ in csv.DictReader(f))

    # 5. Models
    models_path = os.path.join(RESULTS_DIR, "javct_models.csv")
    if os.path.exists(models_path):
        with open(models_path, newline="", encoding="utf-8") as f:
            stats["sources"]["Models"] = sum(1 for _ in csv.DictReader(f))

    # Get total unique codes
    codes_path = os.path.join(DOCS_DIR, "codes.txt")
    if os.path.exists(codes_path):
        with open(codes_path, encoding="utf-8") as f:
            stats["total_codes"] = len([l for l in f.read().splitlines() if l.strip()])

    return stats

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stats Dashboard · JAV.guru</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root {
  --bg: #0b0f17; --card: #111827; --line: rgba(255,255,255,.10);
  --text: #e5eefc; --muted: #93a4b8; --accent: #3b82f6;
}
[data-theme="light"] {
  --bg: #f8fafc; --card: #ffffff; --line: rgba(0,0,0,.1);
  --text: #0f172a; --muted: #64748b;
  --green: #16a34a;
  --blue: #2563eb;
  --orange: #d97706;
  --red: #dc2626;
  --cyan: #0891b2;
  --pill: #e2e8f0;
  --pill-hover: #cbd5e1;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg); color: var(--text);
  font-family: system-ui, -apple-system, sans-serif;
  padding: 24px;
}
.wrap { max-width: 1000px; margin: auto; }
nav { margin-bottom: 20px; display: flex; gap: 10px; }
nav a {
  color: var(--muted); text-decoration: none; border: 1px solid var(--line);
  padding: 8px 12px; border-radius: 999px; font-size: 13px;
}
nav a:hover { color: var(--accent); border-color: var(--accent); }
h1 { margin-bottom: 24px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
.stat-card {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 16px; padding: 20px; text-align: center;
}
.stat-val { font-size: 32px; font-weight: bold; color: var(--accent); margin-bottom: 4px; }
.stat-lbl { font-size: 14px; color: var(--muted); }
.chart-container {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 16px; padding: 20px; margin-bottom: 24px;
}
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
    <a href="models.html">Models</a>
    <a href="codes.html">🏷️ Codes</a>
    <a href="sitemap.html">🗺️ Sitemap</a>
  </nav>

  <h1>📊 Stats Dashboard</h1>

  <div class="grid" id="kpi"></div>

  <div class="chart-container">
    <canvas id="timelineChart"></canvas>
  </div>
  
  <div class="chart-container" style="max-width: 500px; margin: auto;">
    <canvas id="sourceChart"></canvas>
  </div>
</div>

<script>
function escHtml(s) {
  return String(s)
    .replaceAll('&','&amp;')
    .replaceAll('<','&lt;')
    .replaceAll('>','&gt;')
    .replaceAll('"','&quot;')
    .replaceAll("'",'&#39;');
}

fetch("stats.json")
  .then(r => r.json())
  .then(data => {
    // Render KPIs
    const kpi = document.getElementById('kpi');
    for (const [src, val] of Object.entries(data.sources)) {
      kpi.innerHTML += `<div class="stat-card">
        <div class="stat-val">${escHtml(val.toLocaleString())}</div>
        <div class="stat-lbl">${escHtml(src)} Videos</div>
      </div>`;
    }

    // Timeline Chart
    const dates = Object.keys(data.timeline).sort();
    const counts = dates.map(d => data.timeline[d]);
    new Chart(document.getElementById('timelineChart'), {
      type: 'line',
      data: {
        labels: dates,
        datasets: [{
          label: 'JAV.guru Videos Added',
          data: counts,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        plugins: { title: { display: true, text: 'Growth Over Time' } },
        scales: {
          x: { ticks: { color: '#93a4b8' } },
          y: { ticks: { color: '#93a4b8' } }
        }
      }
    });

    // Source Doughnut
    new Chart(document.getElementById('sourceChart'), {
      type: 'doughnut',
      data: {
        labels: Object.keys(data.sources),
        datasets: [{
          data: Object.values(data.sources),
          backgroundColor: ['#3b82f6', '#8b5cf6', '#06b6d4', '#10b981', '#ec4899']
        }]
      },
      options: {
        responsive: true,
        plugins: { title: { display: true, text: 'Source Breakdown' } }
      }
    });
  });
</script>
</body>
</html>
"""

def build():
    os.makedirs(DOCS_DIR, exist_ok=True)
    stats = load_data()
    
    with open(os.path.join(DOCS_DIR, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
        
    with open(os.path.join(DOCS_DIR, "stats.html"), "w", encoding="utf-8") as f:
        f.write(HTML)
        
    print("✅ Stats Dashboard generated")

if __name__ == "__main__":
    build()
