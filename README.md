# AI Site Selector

A complete Python workflow — FastAPI backend + single-page web UI — that turns a plain-English
request like *"find the best spot for a coffee shop near downtown Austin"* into a ranked,
mapped shortlist of real candidate sites, using **Gemini on Vertex AI** for reasoning and the
**Google Maps Platform** for real geospatial data.

Matches this pipeline end-to-end:

```
Query → Gemini Intent Analyzer → Project Definition → Gemini Planner → Research Strategy
      → Google Maps (Geo / Traffic / Business data)
      → Geo Processing Engine (Candidate Sites | Routing Analysis | Spatial Analysis)
      → Candidate Evaluation → Gemini Analyst → Final Site Report (map + coordinates + data)
```

## 1. Prerequisites

- Python 3.10+
- A Google Cloud project with **Vertex AI API** enabled, and a Gemini model available to it.
- A **Google Maps Platform** API key with these APIs enabled:
  - Geocoding API
  - Places API
  - Distance Matrix API
  - Maps JavaScript API

## 2. Get your credentials

**Vertex AI (`vertex.json`)**
1. In Google Cloud Console → IAM & Admin → Service Accounts, create (or reuse) a service account
   with the **Vertex AI User** role.
2. Create a JSON key for it and download it.
3. Save it in the project root as `vertex.json` (a `vertex.example.json` template is included
   for reference — do not commit your real key).

**Google Maps API key**
1. In Google Cloud Console → APIs & Services → Credentials, create an API key.
2. Enable Geocoding API, Places API, Distance Matrix API, and Maps JavaScript API for it.
3. Restrict the key (by HTTP referrer for the JS Maps usage, and/or by API) before using it
   anywhere public — this key is sent to the browser to render the map.

## 3. Configure the app

```bash
cp .env.example .env
```

Edit `.env`:

```
VERTEX_CREDENTIALS_PATH=vertex.json
VERTEX_PROJECT_ID=your-gcp-project-id
VERTEX_LOCATION=us-central1
GEMINI_MODEL=gemini-2.5-flash        # use whatever Gemini model your project has access to
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
```

## 4. Install & run

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** — type a request, click **Find the best site**, and watch the
right-hand map populate with ranked, numbered candidates while the left panel shows the
project's "reading" of your query, the ranked list, and Gemini's final written report.

Check `GET /api/health` any time to confirm your credentials are wired up correctly.

## 5. Project layout

```
main.py                        FastAPI app: serves the UI + /api/analyze, /api/config, /api/health
config.py                      Loads all credentials/settings from .env + vertex.json
app/
  schemas.py                   Pydantic request/response models
  workflow.py                  Orchestrates the full pipeline (mirrors the architecture diagram)
  services/
    vertex_client.py           Gemini/Vertex AI wrapper (auth via vertex.json)
    maps_client.py             Google Maps wrapper: geocoding, places, distance matrix
    intent_analyzer.py         Stage 1 — Gemini: query → structured project definition
    planner.py                 Stage 2 — Gemini: project definition → research strategy
    geo_processing.py          Stage 3 — candidate grid, spatial analysis, routing analysis
    evaluator.py                Stage 4 — normalizes metrics + applies weights → ranked list
    analyst.py                  Stage 5 — Gemini: ranked candidates → final markdown report
static/
  index.html, style.css, app.js   Single-page frontend + Google Maps JS rendering
```

## 6. How the scoring works

For each candidate point in a grid around your target area, the engine measures:

| Metric                | Source                          | Meaning                                  |
|------------------------|----------------------------------|-------------------------------------------|
| `demand_proxy`         | Places API nearby search        | Density of POIs that indicate demand (offices, residences, etc. — chosen per business type by the Planner) |
| `competitor_density`   | Places API nearby search        | Density of direct competitors nearby (lower is better) |
| `accessibility`        | Distance Matrix API (traffic-aware) | Average drive time to key anchor points (city center, transit, etc.) |
| `foot_traffic_proxy`   | Places API nearby search        | Proxy for passing foot traffic |

Each metric is min-max normalized to 0–100 across the candidate set, then combined using
weights Gemini's Planner chose for **this specific business type**, producing a `total_score`
used to rank sites. Gemini's Analyst then writes the final narrative report from that ranked,
numeric data — it is not allowed to invent figures.

## 7. Notes & limitations

- This is a real, working pipeline against live Google APIs — API usage costs apply per your
  Google Cloud billing.
- The "candidate sites" are generated on a deterministic grid around the resolved target area
  (not real parcel/zoning data); treat results as a data-informed shortlist to investigate
  further, not a final decision.
- The Google Maps key is exposed to the browser to render the map (standard practice for the
  Maps JavaScript API) — always apply HTTP-referrer and API restrictions to it in Google Cloud.
# geo
