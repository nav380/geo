"""
End-to-end orchestration matching the architecture diagram:

  Query -> Intent Analyzer -> Project Definition -> Planner -> Research Strategy
        -> (Geo Data / Traffic / Business Data via Google Maps Platform)
        -> Geo Processing Engine (Candidate Sites | Routing Analysis | Spatial Analysis)
        -> Candidate Evaluation -> Gemini Analyst -> Final Site Report
"""
from config import settings
from app.services.vertex_client import VertexClient
from app.services.maps_client import MapsClient
from app.services.intent_analyzer import analyze_intent
from app.services.planner import build_research_strategy
from app.services import geo_processing
from app.services.evaluator import evaluate_candidates
from app.services.analyst import generate_report


def run_pipeline(query: str) -> dict:
    warnings: list[str] = []

    vertex_client = VertexClient(
        credentials_path=settings.VERTEX_CREDENTIALS_PATH,
        project_id=settings.VERTEX_PROJECT_ID,
        location=settings.VERTEX_LOCATION,
        model_name=settings.GEMINI_MODEL,
    )
    maps_client = MapsClient(api_key=settings.GOOGLE_MAPS_API_KEY)

    # ---- Stage 1: Intent Analyzer ----
    project_definition = analyze_intent(vertex_client, query)

    # ---- Resolve a real center point via Geocoding, unless Gemini already gave coordinates ----
    lat, lng = project_definition.get("target_lat"), project_definition.get("target_lng")
    if lat is None or lng is None:
        place_query = f"{project_definition.get('city', '')}, {project_definition.get('country', '')}".strip(", ")
        geocoded = maps_client.geocode(place_query)
        if geocoded is None:
            raise ValueError(f"Could not geocode location '{place_query}'. Try being more specific.")
        lat, lng = geocoded["lat"], geocoded["lng"]
        project_definition["resolved_center_address"] = geocoded["formatted_address"]
    center_lat, center_lng = lat, lng

    # ---- Stage 2: Planner ----
    research_strategy = build_research_strategy(vertex_client, project_definition)
    radius_km = project_definition.get("search_radius_km") or settings.DEFAULT_SEARCH_RADIUS_KM
    num_candidates = min(
        research_strategy.get("num_candidates", 6) or 6, settings.MAX_CANDIDATES
    )

    # ---- Traffic anchors: turn planner's human-readable anchor names into real coordinates ----
    anchor_coords = []
    city_country = f"{project_definition.get('city', '')}, {project_definition.get('country', '')}"
    for anchor_name in research_strategy.get("traffic_anchor_names", []):
        geocoded_anchor = maps_client.geocode(f"{anchor_name}, {city_country}")
        if geocoded_anchor:
            anchor_coords.append((geocoded_anchor["lat"], geocoded_anchor["lng"]))
    if not anchor_coords:
        warnings.append("Could not resolve traffic anchor points; accessibility scoring uses defaults.")

    # ---- Stage 3: Geo Processing Engine ----
    grid = geo_processing.generate_candidate_grid(center_lat, center_lng, radius_km, num_candidates)

    raw_candidates = []
    for point in grid:
        spatial = geo_processing.spatial_analysis(
            maps_client, point["lat"], point["lng"], radius_km,
            research_strategy.get("poi_search_keywords", []),
            research_strategy.get("competitor_keywords", []),
        )
        routing = geo_processing.routing_analysis(maps_client, point["lat"], point["lng"], anchor_coords)
        address = maps_client.reverse_geocode(point["lat"], point["lng"])
        raw_candidates.append({
            "id": point["id"],
            "lat": point["lat"],
            "lng": point["lng"],
            "address": address,
            **spatial,
            **routing,
        })

    # ---- Stage 4: Candidate Evaluation ----
    ranked = evaluate_candidates(raw_candidates, research_strategy.get("scoring_weights", {}))

    # ---- Stage 5: Gemini Analyst -> Final Site Report ----
    report = generate_report(vertex_client, project_definition, research_strategy, ranked)

    return {
        "query": query,
        "project_definition": project_definition,
        "research_strategy": research_strategy,
        "map_center": {"lat": center_lat, "lng": center_lng},
        "candidates": ranked,
        "top_candidate": ranked[0],
        "report": report,
        "warnings": warnings,
    }
