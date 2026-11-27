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
* **Dashboard (`app.py`):** 4 pages via `st.navigation` (Forecast, Why this risk, Ward heatmap, Action plan & alerts, Validation) with shared city/ward/horizon filters.
  Contents: 3-horizon forecast with risk tier and 80% interval, model-based driver breakdown, weather scenario simulator, ward x week heatmap, validation tab (MAE/RMSE, confusion matrix, alert recall/precision, interval coverage).
* See `ARCHITECTURE.md` for data flow, split logic, measured accuracy per horizon and model selection.

* **Operations page (`operations.py`):** ranks High/Critical wards, builds a capacity-aware 2-week spray/cleanup/follow-up schedule (CSV export), and composes Bangla/English SMS + WhatsApp alerts with checklists for councillors and residents. Sending is simulated (console + outbox); a WhatsApp click-to-chat link is provided. Template-based, no LLM or API cost.

## Phase 2 (onsite): resource optimisation, routing, simulation, dispatch
Same repo, extended. Four new pages (all local/offline, no external API):
* **Resources (`resource_engine.allocate`):** forecast cases -> `saline_bags_needed`, `diagnostic_kits_needed`, `hospital_beds_required` (ratios fitted on the onsite dataset), regional-stock slider 30-100%, total-crews input, priority = tier weight x cases x density, live deficit alerts.
* **Beds & overflow (`route_overflow`):** bed demand vs ward capacity; overflow routed only inside the same city to the ward with the most free beds; net deficits and city-wide utilisation before/after.
* **What-if simulator (`simulate`):** crews reduce the water-logging breeding index, the saved Phase 1 model is re-run for +2/+3/+4 weeks, wards ranked by ROI (cases prevented per crew), beds and saline saved.
* **Dispatch & briefs:** SMS/WhatsApp notices (Bangla/English) and printable HTML commissioner briefs; one click saves samples into `exports/`.

Assumptions are listed at the top of `resource_engine.py` and in ARCHITECTURE.md section 7 (bed capacity is not in the dataset; crew effect is not field-validated).

## User vs Admin
* **Viewer (default):** every page is read-only. Viewers can pick city/ward/week/horizon/language and read forecasts, allocation, bed routing, simulator results, schedules, notices and briefs, but cannot change settings, send alerts or export.
* **Admin:** log in on the *Admin login* page. Admin controls: regional stock %, total crews, bed-capacity assumption, simulator crews/wards, spray/cleanup team settings, weather scenario, simulated alert sending, `/exports`.
* Admin changes are saved to `admin_settings.json` (local, git-ignore it) and every viewer sees them on the next interaction.
* **Login (email + password):** set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.streamlit/secrets.toml` (or Streamlit Cloud Secrets), or the env vars `DENGUE_ADMIN_EMAIL` / `DENGUE_ADMIN_PASSWORD`. Without them the demo defaults `admin@dengue.local` / `admin123` are used and a warning is shown: change both before deploying.

## AI Assistants & External APIs Disclosure
* **AI Assistants:** Google Gemini (initial code generation) and Anthropic Claude (code review, speed-up, forecast-horizon models, driver explanation, model comparison script, documentation). All code was run and verified by the team.
* **External APIs:** None. All processing, training and inference run locally.
