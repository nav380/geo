"""
Candidate Evaluation
====================
Takes raw per-candidate metrics (from geo_processing) and the scoring weights
chosen by the Planner, normalizes each metric to a 0-100 scale, and produces
a final weighted ranking.
"""
from typing import List, Dict


def _normalize(values: List[float], invert: bool = False) -> List[float]:
    """Min-max normalize a list of values to 0-100. If invert=True, lower raw values score higher."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [50.0 for _ in values]
    scaled = [(v - lo) / (hi - lo) * 100 for v in values]
    return [100 - s for s in scaled] if invert else scaled


def evaluate_candidates(raw_candidates: List[Dict], weights: Dict[str, float]) -> List[Dict]:
    """
    raw_candidates: list of dicts each containing at least
        id, lat, lng, address, nearby_demand_pois, nearby_competitors, avg_drive_time_min
    weights: dict with keys demand_proxy, competitor_density, accessibility, foot_traffic_proxy
             (competitor_density weight applies to AVOIDING competitors)
    """
    # normalize weights so they sum to 1
    total_w = sum(weights.values()) or 1.0
    w = {k: v / total_w for k, v in weights.items()}

    demand_vals = [c["nearby_demand_pois"] for c in raw_candidates]
    competitor_vals = [c["nearby_competitors"] for c in raw_candidates]
    # drive time: missing values treated as the worst (max) observed drive time
    drive_times_present = [c["avg_drive_time_min"] for c in raw_candidates if c["avg_drive_time_min"] is not None]
    worst_drive_time = max(drive_times_present) if drive_times_present else 0
    drive_vals = [
        c["avg_drive_time_min"] if c["avg_drive_time_min"] is not None else worst_drive_time
        for c in raw_candidates
    ]

    demand_scores = _normalize(demand_vals)
    competitor_scores = _normalize(competitor_vals, invert=True)  # fewer competitors = higher score
    accessibility_scores = _normalize(drive_vals, invert=True)     # shorter drive time = higher score
    # foot traffic proxy reuses demand density as a stand-in signal (same underlying Places data,
    # weighted separately at the planner's discretion)
    foot_traffic_scores = demand_scores

    results = []
    for i, c in enumerate(raw_candidates):
        scores = {
            "demand_proxy": round(demand_scores[i], 1),
            "competitor_density": round(competitor_scores[i], 1),
            "accessibility": round(accessibility_scores[i], 1),
            "foot_traffic_proxy": round(foot_traffic_scores[i], 1),
        }
        total = (
            scores["demand_proxy"] * w.get("demand_proxy", 0)
            + scores["competitor_density"] * w.get("competitor_density", 0)
            + scores["accessibility"] * w.get("accessibility", 0)
            + scores["foot_traffic_proxy"] * w.get("foot_traffic_proxy", 0)
        )
        results.append({**c, "scores": scores, "total_score": round(total, 1)})

    results.sort(key=lambda r: r["total_score"], reverse=True)
    for rank, r in enumerate(results, start=1):
        r["rank"] = rank
    return results
