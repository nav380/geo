"""
Site Selector — FastAPI entry point.

Run with:  uvicorn main:app --reload --port 8000
Then open: http://localhost:8000
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.workflow import run_pipeline

app = FastAPI(title="AI Site Selector", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/api/config")
def get_config():
    """Frontend uses this to load the Google Maps JS API with a key that stays server-side config."""
    return {"mapsApiKey": settings.GOOGLE_MAPS_API_KEY}


@app.get("/api/health")
def health():
    problems = settings.validate()
    return {"ok": len(problems) == 0, "problems": problems}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    problems = settings.validate()
    if problems:
        raise HTTPException(status_code=500, detail={"config_errors": problems})
    try:
        result = run_pipeline(request.query)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")
