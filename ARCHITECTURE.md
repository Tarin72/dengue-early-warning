# System Architecture: Urban Dengue Outbreak Early-Warning Engine

## 1. End-to-End Data Flow
```mermaid
flowchart LR
    A[Weekly ward dataset<br/>31,320 rows, 60 wards, 2016-2025] --> B[src/preprocess.py<br/>per-ward 2-4w lags + 2 future weeks]
    B --> C[Feature matrix<br/>lagged weather, breeding suitability, ward vulnerability]
    C --> D[src/train.py<br/>3 horizon models, chronological split]
    D --> E[models/dengue_model.joblib<br/>+ validation_results.csv]
    E --> F[app.py Streamlit<br/>cached local inference]
    F --> G[Risk tier, 80% interval, model-based drivers,<br/>ward x week heatmap, validation dashboard]
```

## 2. Forecasting Design (true 2-4 week lead)
* Features for a ward-week `s` use weather from weeks `s-2, s-3, s-4` only (`groupby(ward_id).shift`, no cross-ward leakage). No past case counts are used.
* Let `T` be the last observed weather week. Three models forecast cases at `T+2`, `T+3`, `T+4`: the 3- and 4-week models are trained with the target shifted forward, so they use weather that is 3-5 and 4-6 weeks older than the target week. All three use the same feature row (built from weather up to `T`), so the dashboard issues a real forecast beyond the last data point (`add_future_rows` appends 2 empty weeks per ward).
* `derive_features()` is the single formula used by training, the scenario simulator and the driver explanation, so they cannot drift apart.
* Aedes breeding suitability: Gaussian temperature peak at 29 C and humidity ramp, interacted with ward `water_logging_risk_index`, `population_density_sqkm` and `(1 - sanitation_score)`.

## 3. Chronological Validation Split
* Split by **target week**: train `< 2024-01-01` (24,780 ward-weeks for the 2-week model), test `>= 2024-01-01` (6,300 ward-weeks). No shuffling, no future information in training.
* Interval dispersion and model comparison use a validation window (2022-2023, trained on `< 2022`) only; the 2024-2025 test set is used once for final numbers.

| Horizon | Ridge MAE | HGB MAE | HGB RMSE | R2 | Tier acc. | High/Critical alert recall / precision | 80% interval coverage* |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| +2 weeks | 1.1191 | **0.9471** | 1.8871 | 0.7611 | 86.13% | 63.1% / 68.3% | 83.9% |
| +3 weeks | 1.2811 | **0.9912** | 1.915 | 0.754 | 85.25% | 61.9% / 64.4% | 90.4% |
| +4 weeks | 1.5437 | **1.2416** | 2.4963 | 0.582 | 83.0% | 64.9% / 54.0% | 86.1% |

\*coverage on weeks with >= 3 predicted cases. Accuracy falls with horizon, as expected: older weather carries less information.

### Risk tiers and why overall accuracy is not enough
Tiers use fixed weekly-case cut-offs: Low < 3, Medium 3-<8, High 8-<15, Critical >= 15 (operational assumptions to be tuned with health officers). On the holdout the actual tier shares (2-week model) are Low 72.0%, Medium 16.7%, High 9.6%, Critical 1.8%. Because Low dominates, tier accuracy overstates quality; per-tier recall is Low 95.0%, Medium 73.1%, High 52.5%, Critical 30.6%. Rare extreme weeks are the hardest to catch; the dashboard shows the full confusion matrix.

## 4. Model Selection Rationale
Reproduce with `python src/compare_models.py` (2-week horizon, validation window 2022-2023):

| Model | Val MAE | Val RMSE | Val Tier acc. | Fit time |
| :--- | :---: | :---: | :---: | :---: |
| ExtraTrees | 1.1285 | 2.2188 | 84.89% | 4.8s |
| RandomForest | 1.1502 | 2.2616 | 84.25% | 25.64s |
| HistGradientBoosting (Poisson) — chosen | 1.1612 | 2.3523 | 84.09% | 0.33s |
| Poisson GLM (scaled) | 1.2163 | 2.4229 | 83.61% | 0.15s |
| Ridge | 1.2753 | 2.3525 | 83.96% | 0.05s |

ExtraTrees is marginally better on validation MAE, but the differences among tree models are small. We keep Poisson HistGradientBoosting: a count-appropriate objective, ~0.3 s to fit, a ~1 MB artifact for all three horizons, and a natural fit for fast cached inference. Ridge is kept as the baseline.

* **Forecast interval:** 80% Negative-Binomial range around the model mean; dispersion chosen on the validation window only.
* **Driver breakdown:** for each driver group (rainfall lags, temperature, humidity, water-logging, density, sanitation) the dashboard re-predicts with that group set to its median and reports the change in forecast cases. This is model-based (counterfactual), not a raw input scale.

## 5. Compute & API Cost Controls
1. **Serialized models:** `joblib` artifact loaded once with `@st.cache_resource`; inference for 3 horizons + 7 driver counterfactuals is a single small batch (milliseconds).
2. **Feature cache:** engineered features cached in `models/processed_features_v2.pkl` (git-ignored, rebuilt automatically); Excel read with the fast `calamine` engine; `@st.cache_data` for frames.
3. **Zero external API calls** in this prototype. Planned production guardrails: one batched weather fetch per city per day cached in SQLite/Redis; any LLM advisory generated only on a High/Critical tier change, `max_tokens=250`, de-duplicated per `(ward_id, week)`.
