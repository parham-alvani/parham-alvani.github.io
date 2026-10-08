#!/usr/bin/env python3
"""Build the static site into dist/ from trips.json.

Every trip gets its own page at /trips/<slug>/ with full metadata (Open Graph,
Twitter cards, JSON-LD, canonical URL), plus a sitemap, an Atom feed, robots.txt
and a web manifest, so search engines and link previews can read the site
without running JavaScript.

Usage:
    python3 scripts/build.py            # build into dist/
    python3 scripts/build.py --check    # validate trips.json only
    python3 scripts/build.py --linkcheck  # build, then verify internal links
"""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SITE_URL = "https://we.1995parham.me"
SITE_NAME = "Our Trips"
SITE_TAGLINE = "Elaheh and Parham, around the world"
SITE_DESCRIPTION = "Pictures, posts and reels from Elaheh and Parham's trips around the world."
AUTHORS = "Elaheh Dastan and Parham Alvani"
INSTAGRAM = "https://www.instagram.com/elahe.dstn/"
REPO_URL = "https://github.com/parham-alvani/parham-alvani.github.io"

COUNTRY_NAMES = {
    "AE": "United Arab Emirates", "BE": "Belgium", "CN": "China", "ES": "Spain", "FR": "France",
    "GE": "Georgia", "IR": "Iran", "RU": "Russia", "TR": "Turkey", "NL": "Netherlands",
    "DE": "Germany", "TN": "Tunisia", "IT": "Italy", "PT": "Portugal", "GB": "United Kingdom",
    "US": "United States", "AM": "Armenia", "AZ": "Azerbaijan", "OM": "Oman", "QA": "Qatar",
    "TH": "Thailand", "MY": "Malaysia", "ID": "Indonesia", "JP": "Japan", "KR": "South Korea",
    "GR": "Greece", "CY": "Cyprus", "AT": "Austria", "CH": "Switzerland", "CZ": "Czechia",
    "HU": "Hungary", "PL": "Poland", "SE": "Sweden", "NO": "Norway", "DK": "Denmark", "FI": "Finland",
}


def esc(s: object) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def flag(cc: str) -> str:
    cc = (cc or "").upper()
    if len(cc) != 2 or not cc.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in cc)


def parse_date(s: str) -> dt.date:
    parts = [int(p) for p in str(s).split("-")]
    while len(parts) < 3:
        parts.append(1)
    return dt.date(*parts)


def fmt_date(s: str) -> str:
    d = parse_date(s)
    if len(str(s)) >= 10:
        return d.strftime("%-d %B %Y")
    return d.strftime("%B %Y")


def hue(slug: str) -> int:
    return int(hashlib.sha1(slug.encode()).hexdigest()[:4], 16) % 360


def gradient(slug: str) -> str:
    h = hue(slug)
    return f"linear-gradient(135deg, hsl({h} 70% 45%), hsl({(h + 50) % 360} 80% 60%))"


def ig_url(entry: str) -> str:
    kind = "reel" if entry.startswith("reel:") else "p"
    code = re.sub(r"^(reel|p):", "", entry)
    return f"https://www.instagram.com/{kind}/{code}/"


