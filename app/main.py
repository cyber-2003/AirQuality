from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.models import PredictRequest, PredictResponse, PrefillResponse
from app.predictor import predict
from app.openaq import fetch_city_lags
from app.aqi_utils import band_color, band_advice, band_safe, pm25_to_band

# ── App setup ──────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent.parent
STATIC_DIR  = BASE_DIR / "static"

app = FastAPI(title="Real-Time AQI Dashboard", version="1.0.0")

# CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Routes ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=FileResponse)
async def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.post("/predict", response_model=PredictResponse)
async def predict_route(req: PredictRequest):
    """
    Receive form data, run both models, return prediction + health info.
    """
    # Remap Pydantic alias names back to dotted column names
    raw = req.model_dump(by_alias=True)

    # Add current time features if not provided
    now = datetime.now(timezone.utc)
    raw.setdefault("hour",  now.hour)
    raw.setdefault("day",   now.weekday())
    raw.setdefault("month", now.month)

    try:
        pm25, band = predict(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    return PredictResponse(
        pm25_predicted = pm25,
        aqi_band       = band,
        color          = band_color(band),
        advice         = band_advice(band),
        safe_outside   = band_safe(band),
    )


@app.get("/prefill/{city}", response_model=PrefillResponse)
async def prefill_route(city: str):
    """
    Fetch real PM2.5 lag features from Open-Meteo for a given city.
    Frontend calls this to auto-fill the lag/roll input fields.
    """
    result = await fetch_city_lags(city)
    return PrefillResponse(
        found     = result["found"],
        city      = city,
        lags      = result.get("lags", {}),
        current   = result.get("current"),
        timestamp = result.get("timestamp"),
        warning   = result.get("warning"),
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
