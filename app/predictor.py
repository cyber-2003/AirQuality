import joblib
import pandas as pd
from pathlib import Path

MODEL_DIR = Path(__file__).parent.parent / "models"

# Loaded once when the module is first imported
_reg_model   = joblib.load(MODEL_DIR / "airquality_regression_model.joblib")
_cls_model   = joblib.load(MODEL_DIR / "airquality_classification_model.joblib")
_label_enc   = joblib.load(MODEL_DIR / "airquality_label_encoder.joblib")

# Exact column order the pipeline was trained on
FEATURE_ORDER = [
    'PM10','SO2','NO2','CO','O3','TEMP','PRES','DEWP','RAIN','WSPM',
    'hour','day','month',
    'PM2.5_lag1','PM2.5_lag2','PM2.5_lag3','PM2.5_lag6',
    'PM2.5_lag12','PM2.5_lag24','PM2.5_lag48','PM2.5_lag72',
    'PM2.5_roll3_mean','PM2.5_roll3_std',
    'PM2.5_roll6_mean','PM2.5_roll6_std',
    'PM2.5_roll12_mean','PM2.5_roll12_std',
    'PM2.5_roll24_mean','PM2.5_roll24_std',
    'wd',
]


def predict(data: dict) -> tuple[float, str]:
    """
    data: flat dict with keys matching FEATURE_ORDER.
    Returns (pm25_float, aqi_band_string).
    """
    # Build single-row DataFrame with correct column names and order
    df = pd.DataFrame([data])[FEATURE_ORDER]

    pm25: float = float(_reg_model.predict(df)[0])
    band_int = _cls_model.predict(df)[0]
    band: str = _label_enc.inverse_transform([band_int])[0]

    return round(pm25, 2), band