# --------------------------------------------------------------------------- validation

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}(-\d{2}){1,2}$")
IG_RE = re.compile(r"^(p|reel):[A-Za-z0-9_-]{5,}$")


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    trips = data.get("trips")
    if not isinstance(trips, list):
        return ["trips.json must have a top-level 'trips' list"]
    seen = set()
    for i, t in enumerate(trips):
        where = f"trips[{i}] ({t.get('slug', '?')})"
        for key in ("slug", "title", "place", "date"):
            if not t.get(key):
                errors.append(f"{where}: missing '{key}'")
        slug = t.get("slug", "")
        if slug and not SLUG_RE.match(slug):
            errors.append(f"{where}: slug must be lowercase words joined by dashes")
        if slug in seen:
            errors.append(f"{where}: duplicate slug")
        seen.add(slug)
        if t.get("date") and not DATE_RE.match(str(t["date"])):
            errors.append(f"{where}: date must be YYYY-MM or YYYY-MM-DD")
        else:
            try:
                parse_date(t["date"])
            except Exception:
                errors.append(f"{where}: date is not a real date")
        cc = t.get("country", "")
        if cc and (len(cc) != 2 or not cc.isalpha() or not cc.isupper()):
            errors.append(f"{where}: country must be a two-letter uppercase code")
        for k in ("lat", "lng"):
            if k in t and not isinstance(t[k], (int, float)):
                errors.append(f"{where}: {k} must be a number")
        if ("lat" in t) != ("lng" in t):
            errors.append(f"{where}: lat and lng must both be set or both omitted")
        for e in t.get("instagram", []):
            if not IG_RE.match(e):
                errors.append(f"{where}: bad instagram entry '{e}' (use p:CODE or reel:CODE)")
        photos = t.get("photos", [])
        names = set()
        for p in photos:
            f = p.get("file") if isinstance(p, dict) else None
            if not f:
                errors.append(f"{where}: photo without a file name")
                continue
            names.add(f)
            if not (ROOT / "photos" / slug / f).exists():
                errors.append(f"{where}: photos/{slug}/{f} does not exist")
            if not (ROOT / "photos" / slug / "thumbs" / f).exists():
                errors.append(f"{where}: photos/{slug}/thumbs/{f} is missing")
        if t.get("cover") and t["cover"] not in names:
            errors.append(f"{where}: cover '{t['cover']}' is not one of its photos")
    return errors


# --------------------------------------------------------------------------- templates

def layout(*, title: str, description: str, path: str, body: str, og_image: str | None,
           json_ld: list[dict], og_type: str = "website", extra_head: str = "", body_class: str = "") -> str:
    canonical = f"{SITE_URL}{path}"
    ld = "\n".join(
        f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in json_ld
    )
    og = ""
    if og_image:
        og = f'''<meta property="og:image" content="{esc(og_image)}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:image" content="{esc(og_image)}">'''
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="author" content="{esc(AUTHORS)}">
  <link rel="canonical" href="{esc(canonical)}">
  <meta name="theme-color" content="#0b0d12" media="(prefers-color-scheme: dark)">
  <meta name="theme-color" content="#f7f5f0" media="(prefers-color-scheme: light)">
  <meta property="og:site_name" content="{esc(SITE_NAME)}">
  <meta property="og:type" content="{esc(og_type)}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta name="twitter:card" content="{'summary_large_image' if og_image else 'summary'}">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(description)}">
  {og}
  <link rel="alternate" type="application/atom+xml" title="{esc(SITE_NAME)}" href="{SITE_URL}/feed.xml">
  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="icon" href="/assets/icon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/assets/icon-180.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&display=swap">
  <link rel="stylesheet" href="/assets/style.css">
  {extra_head}
  {ld}
  <script>(function(){{try{{var t=localStorage.getItem("theme");if(t)document.documentElement.dataset.theme=t;}}catch(e){{}}}})();</script>
</head>
<body class="{esc(body_class)}">
  <a class="skip" href="#main">Skip to content</a>
  <header class="site-header">
    <a class="brand" href="/" aria-label="{esc(SITE_NAME)} home">
      <span class="brand-mark" aria-hidden="true">✈</span>
      <span class="brand-text">{esc(SITE_NAME)}</span>
    </a>
    <nav class="site-nav" aria-label="Primary">
      <a href="/#trips">Trips</a>
      <a href="/#map">Map</a>
      <a href="{esc(INSTAGRAM)}" target="_blank" rel="noopener me">Instagram</a>
      <button class="theme-toggle" type="button" aria-label="Toggle dark mode" title="Toggle dark mode">
        <span class="sun" aria-hidden="true">☀</span><span class="moon" aria-hidden="true">☾</span>
      </button>
    </nav>
  </header>
  <main id="main">
{body}
  </main>
  <footer class="site-footer">
    <p>{esc(SITE_TAGLINE)}. Photos and reels on <a href="{esc(INSTAGRAM)}" rel="me">@elahe.dstn</a>.</p>
    <p class="fine">Static site, <a href="{esc(REPO_URL)}">built in the open</a> and served by GitHub Pages through Cloudflare.</p>
  </footer>
  <div class="lightbox" id="lightbox" aria-hidden="true" role="dialog" aria-label="Photo viewer">
    <button class="lb-close" aria-label="Close">×</button>
    <button class="lb-prev" aria-label="Previous photo">‹</button>
    <img id="lb-img" alt="">
    <button class="lb-next" aria-label="Next photo">›</button>
    <div class="lb-caption" id="lb-caption"></div>
  </div>
  <script src="/assets/app.js" defer></script>
