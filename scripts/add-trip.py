#!/usr/bin/env python3
"""Import a folder of photos as a trip.

Copies the images into photos/<slug>/ (resized so the long edge is at most
MAX_EDGE pixels), writes thumbnails into photos/<slug>/thumbs/, and adds or
updates the trip entry in trips.json.

Resizing uses `sips` on macOS and falls back to Pillow elsewhere.

Example:
    python3 scripts/add-trip.py ~/Pictures/Lisbon --title "Lisbon" --place "Portugal" --date 2025-05
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHOTOS_DIR = ROOT / "photos"
MANIFEST = ROOT / "trips.json"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
MAX_EDGE = 2000
THUMB_EDGE = 600


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "trip"


def have_sips() -> bool:
    return shutil.which("sips") is not None


def resize(src: Path, dst: Path, max_edge: int) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if have_sips():
        # sips -Z keeps aspect ratio and only shrinks if larger. HEIC is converted to JPEG.
        cmd = ["sips", "-Z", str(max_edge), str(src), "--out", str(dst)]
        if src.suffix.lower() == ".heic":
            cmd += ["-s", "format", "jpeg"]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    try:
        from PIL import Image, ImageOps
    except ImportError:
        sys.exit("Need either `sips` (macOS) or Pillow (`pip install pillow`) to resize images.")
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail((max_edge, max_edge))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        im.save(dst, quality=88, optimize=True)


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {"trips": []}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path, help="folder containing the photos")
    ap.add_argument("--title", required=True)
    ap.add_argument("--place", required=True, help="country or region, shown under the title")
    ap.add_argument("--date", required=True, help="YYYY-MM or YYYY-MM-DD, used for sorting")
    ap.add_argument("--slug", help="URL slug (default: derived from title)")
    ap.add_argument("--description", default="")
    ap.add_argument("--cover", help="file name (after import) to use as the cover; default is the first photo")
    args = ap.parse_args()

    if not args.folder.is_dir():
        sys.exit(f"{args.folder} is not a directory")

    slug = args.slug or slugify(args.title)
    dest = PHOTOS_DIR / slug
    thumbs = dest / "thumbs"

    sources = sorted(p for p in args.folder.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not sources:
        sys.exit(f"No images found in {args.folder}")

    photos = []
    for i, src in enumerate(sources, 1):
        out_name = src.stem + (".jpg" if src.suffix.lower() == ".heic" else src.suffix.lower())
        print(f"[{i}/{len(sources)}] {src.name} -> photos/{slug}/{out_name}")
        resize(src, dest / out_name, MAX_EDGE)
        resize(dest / out_name, thumbs / out_name, THUMB_EDGE)
        photos.append({"file": out_name, "caption": ""})

    manifest = load_manifest()
    manifest["trips"] = [t for t in manifest["trips"] if t.get("slug") != slug]
    manifest["trips"].append(
        {
            "slug": slug,
            "title": args.title,
            "place": args.place,
            "date": args.date,
            "description": args.description,
            "cover": args.cover or photos[0]["file"],
            "photos": photos,
        }
    )
    manifest["trips"].sort(key=lambda t: str(t.get("date", "")), reverse=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"\nAdded trip '{args.title}' with {len(photos)} photos. Edit trips.json to add captions, then commit and push.")


if __name__ == "__main__":
    main()
