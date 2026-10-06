# parham-alvani.github.io

A small static photo site for pictures from our trips around the world, served by GitHub Pages at <https://parham-alvani.github.io>.

## How it works

There is no build step. `index.html` loads `assets/app.js`, which reads `trips.json` and renders a grid of trips. Clicking a trip shows its photos, and clicking a photo opens a lightbox with keyboard arrows and swipe support. Images live under `photos/<slug>/` with thumbnails in `photos/<slug>/thumbs/`.

## Trips

The trip list in `trips.json` follows Elaheh's Instagram account, [@elahe.dstn](https://www.instagram.com/elahe.dstn/), where every trip has one or more posts and reels. Each trip entry can hold two kinds of media: photos committed to this repository under `photos/<slug>/`, and an `instagram` list of post and reel codes that the trip page embeds with Instagram's official embed script. Nothing is copied from Instagram; the embeds load straight from Instagram and stay in sync with the account, so they only render while the account is public.

An Instagram code is the part of the URL after `/p/` or `/reel/`. Reels are prefixed so the embed uses the right permalink:

```json
"instagram": ["reel:DXy78vYsWlV", "p:DZiAKwkjB5Q"]
```

## Adding photos

To fill an existing album, put its photos in a folder and run the import script with the trip's slug. The title, place and date already in `trips.json` are kept.

```sh
python3 scripts/add-trip.py ~/Pictures/Larak --slug larak-island
```

For a brand new trip, pass the details as well. It resizes the originals so the long edge is at most 2000px, generates 600px thumbnails, converts HEIC to JPEG, and adds the trip to `trips.json`.

```sh
python3 scripts/add-trip.py ~/Pictures/Lisbon --title "Lisbon" --place "Portugal" --date 2025-05 --description "A long weekend of trams and pastéis de nata."
```

The script uses `sips` on macOS and falls back to Pillow (`pip install pillow`) elsewhere. Afterwards, open `trips.json` to add captions or change the cover photo, then commit and push. GitHub Pages redeploys from `main` automatically.

Re-running the script for the same slug replaces that album's photo list but keeps the captions you already wrote for files that are still there, so you can re-import a folder after adding photos to it.

## Previewing locally

```sh
python3 -m http.server 8000
```

Then open <http://localhost:8000>. A plain `file://` open will not work because the page fetches `trips.json`.

## Notes

Photos are committed to the repository, so keep an eye on size. Resizing at import keeps a typical trip of 50 photos around 30 to 60 MB. If the repository grows past a few GB, move originals to a separate storage and keep only the resized copies here.