</body>
</html>
'''


def card(t: dict) -> str:
    year = parse_date(t["date"]).year
    media = []
    if t.get("photos"):
        media.append(f"{len(t['photos'])} photo{'s' if len(t['photos']) != 1 else ''}")
    if t.get("instagram"):
        n = len(t["instagram"])
        media.append(f"{n} on Instagram")
    visual = f'<div class="card-art" style="background:{gradient(t["slug"])}" aria-hidden="true"><span>{flag(t.get("country", ""))}</span></div>'
    return f'''<a class="trip-card" href="/trips/{esc(t["slug"])}/" data-country="{esc(t.get("country", ""))}" data-year="{year}">
  <div class="card-visual">{visual}</div>
  <div class="card-body">
    <div class="card-top"><span class="chip">{flag(t.get("country", ""))} {esc(t["place"])}</span><time datetime="{esc(t["date"])}">{esc(fmt_date(t["date"]))}</time></div>
    <h3>{esc(t["title"])}</h3>
    <p class="card-meta">{esc(" · ".join(media) if media else "Album coming soon")}</p>
  </div>
</a>'''


def build_home(trips: list[dict], og: str | None) -> str:
    countries = sorted({t.get("country", "") for t in trips if t.get("country")})
    years = sorted({parse_date(t["date"]).year for t in trips}, reverse=True)
    posts = sum(len(t.get("instagram", [])) for t in trips)
    photos = sum(len(t.get("photos", [])) for t in trips)
    chips = "".join(
        f'<button class="filter" type="button" data-filter="country" data-value="{cc}">{flag(cc)} {esc(COUNTRY_NAMES.get(cc, cc))}</button>'
        for cc in countries
    )
    ychips = "".join(f'<button class="filter" type="button" data-filter="year" data-value="{y}">{y}</button>' for y in years)
    markers = [
        {"slug": t["slug"], "title": t["title"], "place": t["place"], "date": fmt_date(t["date"]), "lat": t["lat"], "lng": t["lng"],
         "flag": flag(t.get("country", ""))}
        for t in trips if "lat" in t and "lng" in t
    ]
    body = f'''
    <section class="hero">
      <p class="eyebrow">{esc(SITE_TAGLINE)}</p>
      <h1>Places we have been, <em>together</em>.</h1>
      <p class="lede">{esc(SITE_DESCRIPTION)}</p>
      <dl class="stats">
        <div><dt>Trips</dt><dd>{len(trips)}</dd></div>
        <div><dt>Countries</dt><dd>{len(countries)}</dd></div>
        <div><dt>Posts &amp; reels</dt><dd>{posts}</dd></div>
        {'<div><dt>Photos</dt><dd>' + str(photos) + '</dd></div>' if photos else ''}
      </dl>
    </section>

    <section class="map-section" id="map" aria-label="Map of our trips">
      <div id="trip-map" class="trip-map" data-markers='{esc(json.dumps(markers, ensure_ascii=False))}'></div>
      <noscript><p class="empty">The map needs JavaScript. The trips are listed below.</p></noscript>
    </section>

    <section class="trips" id="trips">
      <div class="section-head">
        <h2>All trips</h2>
        <div class="filters" role="group" aria-label="Filter trips">
          <button class="filter is-active" type="button" data-filter="all" data-value="">All</button>
          {chips}
          <span class="filter-sep" aria-hidden="true"></span>
          {ychips}
        </div>
      </div>
      <div class="trip-grid">
        {"".join(card(t) for t in trips)}
      </div>
      <p class="empty filter-empty" hidden>No trips match that filter.</p>
    </section>
