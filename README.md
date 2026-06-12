# Real-Time AQI Predictor & Dashboard

An AI-powered web application that predicts PM2.5 concentrations and classifies Air Quality Index (AQI) bands using machine learning models (Random Forest). Features live data pre-filling via the **Open-Meteo Air Quality & Geocoding APIs** (completely free, no API key required) and an interactive, modern glassmorphic dashboard.

## 🚀 Getting Started

This project is built and managed with [uv](https://github.com/astral-sh/uv), a fast Python package installer and resolver.

### 1. Run the Development Server
Install dependencies and run the FastAPI server using `uv`:
```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
*(No API key configuration is required! The Open-Meteo APIs are free and public.)*

### 2. Open the Dashboard
Open your web browser and navigate to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🛠️ Project Structure

- **`pyproject.toml`**: Project configuration and dependencies (pinned scikit-learn version matching the training environment).
- **`app/`**: Python backend package:
  - `main.py`: FastAPI server setup, endpoints, static file serving, and CORS configurations.
  - `models.py`: Pydantic validation schemas.
  - `predictor.py`: Machine learning model loading and inference pipeline logic.
  - `openaq.py`: Integration with Open-Meteo Geocoding and Air Quality APIs for fetching real-time/historical PM2.5 readings.
  - `aqi_utils.py`: Helper mappings for AQI bands, hex color schemes, health advisories, and outdoor safety statuses.
- **`models/`**: Serialization files for pre-trained Random Forest models (`.joblib` format).
- **`static/`**: Clean, premium front-end using Vanilla HTML/CSS/JS:
  - `index.html`: Dashboard structure, custom inputs, and dynamic results display.
  - `style.css`: Modern glassmorphic theme, responsive layout, CSS variables, and fluid transition animations.
  - `app.js`: Event handling, form validation, Open-Meteo integration, and dynamic styles injection.

---

## ⚡ Tech Stack & Features
- **FastAPI**: Asynchronous Python API.
- **Uvicorn**: ASGI server.
- **scikit-learn (1.6.1)**: Loaded pipeline models for immediate predictions.
- **Vanilla CSS & JS**: Modern glassmorphic layout, dark mode by default, vibrant status colors, dynamic blur overlays, and clean micro-animations.
- **Open-Meteo Air Quality API**: Queries global, high-reliability meteorological models to automatically compute lags and rolling stats for any city.
