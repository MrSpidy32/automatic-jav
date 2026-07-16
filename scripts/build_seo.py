#!/usr/bin/env python3
import os
from datetime import datetime

DOCS_DIR = "docs"
if "GITHUB_REPOSITORY" in os.environ:
    _, repo = os.environ["GITHUB_REPOSITORY"].split("/")
    BASE_URL = f"https://{owner}.github.io/{repo}"
else:
    BASE_URL = "https://guiltjay.github.io/automatic-jav"

PAGES = [
    "index.html",
    "home.html",
    "missav.html",
    "onejav.html",
    "javct.html",
    "models.html",
    "codes.html",
    "sitemap.html",
    "stats.html"
]

def build_robots_txt():
    content = f"""User-agent: *
Allow: /

Sitemap: {BASE_URL}/sitemap.xml
"""
    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ Generated robots.txt")

def build_sitemap_xml():
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    xml_items = []
    for page in PAGES:
        # Give higher priority to main index and home pages
        priority = "1.0" if page in ["index.html", "home.html"] else "0.8"
        xml_items.append(f"""  <url>
    <loc>{BASE_URL}/{page}</loc>
    <lastmod>{date_str}</lastmod>
    <changefreq>daily</changefreq>
    <priority>{priority}</priority>
  </url>""")

    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(xml_items)}
</urlset>"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(xml_content)
    print("✅ Generated sitemap.xml")

if __name__ == "__main__":
    os.makedirs(DOCS_DIR, exist_ok=True)
    build_robots_txt()
    build_sitemap_xml()