'''
    json_ld = [
        {"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/",
         "description": SITE_DESCRIPTION, "author": {"@type": "Person", "name": "Elaheh Dastan", "sameAs": [INSTAGRAM]}},
        {"@context": "https://schema.org", "@type": "ItemList", "name": "Our trips",
         "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "url": f"{SITE_URL}/trips/{t['slug']}/", "name": t["title"]}
             for i, t in enumerate(trips)
         ]},
    ]
    return layout(title=f"{SITE_NAME} · {SITE_TAGLINE}", description=SITE_DESCRIPTION, path="/", body=body,
                  og_image=og, json_ld=json_ld, body_class="home",
                  extra_head='<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" crossorigin="anonymous" referrerpolicy="no-referrer">')


def build_trip(t: dict, prev_t: dict | None, next_t: dict | None, og: str | None) -> str:
    slug = t["slug"]
    photos = t.get("photos", [])
    insta = t.get("instagram", [])
    desc = t.get("description") or f"{t['title']}, {t['place']}, {fmt_date(t['date'])}. Photos and reels from our trip."
    photo_grid = ""
    if photos:
        photo_grid = '<section class="photos" aria-label="Photos"><div class="photo-grid">' + "".join(
            f'<a class="photo" href="/photos/{esc(slug)}/{esc(p["file"])}" data-index="{i}" data-caption="{esc(p.get("caption", ""))}">'
            f'<img src="/photos/{esc(slug)}/thumbs/{esc(p["file"])}" alt="{esc(p.get("caption") or t["title"])}" loading="lazy"></a>'
            for i, p in enumerate(photos)
        ) + "</div></section>"
    insta_html = ""
    if insta:
        insta_html = f'''<section class="instagram" aria-label="Instagram posts and reels">
      <h2>{"From Instagram" if photos else "Posts and reels"}</h2>
      <div class="ig-grid">''' + "".join(
            f'<blockquote class="instagram-media" data-instgrm-permalink="{ig_url(e)}" data-instgrm-version="14">'
            f'<a href="{ig_url(e)}" target="_blank" rel="noopener">View this {"reel" if e.startswith("reel:") else "post"} on Instagram</a></blockquote>'
            for e in insta
        ) + "</div></section>"
    if not photos and not insta:
        insta_html = '<p class="empty">No photos yet. Check back soon.</p>'
    nav = '<nav class="trip-nav" aria-label="Other trips">'
    nav += (f'<a class="nav-prev" href="/trips/{esc(prev_t["slug"])}/"><small>Newer</small><span>{esc(prev_t["title"])}</span></a>' if prev_t else "<span></span>")
    nav += (f'<a class="nav-next" href="/trips/{esc(next_t["slug"])}/"><small>Older</small><span>{esc(next_t["title"])}</span></a>' if next_t else "<span></span>")
    nav += "</nav>"
    body = f'''
    <article class="trip">
      <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Our Trips</a> <span aria-hidden="true">/</span> <span aria-current="page">{esc(t["title"])}</span></nav>
      <header class="trip-header" style="--art:{gradient(slug)}">
        <p class="eyebrow">{flag(t.get("country", ""))} {esc(t["place"])} · <time datetime="{esc(t["date"])}">{esc(fmt_date(t["date"]))}</time></p>
        <h1>{esc(t["title"])}</h1>
        {f'<p class="lede">{esc(t["description"])}</p>' if t.get("description") else ""}
      </header>
      {photo_grid}
      {insta_html}
      {nav}
    </article>
