# 🦟 AI for Urban Dengue Outbreak Early-Warning System

Ward-level dengue forecasts **2, 3 and 4 weeks after the last observed weather week** for Dhaka North, Dhaka South, Chattogram, Gazipur and Narayanganj, using grouped multi-week weather lags and ward vulnerability.

## Quick Local Setup (< 3 minutes)
```bash
git clone https://github.com/Tarin72/dengue-early-warning.git
cd dengue-early-warning
pip install -r requirements.txt
streamlit run app.py
```
The app loads the pre-trained `models/dengue_model.joblib`. If it is missing or incompatible with your library versions, it retrains automatically (~5 s).
Optional: `python src/train.py` (retrain), `python src/compare_models.py` (model comparison table).

## Features
* **Lag pipeline (`src/preprocess.py`):** 2/3/4-week lags of rainfall, avg temperature, humidity and diurnal range, grouped per `ward_id`.
* **Models (`src/train.py`):** Poisson HistGradientBoosting for +2/+3/+4-week horizons, chronological split (train < 2024, test 2024-25), Ridge baseline.
* **Dashboard (`app.py`):** 3-horizon forecast with risk tier and 80% interval, model-based driver breakdown, weather scenario simulator, ward x week heatmap, validation tab (MAE/RMSE, confusion matrix, alert recall/precision, interval coverage).
* See `ARCHITECTURE.md` for data flow, split logic, measured accuracy per horizon and model selection.

## AI Assistants & External APIs Disclosure
* **AI Assistants:** Google Gemini (initial code generation) and Anthropic Claude (code review, speed-up, forecast-horizon models, driver explanation, model comparison script, documentation). All code was run and verified by the team.
* **External APIs:** None. All processing, training and inference run locally.
