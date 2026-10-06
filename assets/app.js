// Tiny hash-routed gallery. Data lives in trips.json; images live under photos/<slug>/.
(function () {
  const app = document.getElementById("app");
  const lightbox = document.getElementById("lightbox");
  const lbImg = document.getElementById("lb-img");
  const lbCaption = document.getElementById("lb-caption");

  let trips = [];
  let current = { photos: [], index: 0 };

  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const photoSrc = (trip, name) => `photos/${trip.slug}/${name}`;
  const thumbSrc = (trip, name) => `photos/${trip.slug}/thumbs/${name}`;

  function formatDate(d) {
    if (!d) return "";
    const date = new Date(d);
    if (isNaN(date)) return d;
    return date.toLocaleDateString(undefined, { year: "numeric", month: "long" });
  }

  function renderHome() {
    document.title = "Our Trips";
    if (!trips.length) {
      app.innerHTML = `<p class="empty">No trips yet. Add one with <code>python3 scripts/add-trip.py</code>.</p>`;
      return;
    }
    const sorted = [...trips].sort((a, b) => String(b.date).localeCompare(String(a.date)));
    app.innerHTML = `<div class="grid">${sorted
      .map((t) => {
        const cover = t.cover || (t.photos[0] && t.photos[0].file);
        const img = cover
          ? `<img src="${thumbSrc(t, cover)}" alt="${esc(t.title)}" loading="lazy">`
          : `<div class="placeholder" aria-hidden="true">${esc(t.title.slice(0, 1))}</div>`;
        return `<a class="card${cover ? "" : " no-photos"}" href="#/${encodeURIComponent(t.slug)}">${img}
          <div class="caption"><strong>${esc(t.title)}</strong><span>${esc(t.place)} · ${esc(formatDate(t.date))}${(t.instagram || []).length ? ` · ${t.instagram.length} on Instagram` : ""}</span></div></a>`;
      })
      .join("")}</div>`;
  }

  function renderTrip(slug) {
    const trip = trips.find((t) => t.slug === slug);
    if (!trip) {
      app.innerHTML = `<p class="breadcrumb"><a href="#/">← All trips</a></p><p class="empty">Trip not found.</p>`;
      return;
    }
    document.title = `${trip.title} · Our Trips`;
    current = { trip, photos: trip.photos, index: 0 };
    app.innerHTML = `
      <p class="breadcrumb"><a href="#/">← All trips</a></p>
      <div class="trip-header">
        <h2>${esc(trip.title)}</h2>
        <div class="meta">${esc(trip.place)} · ${esc(formatDate(trip.date))} · ${trip.photos.length} photo${trip.photos.length === 1 ? "" : "s"}</div>
        ${trip.description ? `<p class="description">${esc(trip.description)}</p>` : ""}
      </div>
      ${trip.photos.length || (trip.instagram || []).length ? "" : `<p class="empty">No photos yet. Import them with <code>python3 scripts/add-trip.py &lt;folder&gt; --slug ${esc(trip.slug)}</code>.</p>`}
      <div class="grid photos">${trip.photos
        .map(
          (p, i) => `<a class="card" href="${photoSrc(trip, p.file)}" data-index="${i}">
            <img src="${thumbSrc(trip, p.file)}" alt="${esc(p.caption || trip.title)}" loading="lazy"></a>`
        )
        .join("")}</div>
      ${renderInstagram(trip)}`;
    loadInstagramEmbeds();
    app.querySelectorAll(".photos .card").forEach((el) =>
      el.addEventListener("click", (e) => {
        e.preventDefault();
        openLightbox(Number(el.dataset.index));
      })
    );
  }

  // Instagram posts and reels are embedded with Instagram's official embed script,
  // so nothing is copied; each entry is a post or reel code from the URL.
  function renderInstagram(trip) {
    const codes = trip.instagram || [];
    if (!codes.length) return "";
    return `<section class="instagram">
      <h3>${trip.photos.length ? "From Instagram" : "On Instagram"}</h3>
      <div class="ig-grid">${codes
        .map((c) => {
          const kind = c.startsWith("reel:") ? "reel" : "p";
          const code = c.replace(/^(reel|p):/, "");
          const url = `https://www.instagram.com/${kind}/${encodeURIComponent(code)}/`;
          return `<blockquote class="instagram-media" data-instgrm-permalink="${url}" data-instgrm-version="14">
            <a href="${url}" target="_blank" rel="noopener">View on Instagram</a></blockquote>`;
        })
        .join("")}</div></section>`;
  }

  let instagramScript = null;
  function loadInstagramEmbeds() {
    if (!document.querySelector(".instagram-media")) return;
    if (window.instgrm && window.instgrm.Embeds) {
      window.instgrm.Embeds.process();
      return;
    }
    if (instagramScript) return;
    instagramScript = document.createElement("script");
    instagramScript.async = true;
    instagramScript.src = "https://www.instagram.com/embed.js";
    document.body.appendChild(instagramScript);
  }

  function openLightbox(i) {
    current.index = i;
    showCurrent();
    lightbox.classList.add("open");
    lightbox.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeLightbox() {
    lightbox.classList.remove("open");
    lightbox.setAttribute("aria-hidden", "true");
    lbImg.src = "";
    document.body.style.overflow = "";
  }

  function showCurrent() {
    const p = current.photos[current.index];
    if (!p) return;
    lbImg.src = photoSrc(current.trip, p.file);
    lbImg.alt = p.caption || current.trip.title;
    lbCaption.textContent = `${p.caption ? p.caption + " — " : ""}${current.index + 1} / ${current.photos.length}`;
    // Preload neighbours.
    [current.index + 1, current.index - 1].forEach((j) => {
      const q = current.photos[j];
      if (q) new Image().src = photoSrc(current.trip, q.file);
    });
  }

  function step(delta) {
    const n = current.photos.length;
    if (!n) return;
    current.index = (current.index + delta + n) % n;
    showCurrent();
  }

  lightbox.querySelector(".lb-close").addEventListener("click", closeLightbox);
  lightbox.querySelector(".lb-prev").addEventListener("click", () => step(-1));
  lightbox.querySelector(".lb-next").addEventListener("click", () => step(1));
  lightbox.addEventListener("click", (e) => { if (e.target === lightbox) closeLightbox(); });
  document.addEventListener("keydown", (e) => {
    if (!lightbox.classList.contains("open")) return;
    if (e.key === "Escape") closeLightbox();
    else if (e.key === "ArrowLeft") step(-1);
    else if (e.key === "ArrowRight") step(1);
  });

  // Basic swipe support.
  let touchX = null;
  lightbox.addEventListener("touchstart", (e) => { touchX = e.touches[0].clientX; }, { passive: true });
  lightbox.addEventListener("touchend", (e) => {
    if (touchX === null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 40) step(dx < 0 ? 1 : -1);
    touchX = null;
  });

  function route() {
    const hash = location.hash.replace(/^#\/?/, "");
    if (hash) renderTrip(decodeURIComponent(hash));
    else renderHome();
    window.scrollTo(0, 0);
  }

  fetch("trips.json", { cache: "no-cache" })
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`trips.json: ${r.status}`))))
    .then((data) => { trips = data.trips || []; route(); })
    .catch((err) => { app.innerHTML = `<p class="empty">Could not load trips: ${esc(err.message)}</p>`; });

  window.addEventListener("hashchange", route);
})();