'''
    json_ld = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": t["title"], "item": f"{SITE_URL}/trips/{slug}/"},
        ]},
        {"@context": "https://schema.org", "@type": "ImageGallery", "name": t["title"], "url": f"{SITE_URL}/trips/{slug}/",
         "description": desc, "dateCreated": str(t["date"]), "author": {"@type": "Person", "name": "Elaheh Dastan", "sameAs": [INSTAGRAM]},
         "contentLocation": {"@type": "Place", "name": t["place"], **({"geo": {"@type": "GeoCoordinates", "latitude": t["lat"], "longitude": t["lng"]}} if "lat" in t else {})},
         "sameAs": [ig_url(e) for e in insta],
         "hasPart": [{"@type": "ImageObject", "contentUrl": f"{SITE_URL}/photos/{slug}/{p['file']}", "thumbnailUrl": f"{SITE_URL}/photos/{slug}/thumbs/{p['file']}", "caption": p.get("caption", "")} for p in photos]},
    ]
    title = f"{t['title']} · {t['place']} · {SITE_NAME}"
    return layout(title=title, description=desc, path=f"/trips/{slug}/", body=body, og_image=og, json_ld=json_ld, og_type="article", body_class="trip-page")


def build_404() -> str:
    body = '''
    <section class="hero">
      <p class="eyebrow">404</p>
      <h1>We have not been <em>here</em> yet.</h1>
      <p class="lede">That page does not exist. <a href="/">Back to all trips</a>.</p>
    </section>
'''
    return layout(title=f"Not found · {SITE_NAME}", description="Page not found.", path="/404.html", body=body, og_image=None, json_ld=[])


# --------------------------------------------------------------------------- og images

def make_og_images(trips: list[dict]) -> dict[str, str]:
    """Render 1200x630 social preview images with Pillow when it is installed."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not installed; skipping social preview images.")
        return {}
    out = DIST / "og"
    out.mkdir(parents=True, exist_ok=True)
    font_dirs = [Path("/usr/share/fonts"), Path("/System/Library/Fonts"), Path("/Library/Fonts"), Path.home() / "Library/Fonts"]
    bold = regular = None
    for d in font_dirs:
        for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "Helvetica.ttc", "SFNS.ttf"):
            for p in d.rglob(name):
                bold = bold or str(p)
        for name in ("DejaVuSans.ttf", "Arial.ttf", "Helvetica.ttc", "SFNS.ttf"):
            for p in d.rglob(name):
                regular = regular or str(p)

    def font(path, size):
        try:
            return ImageFont.truetype(path, size) if path else ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()

    def render(slug: str, title: str, sub: str, small: str) -> str:
        W, H = 1200, 630
        h = hue(slug)
        img = Image.new("RGB", (W, H))
        px = img.load()
        import colorsys
        c1 = colorsys.hls_to_rgb(h / 360, 0.42, 0.65)
        c2 = colorsys.hls_to_rgb(((h + 50) % 360) / 360, 0.58, 0.75)
        for y in range(H):
            for x in range(0, W, 4):
                k = (x / W + y / H) / 2
                r, g, b = (int(255 * (c1[i] * (1 - k) + c2[i] * k)) for i in range(3))
                for dx in range(4):
                    if x + dx < W:
                        px[x + dx, y] = (r, g, b)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((60, 60, W - 60, H - 60), radius=36, fill=(12, 14, 20))
        d.text((110, 120), small.upper(), font=font(regular, 28), fill=(170, 176, 190))
        tf = font(bold, 92 if len(title) < 16 else 72)
        d.text((110, 180), title, font=tf, fill=(245, 245, 247))
        d.text((110, 330), sub, font=font(regular, 40), fill=(220, 222, 228))
        d.text((110, H - 150), "we.1995parham.me", font=font(bold, 32), fill=(240, 179, 91))
        path = out / f"{slug}.png"
        img.save(path, optimize=True)
        return f"{SITE_URL}/og/{slug}.png"

    result = {"__home__": render("home", SITE_NAME, SITE_TAGLINE, "Elaheh & Parham")}
    for t in trips:
        result[t["slug"]] = render(t["slug"], t["title"], f"{t['place']} · {fmt_date(t['date'])}", SITE_NAME)
    return result


# --------------------------------------------------------------------------- build

def build() -> None:
    data = json.loads((ROOT / "trips.json").read_text())
    errors = validate(data)
    if errors:
        print("trips.json has problems:\n  " + "\n  ".join(errors))
        sys.exit(1)
    trips = sorted(data["trips"], key=lambda t: str(t["date"]), reverse=True)
    for t in trips:
        t.setdefault("photos", [])
        t.setdefault("instagram", [])

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    shutil.copytree(ROOT / "assets", DIST / "assets")
    if (ROOT / "photos").exists():
        shutil.copytree(ROOT / "photos", DIST / "photos", ignore=shutil.ignore_patterns(".gitkeep", ".DS_Store"))
    shutil.copy(ROOT / "trips.json", DIST / "trips.json")
    (DIST / ".nojekyll").write_text("")
    if (ROOT / "CNAME").exists():
        shutil.copy(ROOT / "CNAME", DIST / "CNAME")

    og = make_og_images(trips)
    (DIST / "index.html").write_text(build_home(trips, og.get("__home__")))
    for i, t in enumerate(trips):
        prev_t = trips[i - 1] if i > 0 else None
        next_t = trips[i + 1] if i + 1 < len(trips) else None
        d = DIST / "trips" / t["slug"]
        d.mkdir(parents=True)
        (d / "index.html").write_text(build_trip(t, prev_t, next_t, og.get(t["slug"])))
    (DIST / "404.html").write_text(build_404())

    today = dt.date.today().isoformat()
    urls = [("/", "weekly", "1.0")] + [(f"/trips/{t['slug']}/", "monthly", "0.8") for t in trips]
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE_URL}{p}</loc><lastmod>{today}</lastmod><changefreq>{f}</changefreq><priority>{pr}</priority></url>\n" for p, f, pr in urls)
        + "</urlset>\n"
    )
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")

    def rfc3339(s: str) -> str:
        return parse_date(s).isoformat() + "T00:00:00Z"

    entries = "".join(
        f'''  <entry>
    <title>{esc(t["title"])} · {esc(t["place"])}</title>
    <link href="{SITE_URL}/trips/{esc(t["slug"])}/"/>
    <id>{SITE_URL}/trips/{esc(t["slug"])}/</id>
    <updated>{rfc3339(t["date"])}</updated>
    <summary>{esc(t.get("description") or f"{t['title']}, {t['place']}, {fmt_date(t['date'])}.")}</summary>
  </entry>
