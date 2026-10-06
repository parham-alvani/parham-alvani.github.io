// Our Trips — progressive enhancement on top of the static pages built by scripts/build.py.
(function () {
  "use strict";

  // Old links used hash routes (#/slug); send them to the real page.
  const m = location.hash.match(/^#\/([a-z0-9-]+)\/?$/);
  if (m && location.pathname === "/") {
    location.replace(`/trips/${m[1]}/`);
    return;
  }

  // ---- Theme toggle --------------------------------------------------------
  const root = document.documentElement;
  const toggle = document.querySelector(".theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", () => {
      const dark = matchMedia("(prefers-color-scheme: dark)").matches;
      const current = root.dataset.theme || (dark ? "dark" : "light");
      const next = current === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      try { localStorage.setItem("theme", next); } catch (e) { /* private mode */ }
      if (window.__map) setTiles();
    });
  }
  const isDark = () => root.dataset.theme === "dark" || (!root.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);

  // ---- Filters (home) ------------------------------------------------------
  const filters = document.querySelectorAll(".filter");
  const cards = document.querySelectorAll(".trip-card");
  if (filters.length && cards.length) {
    const emptyNote = document.querySelector(".filter-empty");
    filters.forEach((btn) =>
      btn.addEventListener("click", () => {
        filters.forEach((b) => b.classList.toggle("is-active", b === btn));
        const kind = btn.dataset.filter, value = btn.dataset.value;
        let shown = 0;
        cards.forEach((c) => {
          const ok = kind === "all" || c.dataset[kind] === value;
          c.hidden = !ok;
          if (ok) shown++;
        });
        if (emptyNote) emptyNote.hidden = shown > 0;
        if (window.__map) window.__map.setFilter(kind, value);
      })
    );
  }

  // ---- Map (home) ----------------------------------------------------------
  const mapEl = document.getElementById("trip-map");
  let tileLayer = null;
  // OpenStreetMap tiles; in dark mode the tile pane is inverted with CSS (see .map-dark).
  function setTiles() {
    if (!window.L || !window.__map) return;
    mapEl.classList.toggle("map-dark", isDark());
    if (tileLayer) return;
    tileLayer = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(window.__map.map);
  }
  if (mapEl) {
    const markers = JSON.parse(mapEl.dataset.markers || "[]");
    const s = document.createElement("script");
    s.src = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js";
    s.crossOrigin = "anonymous";
    s.referrerPolicy = "no-referrer";
    s.onload = () => {
      const map = L.map(mapEl, { scrollWheelZoom: false, worldCopyJump: true });
      window.__map = { map, layers: [] };
      setTiles();
      const group = [];
      markers.forEach((mk) => {
        const icon = L.divIcon({ className: "", html: `<div class="pin-flag">${mk.flag || "📍"}</div>`, iconSize: [24, 24], iconAnchor: [12, 12] });
        const marker = L.marker([mk.lat, mk.lng], { icon, title: mk.title }).addTo(map);
        marker.bindPopup(`<a href="/trips/${mk.slug}/">${mk.title}</a><br><small>${mk.place} · ${mk.date}</small>`);
        marker.on("mouseover", () => marker.openPopup());
        const card = document.querySelector(`.trip-card[href="/trips/${mk.slug}/"]`);
        window.__map.layers.push({ marker, country: card ? card.dataset.country : "", year: card ? card.dataset.year : "" });
        group.push([mk.lat, mk.lng]);
      });
      if (group.length) map.fitBounds(group, { padding: [40, 40], maxZoom: 6 });
      window.__map.setFilter = (kind, value) => {
        const visible = [];
        window.__map.layers.forEach((l) => {
          const ok = kind === "all" || l[kind] === value;
          if (ok) { l.marker.addTo(map); visible.push(l.marker.getLatLng()); } else map.removeLayer(l.marker);
        });
        if (visible.length) map.fitBounds(visible, { padding: [40, 40], maxZoom: 6 });
      };
    };
    document.head.appendChild(s);
  }

  // ---- Instagram embeds ----------------------------------------------------
  if (document.querySelector(".instagram-media")) {
    if (window.instgrm && window.instgrm.Embeds) window.instgrm.Embeds.process();
    else {
      const ig = document.createElement("script");
      ig.async = true;
      ig.src = "https://www.instagram.com/embed.js";
      document.body.appendChild(ig);
    }
  }

  // ---- Lightbox for local photos ------------------------------------------
  const lightbox = document.getElementById("lightbox");
  const photos = [...document.querySelectorAll(".photo")];
  if (lightbox && photos.length) {
    const img = document.getElementById("lb-img");
    const cap = document.getElementById("lb-caption");
    let index = 0;
    const show = () => {
      const p = photos[index];
      img.src = p.getAttribute("href");
      img.alt = p.dataset.caption || p.querySelector("img").alt;
      cap.textContent = `${p.dataset.caption ? p.dataset.caption + " — " : ""}${index + 1} / ${photos.length}`;
      [index + 1, index - 1].forEach((j) => { if (photos[j]) new Image().src = photos[j].getAttribute("href"); });
    };
    const open = (i) => { index = i; show(); lightbox.classList.add("open"); lightbox.setAttribute("aria-hidden", "false"); document.body.style.overflow = "hidden"; };
    const close = () => { lightbox.classList.remove("open"); lightbox.setAttribute("aria-hidden", "true"); img.src = ""; document.body.style.overflow = ""; };
    const step = (d) => { index = (index + d + photos.length) % photos.length; show(); };
    photos.forEach((p, i) => p.addEventListener("click", (e) => { e.preventDefault(); open(i); }));
    lightbox.querySelector(".lb-close").addEventListener("click", close);
    lightbox.querySelector(".lb-prev").addEventListener("click", () => step(-1));
    lightbox.querySelector(".lb-next").addEventListener("click", () => step(1));
    lightbox.addEventListener("click", (e) => { if (e.target === lightbox) close(); });
    document.addEventListener("keydown", (e) => {
      if (!lightbox.classList.contains("open")) return;
      if (e.key === "Escape") close(); else if (e.key === "ArrowLeft") step(-1); else if (e.key === "ArrowRight") step(1);
    });
    let touchX = null;
    lightbox.addEventListener("touchstart", (e) => { touchX = e.touches[0].clientX; }, { passive: true });
    lightbox.addEventListener("touchend", (e) => {
      if (touchX === null) return;
      const dx = e.changedTouches[0].clientX - touchX;
      if (Math.abs(dx) > 40) step(dx < 0 ? 1 : -1);
      touchX = null;
    });
  }
})();
