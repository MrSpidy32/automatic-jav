import csv
import json
from collections import defaultdict
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_CSV = BASE_DIR / "results/processed/missav.csv"
CODES_TXT = BASE_DIR / "docs/codes.txt"
OUTPUT_JSON = BASE_DIR / "docs/missav.json"
OUTPUT_HTML = BASE_DIR / "docs/missav.html"


def load_guru_codes() -> set[str]:
    """Load JAV.guru codes (lowercased) from codes.txt."""
    if not CODES_TXT.exists():
        return set()
    return {
        line.strip().lower()
        for line in CODES_TXT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }




def generate():

    if not INPUT_CSV.exists():
        print(f"[✗] CSV not found: {INPUT_CSV}")
        return

    guru_codes = load_guru_codes()
    print(f"[i] Loaded {len(guru_codes)} codes from codes.txt")

    grouped = defaultdict(lambda: {"code": "", "entries": []})
    seen_entries: dict[str, set[tuple[str, str]]] = defaultdict(set)

    with INPUT_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        required = {"page_url", "video_code", "playlist_url", "quality", "source"}
        if not required.issubset(reader.fieldnames or []):
            print("[✗] CSV headers mismatch.")
            print("Found:", reader.fieldnames)
            return

        for r in reader:
            page_url = (r.get("page_url") or "").strip()
            code = (r.get("video_code") or "").strip()
            playlist = (r.get("playlist_url") or "").strip()
            quality = (r.get("quality") or "").strip()
            source = (r.get("source") or "").strip()

            if not page_url or not playlist:
                continue

            grouped[page_url]["code"] = code

            entry = {
                "quality": quality,
                "source": source,
                "url": playlist
            }

            entry_id = (entry["url"], entry["quality"])
            if entry_id not in seen_entries[page_url]:
                seen_entries[page_url].add(entry_id)
                grouped[page_url]["entries"].append(entry)

    guru_count = 0
    cat_count = 0
    data = []
    for v in grouped.values():
        code = v["code"]
        tag = "jav.guru" if code.lower() in guru_codes else "category"
        if tag == "jav.guru":
            guru_count += 1
        else:
            cat_count += 1
        data.append({
            "code": code,
            "tag": tag,
            "entries": v["entries"],
        })

    print(f"[i] Tagged: {guru_count} JAV.guru, {cat_count} Category")

    # Ensure output folders exist (IMPORTANT for CI)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)

    # Write structured JSON
    OUTPUT_JSON.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    # Write HTML via template
    env = Environment(loader=FileSystemLoader(BASE_DIR / "templates"))
    template = env.get_template("missav.html")
    html = template.render(current_page="missav")
    OUTPUT_HTML.write_text(html, encoding="utf-8")

    print(f"[✓] Missav Page build generated.")
    print(f"Videos: {len(data)}")
    print(f"JSON: {OUTPUT_JSON}")
    print(f"HTML: {OUTPUT_HTML}")


if __name__ == "__main__":
    generate()
