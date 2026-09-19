(function () {
  "use strict";

  let map = null;
  let markers = [];
  let infoWindow = null;

  const el = (id) => document.getElementById(id);
  const queryInput = el("queryInput");
  const analyzeBtn = el("analyzeBtn");
  const statusLine = el("statusLine");
  const resultsSection = el("resultsSection");
  const emptyState = el("emptyState");
  const projectFacts = el("projectFacts");
  const candidateList = el("candidateList");
  const reportBody = el("reportBody");
  const warningsBlock = el("warningsBlock");
  const loadingOverlay = el("loadingOverlay");
  const loadingText = el("loadingText");

  const LOADING_MESSAGES = [
    "Reading your request…",
    "Planning the research strategy…",
    "Pulling live map & places data…",
    "Scoring candidate sites…",
    "Writing the final report…",
  ];

  function cycleLoadingMessages() {
    let i = 0;
    loadingText.textContent = LOADING_MESSAGES[0];
    return setInterval(() => {
      i = (i + 1) % LOADING_MESSAGES.length;
      loadingText.textContent = LOADING_MESSAGES[i];
    }, 2200);
  }

  // ---------- Google Maps bootstrap ----------
  async function loadGoogleMaps() {
    const res = await fetch("/api/config");
    const cfg = await res.json();
    if (!cfg.mapsApiKey) {
      statusLine.textContent = "Server is missing GOOGLE_MAPS_API_KEY — map cannot load.";
      return;
    }
    return new Promise((resolve) => {
      window.addEventListener("google-maps-ready", () => resolve(), { once: true });
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(cfg.mapsApiKey)}&callback=__initMap&v=weekly`;
      script.async = true;
      document.head.appendChild(script);
    });
  }

  function initMap(center, zoom) {
    map = new google.maps.Map(el("map"), {
      center,
      zoom: zoom || 13,
      mapId: "SITE_SELECTOR_MAP",
      disableDefaultUI: false,
      streetViewControl: false,
      fullscreenControl: false,
    });
    infoWindow = new google.maps.InfoWindow();
  }

  function clearMarkers() {
    markers.forEach((m) => (m.map = null));
    markers = [];
  }

  function pinSvg(color) {
    return {
      path: "M12 0C7 0 3 4 3 9c0 6.5 9 15 9 15s9-8.5 9-15c0-5-4-9-9-9z",
      fillColor: color,
      fillOpacity: 1,
      strokeColor: "#121A21",
      strokeWeight: 1,
      scale: 1.4,
      anchor: new google.maps.Point(12, 24),
    };
  }

  function renderMarkers(candidates) {
    clearMarkers();
    const bounds = new google.maps.LatLngBounds();
    candidates.forEach((c) => {
      const isTop = c.rank === 1;
      const marker = new google.maps.Marker({
        position: { lat: c.lat, lng: c.lng },
        map,
        icon: pinSvg(isTop ? "#5C7A5A" : "#D98E32"),
        label: {
          text: String(c.rank),
          color: "#F4F1E9",
          fontFamily: "IBM Plex Mono, monospace",
          fontSize: "11px",
          fontWeight: "600",
        },
        title: `#${c.rank} · score ${c.total_score}`,
        zIndex: isTop ? 999 : c.rank,
      });
      marker.addListener("click", () => {
        infoWindow.setContent(candidateInfoHtml(c));
        infoWindow.open(map, marker);
      });
      markers.push(marker);
      bounds.extend(marker.getPosition());
    });
    if (candidates.length > 1) map.fitBounds(bounds, 60);
    else if (candidates.length === 1) { map.setCenter(candidates[0]); map.setZoom(14); }
  }

  function candidateInfoHtml(c) {
    return `
      <div style="font-family: IBM Plex Sans, sans-serif; max-width: 220px;">
        <strong style="font-family: Fraunces, serif; font-size: 1rem;">#${c.rank} · ${c.total_score} pts</strong>
        <div style="font-size: 0.8rem; color: #55606A; margin: 4px 0 8px;">${c.address || "Address unavailable"}</div>
        <div style="font-family: IBM Plex Mono, monospace; font-size: 0.72rem; color: #55606A;">
          ${c.lat.toFixed(5)}, ${c.lng.toFixed(5)}
        </div>
      </div>`;
  }

  // ---------- Rendering results panel ----------
  function renderFacts(projectDefinition) {
    projectFacts.innerHTML = "";
    const rows = [
      ["business", projectDefinition.business_type],
      ["location", projectDefinition.resolved_center_address || `${projectDefinition.city}, ${projectDefinition.country}`],
      ["radius", projectDefinition.search_radius_km ? `${projectDefinition.search_radius_km} km` : null],
      ["customer", projectDefinition.customer_profile],
    ];
    rows.forEach(([k, v]) => {
      if (!v) return;
      const dt = document.createElement("dt");
      dt.textContent = k;
      const dd = document.createElement("dd");
      dd.textContent = v;
      projectFacts.appendChild(dt);
      projectFacts.appendChild(dd);
    });
  }

  function renderCandidateList(candidates) {
    candidateList.innerHTML = "";
    candidates.forEach((c) => {
      const li = document.createElement("li");
      li.className = "candidate-item" + (c.rank === 1 ? " top-pick" : "");
      li.tabIndex = 0;
      li.innerHTML = `
        <span class="candidate-rank">${c.rank}</span>
        <span class="candidate-main">
          <span class="candidate-address">${c.address || "Address unavailable"}</span>
          <span class="candidate-coords">${c.lat.toFixed(5)}, ${c.lng.toFixed(5)}</span>
        </span>
        <span class="candidate-score">${c.total_score}</span>
      `;
      const focusCandidate = () => {
        map.panTo({ lat: c.lat, lng: c.lng });
        map.setZoom(15);
        infoWindow.setContent(candidateInfoHtml(c));
        const marker = markers[candidates.indexOf(c)];
        if (marker) infoWindow.open(map, marker);
      };
      li.addEventListener("click", focusCandidate);
      li.addEventListener("keydown", (e) => { if (e.key === "Enter") focusCandidate(); });
      candidateList.appendChild(li);
    });
  }

  function renderReport(markdown) {
    reportBody.innerHTML = window.marked ? window.marked.parse(markdown) : `<pre>${markdown}</pre>`;
  }

  function renderWarnings(warnings) {
    if (!warnings || warnings.length === 0) {
      warningsBlock.classList.add("hidden");
      return;
    }
    warningsBlock.classList.remove("hidden");
    warningsBlock.innerHTML = warnings.map((w) => `<p>⚠ ${w}</p>`).join("");
  }

  // ---------- Main flow ----------
  async function runAnalysis() {
    const query = queryInput.value.trim();
    if (query.length < 3) {
      statusLine.textContent = "Describe the business and area first.";
      return;
    }
    analyzeBtn.disabled = true;
    statusLine.textContent = "";
    loadingOverlay.classList.remove("hidden");
    const cycle = cycleLoadingMessages();

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        const message = typeof detail === "string" ? detail : JSON.stringify(detail);
        throw new Error(message);
      }

      emptyState.classList.add("hidden");
      resultsSection.classList.remove("hidden");
      renderFacts(data.project_definition);
      renderCandidateList(data.candidates);
      renderReport(data.report);
      renderWarnings(data.warnings);

      if (!map) initMap(data.map_center);
      else map.setCenter(data.map_center);
      renderMarkers(data.candidates);
    } catch (err) {
      statusLine.textContent = `Error: ${err.message}`;
    } finally {
      clearInterval(cycle);
      loadingOverlay.classList.add("hidden");
      analyzeBtn.disabled = false;
    }
  }

  analyzeBtn.addEventListener("click", runAnalysis);
  queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) runAnalysis();
  });

  // Bootstrap the map (centered on a neutral default) as soon as the key is available,
  // so it's visible even before the first analysis runs.
  loadGoogleMaps().then(() => {
    if (!map && window.google) initMap({ lat: 20, lng: 0 }, 2);
  });
})();
