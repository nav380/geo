"""
Wrapper around the Google Maps Platform Python client.
Covers the "Road/Maps", "Traffic", and "POI/Companies" data sources from the
architecture diagram, all backed by real Google Maps Platform endpoints:
  - Geocoding API      -> resolve place names to lat/lng and back
  - Places API         -> POI / competitor density (business data)
  - Distance Matrix API-> drive time / traffic-aware routing analysis
"""
from typing import Optional

import googlemaps


class MapsClient:
    def __init__(self, api_key: str):
        self._client = googlemaps.Client(key=api_key)

    # ---------- Geo Data ----------
    def geocode(self, address: str) -> Optional[dict]:
        results = self._client.geocode(address)
        if not results:
            return None
        loc = results[0]["geometry"]["location"]
        return {
            "lat": loc["lat"],
            "lng": loc["lng"],
            "formatted_address": results[0].get("formatted_address", address),
        }

    def reverse_geocode(self, lat: float, lng: float) -> Optional[str]:
        results = self._client.reverse_geocode((lat, lng))
        if not results:
            return None
        return results[0].get("formatted_address")

    # ---------- Business Data (POI / Companies) ----------
    def nearby_count(self, lat: float, lng: float, radius_m: int, keyword: str) -> int:
        """Returns how many places matching `keyword` are within radius_m of (lat, lng)."""
        try:
            result = self._client.places_nearby(
                location=(lat, lng), radius=radius_m, keyword=keyword
            )
            count = len(result.get("results", []))
            # follow one page of pagination if present, for a slightly better estimate
            token = result.get("next_page_token")
            if token:
                count += 20  # Google caps pages at 20; treat a second page as "plenty"
            return count
        except Exception:
            return 0

    # ---------- Traffic / Routing ----------
    def drive_time_minutes(self, origin: tuple[float, float], destination: tuple[float, float]) -> Optional[float]:
        try:
            result = self._client.distance_matrix(
                origins=[origin],
                destinations=[destination],
                mode="driving",
                departure_time="now",  # enables traffic-aware duration when available
            )
            element = result["rows"][0]["elements"][0]
            if element.get("status") != "OK":
                return None
            duration = element.get("duration_in_traffic", element.get("duration"))
            return duration["value"] / 60.0
        except Exception:
            return None
