# parham-alvani.github.io

A small static photo site for pictures from our trips around the world, served by GitHub Pages at <https://parham-alvani.github.io>.

## How it works

There is no build step. `index.html` loads `assets/app.js`, which reads `trips.json` and renders a grid of trips. Clicking a trip shows its photos, and clicking a photo opens a lightbox with keyboard arrows and swipe support. Images live under `photos/<slug>/` with thumbnails in `photos/<slug>/thumbs/`.

## Adding a trip

Put the photos for one trip in a folder, then run the import script. It resizes the originals so the long edge is at most 2000px, generates 600px thumbnails, converts HEIC to JPEG, and adds the trip to `trips.json`.

```sh
python3 scripts/add-trip.py ~/Pictures/Lisbon --title "Lisbon" --place "Portugal" --date 2025-05 --description "A long weekend of trams and pastéis de nata."
```

The script uses `sips` on macOS and falls back to Pillow (`pip install pillow`) elsewhere. Afterwards, open `trips.json` to add captions or change the cover photo, then commit and push. GitHub Pages redeploys from `main` automatically.

Re-running the script with the same title (or `--slug`) replaces that trip's entry, so you can re-import a folder after adding photos to it.

## Previewing locally

```sh
python3 -m http.server 8000
```

Then open <http://localhost:8000>. A plain `file://` open will not work because the page fetches `trips.json`.

## Notes

Photos are committed to the repository, so keep an eye on size. Resizing at import keeps a typical trip of 50 photos around 30 to 60 MB. If the repository grows past a few GB, move originals to a separate storage and keep only the resized copies here.
