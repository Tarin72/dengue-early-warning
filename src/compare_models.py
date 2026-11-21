"""মডেল তুলনা (২-সপ্তাহ horizon)। ট্রেইন: টার্গেট < ২০২২, ভ্যালিডেশন: ২০২২–২৩। টেস্ট (২০২৪–২৫) এখানে ছোঁয়া হয় না।
চালাতে: python src/compare_models.py  → models/model_comparison.csv"""
import time
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.linear_model import PoissonRegressor, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
try:
    from preprocess import FEATURE_COLS, load_and_engineer_features
    from train import make_model, make_horizon_frame, scores, CUTOFF_VAL, CUTOFF_TEST
except ImportError:
    from src.preprocess import FEATURE_COLS, load_and_engineer_features
    from src.train import make_model, make_horizon_frame, scores, CUTOFF_VAL, CUTOFF_TEST


def main(path="data/hackathon_preli_dataset.xlsx"):
    hf = make_horizon_frame(load_and_engineer_features(path, "models/processed_features_v2.pkl"), 2)
    tr = hf[hf["target_date"] < CUTOFF_VAL]
    va = hf[(hf["target_date"] >= CUTOFF_VAL) & (hf["target_date"] < CUTOFF_TEST)]
    candidates = {
        "Ridge": Ridge(alpha=1.0),
        "Poisson GLM (scaled)": make_pipeline(StandardScaler(), PoissonRegressor(alpha=1e-3, max_iter=500)),
        "HistGradientBoosting (Poisson) — chosen": make_model("poisson"),
        "RandomForest": RandomForestRegressor(n_estimators=150, min_samples_leaf=10, n_jobs=-1, random_state=42),
        "ExtraTrees": ExtraTreesRegressor(n_estimators=150, min_samples_leaf=10, n_jobs=-1, random_state=42),
    }
    rows = []
    for name, m in candidates.items():
        t0 = time.time()
        m.fit(tr[FEATURE_COLS], tr["target"])
        p = np.clip(m.predict(va[FEATURE_COLS]), 0, None)
        rows.append({"Model": name, **scores(va["target"], p), "Fit_sec": round(time.time() - t0, 2)})
    out = pd.DataFrame(rows).sort_values("MAE")
    out.to_csv("models/model_comparison.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