''' for t in trips)
    (DIST / "feed.xml").write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{esc(SITE_NAME)}</title>
  <subtitle>{esc(SITE_DESCRIPTION)}</subtitle>
  <link href="{SITE_URL}/"/>
  <link rel="self" href="{SITE_URL}/feed.xml"/>
  <id>{SITE_URL}/</id>
  <updated>{rfc3339(trips[0]["date"]) if trips else today + "T00:00:00Z"}</updated>
  <author><name>{esc(AUTHORS)}</name></author>
{entries}</feed>
''')
    (DIST / "manifest.webmanifest").write_text(json.dumps({
        "name": SITE_NAME, "short_name": "Trips", "description": SITE_DESCRIPTION, "start_url": "/", "display": "standalone",
        "background_color": "#0b0d12", "theme_color": "#0b0d12",
        "icons": [{"src": "/assets/icon.svg", "sizes": "any", "type": "image/svg+xml"}, {"src": "/assets/icon-180.png", "sizes": "180x180", "type": "image/png"}],
    }, indent=2))
    pages = 1 + len(trips) + 1
    print(f"Built {pages} pages into dist/ ({len(trips)} trips, {sum(len(t['instagram']) for t in trips)} Instagram embeds, {len(og)} social images).")


def linkcheck() -> None:
    bad = []
    for page in DIST.rglob("*.html"):
        text = page.read_text()
        for m in re.finditer(r'(?:href|src)="(/[^"#?]*)', text):
            target = m.group(1)
            p = DIST / target.lstrip("/")
            if target.endswith("/"):
                p = p / "index.html"
            if not p.exists():
                bad.append(f"{page.relative_to(DIST)} -> {target}")
    if bad:
        print("Broken internal links:\n  " + "\n  ".join(sorted(set(bad))))
        sys.exit(1)
    print("All internal links resolve.")


if __name__ == "__main__":
    if "--check" in sys.argv:
        errs = validate(json.loads((ROOT / "trips.json").read_text()))
        if errs:
            print("trips.json has problems:\n  " + "\n  ".join(errs))
            sys.exit(1)
        print("trips.json is valid.")
    else:
        build()
        if "--linkcheck" in sys.argv:
            linkcheck()
