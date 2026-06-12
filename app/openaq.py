"""
Open-Meteo Air Quality and Geocoding API integration.
Replaces the OpenAQ integration to solve the "no recent data" issue
by using Open-Meteo's global, keyless, high-reliability meteorological models.
Also fetches current weather and pollutants to auto-fill the entire form.

v1 Open-Meteo Air Quality endpoint:
  GET https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json
  GET https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&hourly=pm2_5&current=pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone&past_days=4&timezone=UTC
  GET https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,surface_pressure,dew_point_2m,rain,wind_speed_10m,wind_direction_10m&wind_speed_unit=ms&timezone=UTC
"""

import datetime
import asyncio
from typing import Optional
import httpx
import numpy as np
import pandas as pd

def degrees_to_wind_direction(deg: float) -> str:
    """Convert wind direction in degrees (0-360) to 16-point compass directions."""
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int((deg + 11.25) / 22.5) % 16
    return directions[idx]


def safe_float(val, default=0.0) -> float:
    """Safe float converter replacing None with default."""
    return float(val) if val is not None else default


async def _geocode_city(city: str, client: httpx.AsyncClient) -> Optional[tuple[float, float, str]]:
    """
    Geocode city name to latitude/longitude.
    Returns (latitude, longitude, resolved_city_name) or None.
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json"
    }
    resp = await client.get(url, params=params, timeout=10.0)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results")
    if not results:
        return None
    res = results[0]
    return float(res["latitude"]), float(res["longitude"]), res.get("name", city)


async def _fetch_air_quality(
    lat: float,
    lon: float,
    client: httpx.AsyncClient
) -> dict:
    """
    Fetch PM2.5 hourly history and current pollutant values.
    """
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "pm2_5",
        "current": "pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
        "past_days": 4,
        "timezone": "UTC"
    }
    resp = await client.get(url, params=params, timeout=15.0)
    resp.raise_for_status()
    return resp.json()


async def _fetch_current_weather(
    lat: float,
    lon: float,
    client: httpx.AsyncClient
) -> dict:
    """
    Fetch current weather variables from the forecast API.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,surface_pressure,dew_point_2m,rain,wind_speed_10m,wind_direction_10m",
        "wind_speed_unit": "ms",
        "timezone": "UTC"
    }
    resp = await client.get(url, params=params, timeout=15.0)
    resp.raise_for_status()
    return resp.json()


def _compute_lag_features(readings: list[float]) -> dict:
    """
    Given PM2.5 readings ordered newest → oldest,
    compute all lag and rolling features the model expects.

    readings[0]  = most recent hour (lag1)
    readings[1]  = 2 hours ago (lag2)
    ...etc
    """
    s = pd.Series(readings)

    lags = {
        "PM2.5_lag1":  s.iloc[0]  if len(s) > 0  else np.nan,
        "PM2.5_lag2":  s.iloc[1]  if len(s) > 1  else np.nan,
        "PM2.5_lag3":  s.iloc[2]  if len(s) > 2  else np.nan,
        "PM2.5_lag6":  s.iloc[5]  if len(s) > 5  else np.nan,
        "PM2.5_lag12": s.iloc[11] if len(s) > 11 else np.nan,
        "PM2.5_lag24": s.iloc[23] if len(s) > 23 else np.nan,
        "PM2.5_lag48": s.iloc[47] if len(s) > 47 else np.nan,
        "PM2.5_lag72": s.iloc[71] if len(s) > 71 else np.nan,
    }

    # Rolling stats use the most recent W hours
    for w in (3, 6, 12, 24):
        window = s.iloc[:w]
        lags[f"PM2.5_roll{w}_mean"] = float(window.mean()) if len(window) >= 2 else np.nan
        lags[f"PM2.5_roll{w}_std"]  = float(window.std())  if len(window) >= 2 else 0.0

    # Replace any remaining NaN with 0 (model handles it via imputer in pipeline)
    return {k: (0.0 if np.isnan(v) else float(v)) for k, v in lags.items()}


