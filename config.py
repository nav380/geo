"""
Central configuration for the Site Selector platform.

All secrets are loaded from environment variables (see .env.example).
The Vertex AI service account key is loaded from a JSON key file on disk
(default: vertex.json in the project root) rather than being embedded
anywhere in code.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


class Settings:
    # --- Vertex AI / Gemini ---
    VERTEX_CREDENTIALS_PATH: str = os.getenv(
        "VERTEX_CREDENTIALS_PATH", str(BASE_DIR / "vertex.json")
    )
    VERTEX_PROJECT_ID: str = os.getenv("VERTEX_PROJECT_ID", "")
    VERTEX_LOCATION: str = os.getenv("VERTEX_LOCATION", "us-central1")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # --- Google Maps Platform ---
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

    # --- Workflow tuning ---
    DEFAULT_SEARCH_RADIUS_KM: float = float(os.getenv("DEFAULT_SEARCH_RADIUS_KM", "5"))
    MAX_CANDIDATES: int = int(os.getenv("MAX_CANDIDATES", "10"))
    REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "25"))

    def validate(self) -> list[str]:
        """Returns a list of human-readable problems with the current config."""
        problems = []
        if not self.GOOGLE_MAPS_API_KEY:
            problems.append("GOOGLE_MAPS_API_KEY is not set (see .env.example).")
        if not self.VERTEX_PROJECT_ID:
            problems.append("VERTEX_PROJECT_ID is not set (see .env.example).")
        if not Path(self.VERTEX_CREDENTIALS_PATH).exists():
            problems.append(
                f"Vertex credentials file not found at '{self.VERTEX_CREDENTIALS_PATH}'. "
                "Download a service-account JSON key from Google Cloud IAM and save it there "
                "(or point VERTEX_CREDENTIALS_PATH at it)."
            )
        return problems


settings = Settings()
