from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

# ── Request sent from the browser form ──────────────────────────────────────
class PredictRequest(BaseModel):
    # Weather & pollutants
    PM10:  float = Field(..., ge=0)
    SO2:   float = Field(..., ge=0)
    NO2:   float = Field(..., ge=0)
    CO:    float = Field(..., ge=0)
    O3:    float = Field(..., ge=0)
    TEMP:  float
    PRES:  float = Field(..., ge=800, le=1100)
    DEWP:  float
    RAIN:  float = Field(..., ge=0)
    WSPM:  float = Field(..., ge=0)
    wd:    str   = Field(..., description="Wind direction e.g. N, SE, NNW")

    # Time
    hour:  int = Field(..., ge=0, le=23)
    day:   int = Field(..., ge=0, le=6)
    month: int = Field(..., ge=1, le=12)

    # Lag features (pre-filled by OpenAQ or entered manually)
    PM2_5_lag1:  float = Field(..., alias="PM2.5_lag1")
    PM2_5_lag2:  float = Field(..., alias="PM2.5_lag2")
    PM2_5_lag3:  float = Field(..., alias="PM2.5_lag3")
    PM2_5_lag6:  float = Field(..., alias="PM2.5_lag6")
    PM2_5_lag12: float = Field(..., alias="PM2.5_lag12")
    PM2_5_lag24: float = Field(..., alias="PM2.5_lag24")
    PM2_5_lag48: float = Field(..., alias="PM2.5_lag48")
    PM2_5_lag72: float = Field(..., alias="PM2.5_lag72")

    # Rolling features
    PM2_5_roll3_mean:  float = Field(..., alias="PM2.5_roll3_mean")
    PM2_5_roll3_std:   float = Field(..., alias="PM2.5_roll3_std")
    PM2_5_roll6_mean:  float = Field(..., alias="PM2.5_roll6_mean")
    PM2_5_roll6_std:   float = Field(..., alias="PM2.5_roll6_std")
    PM2_5_roll12_mean: float = Field(..., alias="PM2.5_roll12_mean")
    PM2_5_roll12_std:  float = Field(..., alias="PM2.5_roll12_std")
    PM2_5_roll24_mean: float = Field(..., alias="PM2.5_roll24_mean")
    PM2_5_roll24_std:  float = Field(..., alias="PM2.5_roll24_std")

    model_config = {"populate_by_name": True}


# ── Response sent back to the browser ───────────────────────────────────────
class PredictResponse(BaseModel):
    pm25_predicted:  float
    aqi_band:        str
    color:           str
    advice:          str
    safe_outside:    Optional[bool]   # True/False/None (caution)


# ── OpenAQ prefill response ──────────────────────────────────────────────────
class PrefillResponse(BaseModel):
    found:    bool
    city:     str
    lags:     dict
    current:  Optional[dict] = None
    timestamp: Optional[str]
    warning:  Optional[str]

