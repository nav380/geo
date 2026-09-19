"""
Geo Processing Engine
======================
Implements the three parallel branches from the architecture diagram:
  - Candidate Sites   : generate_candidate_grid()
  - Spatial Analysis  : spatial_analysis() (POI / competitor density via Places API)
  - Routing Analysis  : routing_analysis() (drive time to key anchors via Distance Matrix API)

Output of this stage feeds directly into Candidate Evaluation (evaluator.py).
"""
import math
from typing import List, Dict

EARTH_RADIUS_KM = 6371.0


def _offset_latlng(lat: float, lng: float, d_north_km: float, d_east_km: float) -> tuple[float, float]:
    """Offsets a lat/lng point by a given distance (km) north/east using an equirectangular approximation."""
    d_lat = (d_north_km / EARTH_RADIUS_KM) * (180 / math.pi)
    d_lng = (d_east_km / (EARTH_RADIUS_KM * math.cos(math.pi * lat / 180))) * (180 / math.pi)
    return lat + d_lat, lng + d_lng


def generate_candidate_grid(center_lat: float, center_lng: float, radius_km: float, num_candidates: int) -> List[Dict]:
    """
    Generates candidate site coordinates on a ring + center pattern around the target area.
    This stands in for parcel/zoning data in a full GIS pipeline: it gives us a deterministic,
    well-spread set of real-world-plausible points to evaluate within the requested radius.
    """
    candidates = [{"id": "site-00", "lat": center_lat, "lng": center_lng}]
    remaining = max(num_candidates - 1, 0)
    if remaining <= 0:
        return candidates

    rings = 1 if remaining <= 6 else 2
    per_ring = math.ceil(remaining / rings)
    idx = 1
    for ring in range(1, rings + 1):
        ring_radius = radius_km * (ring / rings)
        for i in range(per_ring):
            if idx > remaining:
                break
            angle = (2 * math.pi / per_ring) * i
            d_north = ring_radius * math.sin(angle)
            d_east = ring_radius * math.cos(angle)
            lat, lng = _offset_latlng(center_lat, center_lng, d_north, d_east)
            candidates.append({"id": f"site-{idx:02d}", "lat": lat, "lng": lng})
            idx += 1
    return candidates[:num_candidates]


def spatial_analysis(maps_client, lat: float, lng: float, radius_km: float,
                      demand_keywords: List[str], competitor_keywords: List[str]) -> Dict:
    """POI / Companies branch: counts demand-generating POIs and direct competitors nearby."""
    radius_m = int(radius_km * 1000)
    demand_count = sum(
        maps_client.nearby_count(lat, lng, radius_m, kw) for kw in demand_keywords
    ) if demand_keywords else 0
    competitor_count = sum(
        maps_client.nearby_count(lat, lng, radius_m, kw) for kw in competitor_keywords
    ) if competitor_keywords else 0
    return {"nearby_demand_pois": demand_count, "nearby_competitors": competitor_count}


def routing_analysis(maps_client, lat: float, lng: float, anchor_coords: List[tuple[float, float]]) -> Dict:
    """Traffic / Roads branch: average traffic-aware drive time to key anchor points."""
    if not anchor_coords:
        return {"avg_drive_time_min": None}
    times = []
    for anchor in anchor_coords:
        t = maps_client.drive_time_minutes((lat, lng), anchor)
        if t is not None:
            times.append(t)
    if not times:
        return {"avg_drive_time_min": None}
    return {"avg_drive_time_min": sum(times) / len(times)}
