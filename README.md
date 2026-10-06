# we.1995parham.me

Pictures, posts and reels from Elaheh and Parham's trips around the world, at <https://we.1995parham.me> (also <https://parham-alvani.github.io>).

## How it works

`trips.json` is the only content file. `scripts/build.py` turns it into a static site in `dist/`: a home page with a map and filters, one page per trip at `/trips/<slug>/`, a sitemap, an Atom feed, `robots.txt`, a web manifest and a social preview image per page. There is no framework and no bundler; the pages are plain HTML with one stylesheet and one script.

The trip list follows Elaheh's Instagram account, [@elahe.dstn](https://www.instagram.com/elahe.dstn/), where every trip has one or more posts and reels. A trip can hold two kinds of media: photos committed to this repository under `photos/<slug>/`, and an `instagram` list of post and reel codes that the trip page embeds with Instagram's official embed script. Nothing is copied from Instagram, so the embeds stay in sync with the account and only render while it is public.

## Deployment

Pushing to `main` runs the **Deploy** workflow, which validates `trips.json`, builds `dist/`, checks every internal link and publishes to GitHub Pages. Pull requests run the **Check** workflow with the same validation but no deploy. Once a week the **Instagram embeds** workflow probes every embedded post and opens an issue if one has gone missing.

The custom domain is a Cloudflare CNAME, `we.1995parham.me` to `parham-alvani.github.io`, proxied through Cloudflare with HTTPS enforced on the GitHub side. The `CNAME` file in the repository and the Pages setting have to agree.

## Adding a trip

Add an object to `trips.json`. Only `slug`, `title`, `place` and `date` are required; `country` is a two-letter code used for the flag and the filter, `lat` and `lng` put the trip on the map, and `instagram` lists the posts to embed. An Instagram code is the part of the URL after `/p/` or `/reel/`, prefixed with `p:` or `reel:`.

```json
{
  "slug": "tbilisi",
  "title": "Tbilisi",
  "place": "Georgia",
  "country": "GE",
  "date": "2026-06",
  "lat": 41.7151,
  "lng": 44.8271,
  "description": "",
  "instagram": ["reel:DZkY3oaMDnd", "p:DZiAKwkjB5Q"]
}
```

Run `python3 scripts/build.py --check` to validate before pushing.

## Adding photos

To put photos of your own into an album, put them in a folder and run the import script with the trip's slug. It resizes the originals so the long edge is at most 2000px, generates 600px thumbnails, converts HEIC to JPEG and updates the trip's photo list, keeping any captions you already wrote.

```sh
python3 scripts/add-trip.py ~/Pictures/Tbilisi --slug tbilisi
```

The script uses `sips` on macOS and falls back to Pillow (`pip install pillow`) elsewhere. For a brand new trip pass `--title`, `--place` and `--date` as well.

## Previewing locally

```sh
python3 scripts/build.py && python3 -m http.server -d dist 8000
```

Then open <http://localhost:8000>. Install Pillow to also get the social preview images locally; the workflow always has it.

## Notes

Photos are committed to the repository, so keep an eye on size. Resizing at import keeps a typical trip of 50 photos around 30 to 60 MB. The Check workflow fails on any photo over 4 MB.