async def fetch_city_lags(city: str) -> dict:
    """
    Main entry point.
    Returns a dict with:
      - found: bool
      - lags: dict of lag/roll features (empty if not found)
      - current: dict of current weather/pollutants
      - timestamp: ISO string of latest reading
      - warning: optional message
    """
    async with httpx.AsyncClient() as client:
        # Step 1: Geocode city name to lat/lon
        try:
            geo_res = await _geocode_city(city, client)
        except Exception as e:
            return {
                "found": False, "lags": {}, "current": {}, "timestamp": None,
                "warning": f"Geocoding service error: {str(e)}",
            }

        if not geo_res:
            return {
                "found": False, "lags": {}, "current": {}, "timestamp": None,
                "warning": f"Could not find coordinates for city: {city}",
            }

        lat, lon, resolved_city = geo_res

        # Step 2: Fetch air quality and weather data concurrently
        try:
            aq_task = _fetch_air_quality(lat, lon, client)
            w_task = _fetch_current_weather(lat, lon, client)
            aq_data, w_data = await asyncio.gather(aq_task, w_task)
        except Exception as e:
            return {
                "found": False, "lags": {}, "current": {}, "timestamp": None,
                "warning": f"Data service error: {str(e)}",
            }

        # Step 3: Extract current weather and pollutants
        try:
            w_curr = w_data.get("current", {})
            aq_curr = aq_data.get("current", {})
            
            # Map degrees (0-360) to string direction
            wd_degrees = safe_float(w_curr.get("wind_direction_10m"), 0.0)
            wd_str = degrees_to_wind_direction(wd_degrees)
            
            # Open-Meteo returns CO in ug/m3, model expects mg/m3
            co_ug = safe_float(aq_curr.get("carbon_monoxide"), 0.0)
            co_mg = co_ug / 1000.0
            
            current_conditions = {
                "PM10": safe_float(aq_curr.get("pm10"), 0.0),
                "SO2": safe_float(aq_curr.get("sulphur_dioxide"), 0.0),
                "NO2": safe_float(aq_curr.get("nitrogen_dioxide"), 0.0),
                "CO": co_mg,
                "O3": safe_float(aq_curr.get("ozone"), 0.0),
                "TEMP": safe_float(w_curr.get("temperature_2m"), 15.0),
                "PRES": safe_float(w_curr.get("surface_pressure"), 1013.25),
                "DEWP": safe_float(w_curr.get("dew_point_2m"), 10.0),
                "RAIN": safe_float(w_curr.get("rain"), 0.0),
                "WSPM": safe_float(w_curr.get("wind_speed_10m"), 1.0),
                "wd": wd_str
            }
        except Exception as e:
            current_conditions = {}
            # Non-blocking, continue even if current stats fail
            pass

        # Step 4: Extract and compute hourly lag statistics
        hourly = aq_data.get("hourly")
        if not hourly or "pm2_5" not in hourly or "time" not in hourly:
            return {
                "found": True,
                "lags": {},
                "current": current_conditions,
                "timestamp": None,
                "warning": "Air quality hourly records missing in response.",
            }

        times = hourly["time"]
        pm25_vals = hourly["pm2_5"]

        # Filter out future forecast data and null values
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        valid_readings = []

        for t_str, val in zip(times, pm25_vals):
            if val is None:
                continue
            try:
                dt = datetime.datetime.strptime(t_str, "%Y-%m-%dT%H:%M").replace(tzinfo=datetime.timezone.utc)
                if dt <= now_utc:
                    valid_readings.append((dt, val))
            except Exception:
                continue

        if not valid_readings:
            return {
                "found": True,
                "lags": {},
                "current": current_conditions,
                "timestamp": None,
                "warning": "No historical PM2.5 hourly records available in range.",
            }

        # Sort valid readings newest first
        valid_readings.sort(key=lambda x: x[0], reverse=True)

        readings = [val for dt, val in valid_readings]
        latest_ts = valid_readings[0][0].isoformat()

        # Compute lag features
        lag_features = _compute_lag_features(readings)

        warning = None
        if len(readings) < 72:
            warning = (
                f"Only {len(readings)} hours of history available (72 required). "
                "Some lag features are approximated."
            )

        return {
            "found": True,
            "lags": lag_features,
            "current": current_conditions,
            "timestamp": latest_ts,
            "warning": warning,
        }
