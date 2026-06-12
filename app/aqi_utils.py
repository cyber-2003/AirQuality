from dataclasses import dataclass

BAND_META = {
    "Excellent":          {"color": "#00C853", "safe": True,  "advice": "Air quality is excellent. Great time for outdoor activity."},
    "Good":               {"color": "#64DD17", "safe": True,  "advice": "Air quality is acceptable. Enjoy outdoor activities."},
    "Lightly Polluted":   {"color": "#FFD600", "safe": None,  "advice": "Sensitive groups should reduce prolonged outdoor exertion."},
    "Moderately Polluted":{"color": "#FF6D00", "safe": False, "advice": "Everyone should reduce prolonged outdoor exertion."},
    "Heavily Polluted":   {"color": "#DD2C00", "safe": False, "advice": "Avoid outdoor activities. Wear N95 mask if you must go out."},
    "Severely Polluted":  {"color": "#7B1FA2", "safe": False, "advice": "Hazardous. Stay indoors. Seek medical attention if symptomatic."},
}

def pm25_to_band(pm25: float) -> str:
    if pm25 <= 35:   return "Excellent"
    if pm25 <= 75:   return "Good"
    if pm25 <= 115:  return "Lightly Polluted"
    if pm25 <= 150:  return "Moderately Polluted"
    if pm25 <= 250:  return "Heavily Polluted"
    return "Severely Polluted"

def band_color(band: str) -> str:
    return BAND_META.get(band, {}).get("color", "#888888")

def band_advice(band: str) -> str:
    return BAND_META.get(band, {}).get("advice", "No data.")

def band_safe(band: str):
    return BAND_META.get(band, {}).get("safe", None)
