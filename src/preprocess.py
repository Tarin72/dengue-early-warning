import os
import numpy as np
import pandas as pd
from scipy.stats import nbinom

FEATURE_COLS = [
    "population_density_sqkm", "water_logging_risk_index", "sanitation_score",
    "month", "week_of_year", "week_sin", "week_cos",
    "rainfall_lag_2w", "rainfall_lag_3w", "rainfall_lag_4w",
    "temp_lag_2w", "temp_lag_3w", "temp_lag_4w",
    "humidity_lag_2w", "humidity_lag_3w", "humidity_lag_4w",
    "dtr_lag_2w", "dtr_lag_3w", "dtr_lag_4w",
    "rainfall_sum_2_4w", "rainfall_weighted_lag",
    "temp_mean_2_4w", "humidity_mean_2_4w",
    "temp_suitability", "humidity_suitability", "climate_breeding_index",
    "rain_x_waterlogging", "vulnerability_index",
    "rain_x_vulnerability", "breeding_x_vulnerability",
]


def compute_engineering_columns(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = add_future_rows(df)
    df = df.sort_values(["ward_id", "date"]).reset_index(drop=True)

    df["month"] = df["date"].dt.month
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["week_sin"] = np.sin(2 * np.pi * df["week_of_year"] / 52)
    df["week_cos"] = np.cos(2 * np.pi * df["week_of_year"] / 52)
    df["diurnal_temp_range"] = df["max_temp_c"] - df["min_temp_c"]

    cols = {"rainfall": "rainfall_mm", "temp": "avg_temp_c",
            "humidity": "relative_humidity_pct", "dtr": "diurnal_temp_range"}
    g = df.groupby("ward_id")
    for lag in (2, 3, 4):
        for name, col in cols.items():
            df[f"{name}_lag_{lag}w"] = g[col].shift(lag)

    df = derive_features(df)

    df[FEATURE_COLS] = df[FEATURE_COLS].astype("float32")
    return df


def derive_features(d):
    d["rainfall_sum_2_4w"] = d["rainfall_lag_2w"] + d["rainfall_lag_3w"] + d["rainfall_lag_4w"]
    d["rainfall_weighted_lag"] = 0.25 * d["rainfall_lag_2w"] + 0.5 * d["rainfall_lag_3w"] + 0.25 * d["rainfall_lag_4w"]
    d["temp_mean_2_4w"] = (d["temp_lag_2w"] + d["temp_lag_3w"] + d["temp_lag_4w"]) / 3.0
    d["humidity_mean_2_4w"] = (d["humidity_lag_2w"] + d["humidity_lag_3w"] + d["humidity_lag_4w"]) / 3.0
    d["temp_suitability"] = np.exp(-0.5 * ((d["temp_mean_2_4w"] - 29.0) / 3.5) ** 2)
    d["humidity_suitability"] = np.clip((d["humidity_mean_2_4w"] - 55.0) / 35.0, 0, 1)
    d["climate_breeding_index"] = d["rainfall_weighted_lag"] * d["temp_suitability"] * d["humidity_suitability"]
    d["vulnerability_index"] = (
        (d["population_density_sqkm"] / 75000.0) * 0.4
        + d["water_logging_risk_index"] * 0.4
        + (1.0 - d["sanitation_score"]) * 0.2
    )
    d["rain_x_waterlogging"] = d["rainfall_sum_2_4w"] * d["water_logging_risk_index"]
    d["rain_x_vulnerability"] = d["rainfall_sum_2_4w"] * d["vulnerability_index"]
    d["breeding_x_vulnerability"] = d["climate_breeding_index"] * d["vulnerability_index"]
    return d


RAW_COLS = ["avg_temp_c", "max_temp_c", "min_temp_c", "rainfall_mm", "relative_humidity_pct", "dengue_cases"]


def add_future_rows(df, weeks=2):
    last = df.sort_values("date").groupby("ward_id", sort=False).tail(1)
    parts = [df]
    for k in range(1, weeks + 1):
        f = last.copy()
        f["date"] = f["date"] + pd.Timedelta(weeks=k)
        f[RAW_COLS] = np.nan
        parts.append(f)
    return pd.concat(parts, ignore_index=True)


def local_driver_effects(model, row, baselines):
    groups = {
        "Rainfall (lags 2–4w)": ["rainfall_lag_2w", "rainfall_lag_3w", "rainfall_lag_4w"],
        "Temperature": ["temp_lag_2w", "temp_lag_3w", "temp_lag_4w", "dtr_lag_2w", "dtr_lag_3w", "dtr_lag_4w"],
        "Humidity": ["humidity_lag_2w", "humidity_lag_3w", "humidity_lag_4w"],
        "Water-logging risk": ["water_logging_risk_index"],
        "Population density": ["population_density_sqkm"],
        "Sanitation": ["sanitation_score"],
    }
    rows = [dict(row)]
    for cols in groups.values():
        r = dict(row)
        r.update({c: float(baselines[c]) for c in cols})
        rows.append(derive_features(r))
    X = pd.DataFrame(rows)[FEATURE_COLS].astype("float32")
    p = np.clip(model.predict(X), 0, None)
    return {name: float(p[0] - p[i + 1]) for i, name in enumerate(groups)}


def read_data(filepath):
    if not filepath.endswith((".xlsx", ".xls")):
        return pd.read_csv(filepath)
    try:
        return pd.read_excel(filepath, sheet_name="bangladesh_dengue_large_dataset", engine="calamine")
    except Exception:
        return pd.read_excel(filepath, sheet_name="bangladesh_dengue_large_dataset", engine="openpyxl")


def load_and_engineer_features(filepath="data/hackathon_preli_dataset.xlsx",
                               cache_path="models/processed_features_v2.pkl"):
    if os.path.exists(cache_path):
        try:
            return pd.read_pickle(cache_path)
        except Exception:
            pass
    df = compute_engineering_columns(read_data(filepath))
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    df.to_pickle(cache_path)
    return df


def classify_risk_tier(predicted_cases):
    if predicted_cases < 3.0:
        return "Low"
    elif predicted_cases < 8.0:
        return "Medium"
    elif predicted_cases < 15.0:
        return "High"
    return "Critical"


def predict_interval(mean_cases, dispersion, low_q=0.10, high_q=0.90):
    mu = np.clip(np.asarray(mean_cases, dtype=float), 1e-3, None)
    r = 1.0 / max(dispersion, 1e-6)
    p = r / (r + mu)
    return nbinom.ppf(low_q, r, p), nbinom.ppf(high_q, r, p)
