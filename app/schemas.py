from typing import Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Natural language site-selection request")


class ScoreBreakdown(BaseModel):
    demand_proxy: float
    competitor_density: float
    accessibility: float
    foot_traffic_proxy: float


class Candidate(BaseModel):
    id: str
    lat: float
    lng: float
    address: Optional[str] = None
    scores: ScoreBreakdown
    total_score: float
    rank: int
    nearby_competitors: int
    nearby_demand_pois: int
    avg_drive_time_min: Optional[float] = None


class AnalyzeResponse(BaseModel):
    query: str
    project_definition: dict
    research_strategy: dict
    map_center: dict
    candidates: list[Candidate]
    top_candidate: Candidate
    report: str
    warnings: list[str] = []
